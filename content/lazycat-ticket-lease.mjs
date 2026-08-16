#!/usr/bin/env node
import http from 'node:http'
import { readFileSync } from 'node:fs'
import { pipeline } from 'node:stream'

const port = Number(process.env.PORT || 8787)
const ttlMs = Number(process.env.LEASE_TTL_MS || 15 * 60 * 1000)
const internalToken = process.env.INTERNAL_TOKEN_FILE
  ? readFileSync(process.env.INTERNAL_TOKEN_FILE, 'utf8').trim()
  : (process.env.INTERNAL_TOKEN || '')
const testLoopback = process.env.TEST_ALLOW_LOOPBACK === '1'
const catalogFile = process.env.CATALOG_FILE || ''
let lease = null

function authorized(req) {
  return !internalToken || req.headers['x-internal-token'] === internalToken
}

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

function currentTicket() {
  if (!lease || Date.now() >= lease.expiresAt) {
    lease = null
    return null
  }
  return lease.ticket
}

function capture(req, res) {
  if (!authorized(req)) return send(res, 403)
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
  if (!authorized(req)) return send(res, 403)
  const ticket = currentTicket()
  if (!ticket) return send(res, 428, 'Open Hermes Studio once to authorize LazyCat MCP access.')
  const target = validTarget(req.headers['x-lazycat-target'])
  if (!target || !catalogAllows(target)) return send(res, 400, 'Invalid managed LazyCat MCP target.')

  const headers = { ...req.headers, host: target.host, 'x-hc-user-ticket': ticket }
  const connectionTokens = String(req.headers.connection || '').split(',').map(value => value.trim().toLowerCase()).filter(Boolean)
  for (const name of [
    'x-internal-token', 'x-lazycat-target', 'connection', 'content-length',
    'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer',
    'transfer-encoding', 'upgrade', ...connectionTokens,
  ]) delete headers[name]
  const upstream = http.request(target, { method: req.method, headers }, upstreamRes => {
    if (upstreamRes.statusCode === 401 || upstreamRes.statusCode === 403) lease = null
    const responseHeaders = { ...upstreamRes.headers, 'cache-control': 'no-store' }
    delete responseHeaders['transfer-encoding']
    res.writeHead(upstreamRes.statusCode || 502, responseHeaders)
    pipeline(upstreamRes, res, () => {})
  })
  upstream.on('error', () => send(res, 502, 'Managed LazyCat MCP upstream unavailable.'))
  pipeline(req, upstream, () => {})
}

http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/healthz') return send(res, 200, 'ok')
  if (req.method === 'POST' && req.url === '/internal/capture') return capture(req, res)
  if (req.url === '/internal/proxy') return proxy(req, res)
  return send(res, 404)
}).listen(port, '0.0.0.0', () => {
  console.log('[lazycat-ticket-lease] listening')
})
