#!/usr/bin/env node
import http from 'node:http'
import { chmodSync, chownSync, readFileSync, rmSync } from 'node:fs'
import { pipeline } from 'node:stream'

const port = Number(process.env.PORT || 8787)
const ttlMs = Number(process.env.LEASE_TTL_MS || 15 * 60 * 1000)
const socketPath = process.env.SOCKET_PATH || ''
const socketGid = Number(process.env.SOCKET_GID || 101)
const testLoopback = process.env.TEST_ALLOW_LOOPBACK === '1'
const catalogFile = process.env.CATALOG_FILE || ''
let lease = null

function send(res, status, body = '') {
  res.writeHead(status, {
    'Cache-Control': 'no-store',
    'Content-Type': 'text/plain; charset=utf-8',
  })
  res.end(body)
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

function catalogAllows(url) {
  if (testLoopback) return true
  if (!catalogFile) return false
  try {
    const providers = JSON.parse(readFileSync(catalogFile, 'utf8'))
    return providers.some(provider => `http://app.${provider.package_id}.lzcx${provider.endpoint}` === url.href)
  } catch {
    return false
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
  if (source !== 'client' || typeof ticket !== 'string' || !ticket || typeof userId !== 'string' || !userId) {
    return send(res, 403)
  }
  if (lease && Date.now() < lease.expiresAt && lease.userId !== userId) return send(res, 409)
  lease = { ticket, userId, expiresAt: Date.now() + ttlMs }
  res.writeHead(204, { 'Cache-Control': 'no-store' })
  res.end()
}

function proxy(req, res) {
  const ticket = currentTicket()
  if (!ticket) return send(res, 428, 'Open Hermes Studio once to authorize LazyCat MCP access.')
  const target = validTarget(req.headers['x-lazycat-target'])
  if (!['GET', 'POST', 'DELETE'].includes(req.method || '')) return send(res, 405)
  if (!target || !catalogAllows(target)) return send(res, 400, 'Invalid managed LazyCat MCP target.')

  const headers = stripHopByHop({ ...req.headers, host: target.host, 'x-hc-user-ticket': ticket })
  for (const name of ['x-lazycat-target', 'content-length']) delete headers[name]
  const upstream = http.request(target, { method: req.method, headers }, upstreamRes => {
    if (upstreamRes.statusCode === 401 || upstreamRes.statusCode === 403) lease = null
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
