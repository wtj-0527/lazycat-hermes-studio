#!/usr/bin/env node
import http from 'node:http'
import http2 from 'node:http2'
import { chmodSync, chownSync, readFileSync, rmSync } from 'node:fs'
import { pipeline } from 'node:stream'

const port = Number(process.env.PORT || 8787)
const ttlMs = Number(process.env.LEASE_TTL_MS || 15 * 60 * 1000)
const socketPath = process.env.SOCKET_PATH || ''
const socketGid = Number(process.env.SOCKET_GID || 101)
const testLoopback = process.env.TEST_ALLOW_LOOPBACK === '1'
const catalogFile = process.env.CATALOG_FILE || ''
const lazycatUserId = process.env.LAZYCAT_USER_ID || ''
const apiGatewayAddress = process.env.LZCAPP_API_GATEWAY_ADDRESS || ''
let lease = null

function send(res, status, body = '') {
  res.writeHead(status, {
    'Cache-Control': 'no-store',
    'Content-Type': 'text/plain; charset=utf-8',
  })
  res.end(body)
}

function sendJson(res, status, value) {
  const body = JSON.stringify(value)
  res.writeHead(status, {
    'Cache-Control': 'no-store',
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  })
  res.end(body)
}

function readVarint(buffer, offset) {
  let value = 0
  let shift = 0
  while (offset < buffer.length && shift <= 49) {
    const byte = buffer[offset++]
    value += (byte & 0x7f) * (2 ** shift)
    if ((byte & 0x80) === 0) return [value, offset]
    shift += 7
  }
  throw new Error('invalid protobuf varint')
}

function protobufFields(buffer) {
  const fields = []
  let offset = 0
  while (offset < buffer.length) {
    let key
    ;[key, offset] = readVarint(buffer, offset)
    const number = Math.floor(key / 8)
    const wire = key & 7
    if (!number) throw new Error('invalid protobuf field')
    if (wire === 0) {
      let value
      ;[value, offset] = readVarint(buffer, offset)
      fields.push([number, wire, value])
    } else if (wire === 1) {
      if (offset + 8 > buffer.length) throw new Error('truncated protobuf field')
      fields.push([number, wire, buffer.subarray(offset, offset + 8)])
      offset += 8
    } else if (wire === 2) {
      let length
      ;[length, offset] = readVarint(buffer, offset)
      if (length < 0 || offset + length > buffer.length) throw new Error('truncated protobuf field')
      fields.push([number, wire, buffer.subarray(offset, offset + length)])
      offset += length
    } else if (wire === 5) {
      if (offset + 4 > buffer.length) throw new Error('truncated protobuf field')
      fields.push([number, wire, buffer.subarray(offset, offset + 4)])
      offset += 4
    } else {
      throw new Error('unsupported protobuf wire type')
    }
  }
  return fields
}

function packageIdsFromGrpc(buffer) {
  const ids = new Set()
  let offset = 0
  while (offset < buffer.length) {
    if (offset + 5 > buffer.length) throw new Error('truncated gRPC frame')
    const compressed = buffer[offset]
    const length = buffer.readUInt32BE(offset + 1)
    offset += 5
    if (compressed !== 0 || offset + length > buffer.length) throw new Error('unsupported gRPC frame')
    const message = buffer.subarray(offset, offset + length)
    offset += length
    for (const [number, wire, appInfo] of protobufFields(message)) {
      if (number !== 1 || wire !== 2) continue
      for (const [appNumber, appWire, appId] of protobufFields(appInfo)) {
        if (appNumber !== 1 || appWire !== 2) continue
        const value = appId.toString('utf8')
        if (/^[A-Za-z0-9.-]+$/.test(value)) ids.add(value)
      }
    }
  }
  return [...ids].sort()
}

function queryVisiblePackageIds(ticket, userId) {
  return new Promise((resolve, reject) => {
    if (!apiGatewayAddress || !/^[A-Za-z0-9.-]+:\d+$/.test(apiGatewayAddress)) {
      return reject(new Error('LazyCat API gateway unavailable'))
    }
    const client = http2.connect(`http://${apiGatewayAddress}`)
    const chunks = []
    let grpcStatus = null
    let settled = false
    const fail = error => {
      if (settled) return
      settled = true
      client.close()
      reject(error)
    }
    client.once('error', fail)
    const stream = client.request({
      ':method': 'POST',
      ':path': '/cloud.lazycat.apis.sys.PackageManager/QueryApplication',
      'content-type': 'application/grpc',
      'te': 'trailers',
      'x-hc-user-ticket': ticket,
      'x-hc-user-id': userId,
    })
    stream.setTimeout(10000, () => stream.destroy(new Error('LazyCat API gateway timeout')))
    stream.on('response', headers => {
      if (headers[':status'] !== 200) return stream.destroy(new Error('LazyCat API gateway HTTP error'))
      if (headers['grpc-status'] !== undefined) grpcStatus = String(headers['grpc-status'])
    })
    stream.on('trailers', headers => { grpcStatus = String(headers['grpc-status'] ?? '') })
    stream.on('data', chunk => chunks.push(chunk))
    stream.once('error', fail)
    stream.once('end', () => {
      if (settled) return
      try {
        if (grpcStatus !== '0') throw new Error('LazyCat API gateway gRPC error')
        const ids = packageIdsFromGrpc(Buffer.concat(chunks))
        settled = true
        client.close()
        resolve(ids)
      } catch (error) {
        fail(error)
      }
    })
    stream.end(Buffer.alloc(5))
  })
}

