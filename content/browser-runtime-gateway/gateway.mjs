import { timingSafeEqual } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import { createServer, request as httpRequest } from 'node:http'
import { connect as tcpConnect } from 'node:net'
import { lookup } from 'node:dns/promises'
import { isIP } from 'node:net'

function safeEqual(left, right) {
  const a = Buffer.from(String(left))
  const b = Buffer.from(String(right))
  return a.length === b.length && timingSafeEqual(a, b)
}

function writeJson(response, status, body) {
  response.statusCode = status
  response.setHeader('Content-Type', 'application/json; charset=utf-8')
  response.setHeader('Cache-Control', 'no-store')
  response.end(JSON.stringify(body))
}

async function readJson(request, limit = 64 * 1024) {
  const chunks = []
  let size = 0
  for await (const chunk of request) {
    size += chunk.length
    if (size > limit) throw new Error('request_too_large')
    chunks.push(Buffer.from(chunk))
  }
  const value = chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : {}
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid_request')
  return value
}

export async function readPrivateToken(path) {
  if (process.platform !== 'win32') {
    const info = await stat(path)
    if (!info.isFile() || (info.mode & 0o077) !== 0) throw new Error('Unsafe Browser Runtime token file permissions')
  }
  const token = (await readFile(path, 'utf8')).trim()
  if (token.length < 32) throw new Error('Browser Runtime token is invalid')
  return token
}

function publicAuthority(request, bindPort) {
  const host = String(request.headers.host || `browser-runtime-gateway:${bindPort}`)
  return host
}

function authorized(request, token) {
  const value = String(request.headers.authorization || '')
  return value.startsWith('Bearer ') && safeEqual(value.slice(7), token)
}

function validId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)
}

function validOwner(value) {
  return typeof value === 'string' && value.length >= 3 && value.length <= 300 && /^[^\s\0]+$/.test(value)
}

function validProfile(value) {
  return typeof value === 'string' && value.trim() === value && value.length >= 1 && value.length <= 200 && !value.includes('\0')
}

function validProxy(value, expectedHost) {
  try {
    const url = new URL(value)
    return url.protocol === 'http:'
      && Boolean(url.hostname)
      && url.hostname.toLowerCase() === expectedHost.toLowerCase()
      && Boolean(url.username)
      && Boolean(url.password)
  } catch {
    return false
  }
}

function privateIpv4(address) {
  const octets = String(address).split('.').map(Number)
  if (octets.length !== 4 || octets.some(value => !Number.isInteger(value) || value < 0 || value > 255)) return false
  return octets[0] === 127
    || octets[0] === 10
    || (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31)
    || (octets[0] === 192 && octets[1] === 168)
}

export async function resolvePrivateEngineAddress(hostname) {
  if (isIP(hostname)) {
    if (!privateIpv4(hostname)) throw new Error('Browser Runtime engine address is not private IPv4')
    return hostname
  }
  const answers = await lookup(hostname, { all: true, verbatim: true })
  if (!answers.length || answers.some(answer => answer.family !== 4 || !privateIpv4(answer.address))) {
    throw new Error('Browser Runtime engine DNS answers are not exclusively private IPv4')
  }
  return answers[0].address
}

async function engineRequest(engineBase, engineAddress, path, body) {
  const target = new URL(path, engineBase)
  target.hostname = engineAddress
  const payload = body === undefined ? undefined : Buffer.from(JSON.stringify(body))
  return await new Promise((resolve, reject) => {
    const request = httpRequest(target, {
      method: 'POST',
      headers: {
        Host: engineBase.host,
        'Content-Type': 'application/json',
        ...(payload ? { 'Content-Length': String(payload.length) } : {}),
      },
      timeout: 45_000,
    }, response => {
      const chunks = []
      let size = 0
      response.on('data', chunk => {
        size += chunk.length
        if (size > 1024 * 1024) request.destroy(new Error('engine_response_too_large'))
        else chunks.push(Buffer.from(chunk))
      })
      response.on('end', () => {
        if ((response.statusCode || 500) < 200 || (response.statusCode || 500) >= 300) return reject(new Error(`engine_http_${response.statusCode || 500}`))
        try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString('utf8')) : null) } catch { reject(new Error('engine_invalid_json')) }
      })
    })
    request.once('timeout', () => request.destroy(new Error('engine_timeout')))
    request.once('error', reject)
    if (payload) request.write(payload)
    request.end()
  })
}

