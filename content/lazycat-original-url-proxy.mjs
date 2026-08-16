#!/usr/bin/env node
import http from 'node:http'

import { readFileSync } from 'node:fs'
import { pipeline } from 'node:stream'

const listenPort = Number(process.env.ORIGINAL_URL_PROXY_PORT || 18787)
const socketPath = process.env.SOCKET_PATH || '/lzcapp/var/mcp-runtime/lease.sock'
const catalogFile = process.env.CATALOG_FILE || '/lzcapp/var/mcp-runtime/providers.json'

function send(res, status, body = '') {
  res.writeHead(status, {
    'Cache-Control': 'no-store',
    'Content-Type': 'text/plain; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  })
  res.end(body)
}

function stripHopByHop(input) {
  const headers = { ...input }
  const connectionTokens = String(headers.connection || '').split(',').map(value => value.trim().toLowerCase()).filter(Boolean)
  for (const name of [
    'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'proxy-connection', 'te', 'trailer', 'transfer-encoding', 'upgrade', ...connectionTokens,
  ]) delete headers[name]
  return headers
}

function providers() {
  try {
    const value = JSON.parse(readFileSync(catalogFile, 'utf8'))
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function targetFor(rawUrl) {
  let url
  try { url = new URL(rawUrl) } catch { return null }
  if (url.protocol !== 'http:' || url.username || url.password || url.hash) return null
  if (!url.hostname.endsWith('.lzcapp')) return null
  for (const provider of providers()) {
    if (typeof provider.original_host_suffix !== 'string' || !provider.original_host_suffix) continue
    if (!Number.isInteger(provider.original_port) || provider.original_port < 1 || provider.original_port > 65535) continue
    const suffix = `.${provider.original_host_suffix}`
    if (!url.hostname.endsWith(suffix) || url.hostname.length <= suffix.length) continue
    if (Number(url.port || 80) !== provider.original_port) continue
    if (url.pathname + url.search !== provider.endpoint) continue
    return `http://app.${provider.package_id}.lzcx${provider.endpoint}`
  }
  return null
}

function relay(req, res, target) {
  const headers = stripHopByHop({ ...req.headers, 'x-lazycat-target': target })
  for (const name of Object.keys(headers)) {
    if (name === 'host' || name.startsWith('x-hc-')) delete headers[name]
  }
  const upstream = http.request({
    socketPath,
    path: '/internal/proxy',
    method: req.method,
    headers,
  }, upstreamRes => {
    const responseHeaders = stripHopByHop({ ...upstreamRes.headers, 'cache-control': 'no-store' })
    delete responseHeaders['content-length']
    res.writeHead(upstreamRes.statusCode || 502, responseHeaders)
    pipeline(upstreamRes, res, () => {})
  })
  upstream.setTimeout(300000, () => upstream.destroy(new Error('relay timeout')))
  const abort = () => { if (!res.writableEnded) upstream.destroy() }
  req.once('aborted', abort)
  res.once('close', abort)
  upstream.on('error', () => { if (!res.headersSent) send(res, 502, 'LazyCat MCP ticket relay unavailable.') })
  pipeline(req, upstream, () => {})
}

const server = http.createServer((req, res) => {
  let url
  try { url = new URL(req.url || '') } catch { return send(res, 400) }
  const target = targetFor(url.href)
  if (target) {
    if (!['GET', 'POST', 'DELETE'].includes(req.method || '')) return send(res, 405)
    return relay(req, res, target)
  }
  if (url.hostname.endsWith('.lzcapp')) return send(res, 400, 'Unknown or invalid projected LazyCat MCP URL.')
  return send(res, 403, 'This proxy only accepts exact projected LazyCat MCP URLs.')
})
server.on('connect', (_req, client) => {
  client.end('HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n')
})
server.listen(listenPort, '127.0.0.1', () => {
  console.log('[lazycat-original-url-proxy] listening on loopback')
})