function validTarget(value) {
  if (typeof value !== 'string' || value.length > 2048) return null
  let url
  try { url = new URL(value) } catch { return null }
  if (url.protocol !== 'http:' || url.username || url.password || url.hash) return null
  if (testLoopback && url.hostname === '127.0.0.1') return url
  if (!/^[A-Za-z0-9.-]+\.lzcx$/.test(url.hostname)) return null
  if (!url.hostname.startsWith('app.')) return null
  if (url.port) return null
  return url
}

function catalogProvider(url) {
  if (testLoopback) return { package_id: 'test-loopback', endpoint: url.pathname }
  if (!catalogFile) return null
  try {
    const providers = JSON.parse(readFileSync(catalogFile, 'utf8'))
    return providers.find(provider => `http://app.${provider.package_id}.lzcx${provider.endpoint}` === url.href) || null
  } catch {
    return null
  }
}

function stripHopByHop(input) {
  const headers = { ...input }
  const connectionTokens = String(headers.connection || '').split(',').map(value => value.trim().toLowerCase()).filter(Boolean)
  for (const name of [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailer', 'transfer-encoding', 'upgrade', ...connectionTokens,
  ]) delete headers[name]
  return headers
}

function currentTicket() {
  if (!lease || Date.now() >= lease.expiresAt) {
    lease = null
    return null
  }
  return lease.ticket
}

function capture(req, res) {
  const source = req.headers['x-hc-source']
  const ticket = req.headers['x-hc-user-ticket']
  const userId = req.headers['x-hc-user-id']
  if (source !== 'client' || typeof ticket !== 'string' || !ticket || typeof userId !== 'string' || !userId || !lazycatUserId || userId !== lazycatUserId) {
    return send(res, 403)
  }
  if (lease && Date.now() < lease.expiresAt && lease.userId !== userId) return send(res, 409)
  lease = { ticket, userId, expiresAt: Date.now() + ttlMs }
  res.writeHead(204, { 'Cache-Control': 'no-store' })
  res.end()
}

async function visibleApps(req, res) {
  const ticket = currentTicket()
  if (!ticket || !lease?.userId) return send(res, 428, 'Open Hermes Studio once to query current-user application visibility.')
  try {
    return sendJson(res, 200, { package_ids: await queryVisiblePackageIds(ticket, lease.userId) })
  } catch {
    return sendJson(res, 502, { error: 'CURRENT_USER_APP_VISIBILITY_UNAVAILABLE' })
  }
}

function proxy(req, res) {
  const ticket = currentTicket()
  if (!ticket) return send(res, 428, 'Open Hermes Studio once to authorize LazyCat MCP access.')
  const target = validTarget(req.headers['x-lazycat-target'])
  const provider = target && catalogProvider(target)
  if (!['GET', 'POST', 'DELETE'].includes(req.method || '')) return send(res, 405)
  if (!target || !provider) return send(res, 400, 'Invalid managed LazyCat MCP target.')

  const headers = stripHopByHop({ ...req.headers, host: target.host })
  for (const name of Object.keys(headers)) {
    if (name === 'x-lazycat-target' || name === 'content-length' || name.startsWith('x-hc-')) delete headers[name]
  }
  headers['x-hc-user-ticket'] = ticket
  const upstream = http.request(target, { method: req.method, headers }, upstreamRes => {
    if (upstreamRes.statusCode === 401 || upstreamRes.statusCode === 403) {
      console.error(`[lazycat-ticket-lease] upstream.auth_rejected package_id=${provider.package_id} endpoint=${provider.endpoint} status=${upstreamRes.statusCode}`)
    }
    const responseHeaders = stripHopByHop({ ...upstreamRes.headers, 'cache-control': 'no-store' })
    delete responseHeaders['content-length']
    res.writeHead(upstreamRes.statusCode || 502, responseHeaders)
    pipeline(upstreamRes, res, () => {})
  })
  upstream.setTimeout(300000, () => upstream.destroy(new Error('upstream timeout')))
  const abort = () => { if (!res.writableEnded) upstream.destroy() }
  req.once('aborted', abort)
  res.once('close', abort)
  upstream.on('error', () => { if (!res.headersSent) send(res, 502, 'Managed LazyCat MCP upstream unavailable.') })
  pipeline(req, upstream, () => {})
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/healthz') return send(res, 200, 'ok')
  if (req.method === 'POST' && req.url === '/internal/capture') return capture(req, res)
  if (req.method === 'GET' && req.url === '/internal/visible-apps') return visibleApps(req, res)
  if (req.url === '/internal/proxy') return proxy(req, res)
  return send(res, 404)
})
if (socketPath) {
  rmSync(socketPath, { force: true })
  server.listen(socketPath, () => {
    chownSync(socketPath, 0, socketGid)
    chmodSync(socketPath, 0o660)
    console.log('[lazycat-ticket-lease] listening on private socket')
  })
} else {
  server.listen(port, '0.0.0.0', () => console.log('[lazycat-ticket-lease] listening'))
}