function forwardUpgrade(request, socket, head, target) {
  const port = Number(target.port || (target.protocol === 'wss:' ? 443 : 80))
  if (target.protocol !== 'ws:') {
    socket.end('HTTP/1.1 502 Bad Gateway\r\n\r\n')
    return
  }
  const upstream = tcpConnect(port, target.hostname)
  upstream.setTimeout(30_000, () => upstream.destroy())
  upstream.once('error', () => socket.destroy())
  socket.once('error', () => upstream.destroy())
  upstream.once('connect', () => {
    const headers = []
    for (const [name, value] of Object.entries(request.headers)) {
      if (value == null || name.toLowerCase() === 'authorization' || name.toLowerCase() === 'host') continue
      if (Array.isArray(value)) for (const item of value) headers.push(`${name}: ${item}`)
      else headers.push(`${name}: ${value}`)
    }
    upstream.write([
      `GET ${target.pathname}${target.search} HTTP/1.1`,
      `Host: ${target.host}`,
      ...headers,
      '', '',
    ].join('\r\n'))
    if (head.length) upstream.write(head)
    upstream.pipe(socket)
    socket.pipe(upstream)
  })
}

export function createBrowserRuntimeGateway({ token, engineUrl, engineAddress, egressProxyHost }) {
  if (String(token || '').length < 32) throw new Error('Browser Runtime token is invalid')
  if (typeof egressProxyHost !== 'string' || !egressProxyHost || /[\s/@]/.test(egressProxyHost)) throw new Error('Browser Runtime egress proxy host is invalid')
  const engineBase = new URL(engineUrl)
  if (engineBase.protocol !== 'http:' || engineBase.username || engineBase.password) throw new Error('Browser Runtime engine URL is invalid')
  const pinnedEngineAddress = engineAddress || engineBase.hostname
  if (!privateIpv4(pinnedEngineAddress)) throw new Error('Browser Runtime engine address is not private IPv4')
  let active = null
  let transaction = Promise.resolve()

  const serialized = operation => {
    const next = transaction.catch(() => undefined).then(operation)
    transaction = next.then(() => undefined, () => undefined)
    return next
  }

  const server = createServer(async (request, response) => {
    const url = new URL(request.url || '/', 'http://gateway.invalid')
    if (request.method === 'GET' && url.pathname === '/health') {
      writeJson(response, 200, { status: 'ok' })
      return
    }
    if (!authorized(request, token)) {
      writeJson(response, 401, { error: 'unauthorized' })
      return
    }
    try {
      if (request.method === 'POST' && url.pathname === '/v1/sessions') {
        const input = await readJson(request)
        if (!validId(input.sessionId) || !validOwner(input.ownerKey) || !validProfile(input.profile) || !validProxy(input.egressProxyUrl, egressProxyHost)) {
          writeJson(response, 400, { error: 'invalid_runtime_session_request' })
          return
        }
        const result = await serialized(async () => {
          if (active) return { status: 409, body: { error: 'runtime_in_use' } }
          const payload = await engineRequest(engineBase, pinnedEngineAddress, '/v1/sessions', {
            sessionId: input.sessionId,
            proxyUrl: input.egressProxyUrl,
          })
          if (!payload || payload.id !== input.sessionId || typeof payload.websocketUrl !== 'string') throw new Error('engine_identity_mismatch')
          const cdpTarget = new URL(payload.websocketUrl)
          if (cdpTarget.protocol !== 'ws:' || cdpTarget.username || cdpTarget.password) throw new Error('engine_cdp_invalid')
          cdpTarget.hostname = pinnedEngineAddress
          cdpTarget.port = engineBase.port
          const liveTarget = new URL(`/v1/sessions/${encodeURIComponent(input.sessionId)}/cast`, engineBase)
          liveTarget.protocol = 'ws:'
          liveTarget.hostname = pinnedEngineAddress
          liveTarget.port = engineBase.port
          active = {
            id: input.sessionId,
            ownerKey: input.ownerKey,
            profile: input.profile,
            cdpTarget,
            liveTarget,
          }
          const authority = publicAuthority(request, server.address()?.port)
          return {
            status: 200,
            body: {
              id: active.id,
              cdpUrl: `ws://${authority}/v1/sessions/${encodeURIComponent(active.id)}/cdp`,
              liveViewUrl: `ws://${authority}/v1/sessions/${encodeURIComponent(active.id)}/live/{pageId}`,
            },
          }
        })
        writeJson(response, result.status, result.body)
        return
      }
      const release = url.pathname.match(/^\/v1\/sessions\/([A-Za-z0-9._:-]{1,128})\/release$/)
      if (request.method === 'POST' && release) {
        const result = await serialized(async () => {
          const session = active
          if (!session || session.id !== release[1]) return { status: 409, body: { error: 'session_mismatch' } }
          await engineRequest(engineBase, pinnedEngineAddress, `/v1/sessions/${encodeURIComponent(session.id)}/release`)
          if (active === session) active = null
          return { status: 200, body: { success: true, id: session.id } }
        })
        writeJson(response, result.status, result.body)
        return
      }
      writeJson(response, 404, { error: 'not_found' })
    } catch (error) {
      writeJson(response, error?.message === 'request_too_large' ? 413 : 502, { error: 'runtime_gateway_failed' })
    }
  })

  server.on('upgrade', (request, socket, head) => {
    if (!authorized(request, token)) {
      socket.end('HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n')
      return
    }
    const url = new URL(request.url || '/', 'http://gateway.invalid')
    const match = url.pathname.match(/^\/v1\/sessions\/([A-Za-z0-9._:-]{1,128})\/(cdp|live(?:\/([^/]+))?)$/)
    const session = active
    if (!match || !session || session.id !== match[1]) {
      socket.end('HTTP/1.1 409 Conflict\r\nContent-Length: 0\r\n\r\n')
      return
    }
    const isLive = match[2].startsWith('live/')
    if (match[2] === 'live' || (isLive && !match[3])) {
      socket.end('HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n')
      return
    }
    const target = new URL(isLive ? session.liveTarget : session.cdpTarget)
    if (isLive) target.searchParams.set('pageId', match[3])
    forwardUpgrade(request, socket, head, target)
  })

  return server
}

async function main() {
  const tokenFile = process.env.BROWSER_RUNTIME_TOKEN_FILE
  const engineUrl = process.env.BROWSER_RUNTIME_ENGINE_URL
  const egressProxyHost = process.env.BROWSER_RUNTIME_EGRESS_PROXY_HOST
  const host = process.env.HOST || '0.0.0.0'
  const port = Number(process.env.PORT || 3000)
  if (!tokenFile || !engineUrl || !egressProxyHost || !Number.isInteger(port) || port <= 0 || port > 65535) throw new Error('Browser Runtime Gateway configuration is invalid')
  const token = await readPrivateToken(tokenFile)
  const engineAddress = await resolvePrivateEngineAddress(new URL(engineUrl).hostname)
  const server = createBrowserRuntimeGateway({ token, engineUrl, engineAddress, egressProxyHost })
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(port, host, resolve)
  })
  console.log(`[browser-runtime-gateway] listening on ${host}:${port}`)
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error(`[browser-runtime-gateway] ${error instanceof Error ? error.message : String(error)}`)
    process.exit(1)
  })
}
