#!/usr/bin/env node
import http from 'node:http'
import net from 'node:net'
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
    const suffix = `.${provider.package_id}.lzcapp`
    if (!url.hostname.endsWith(suffix) || url.hostname.length <= suffix.length) continue
    if (url.pathname + url.search !== provider.endpoint) continue
    return `http://app.${provider.package_id}.lzcx${provider.endpoint}`
  }
  return null
}

function relay(req, res, target) {
  const headers = stripHopByHop({ ...req.headers, 'x-lazycat-target': target })
  delete headers.host
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

function forward(req, res, url) {
  if (!['http:'].includes(url.protocol) || url.username || url.password || url.hash) return send(res, 400)
  const headers = stripHopByHop({ ...req.headers, host: url.host })
  for (const name of ['x-lazycat-target', 'x-hc-user-ticket', 'x-hc-user-id', 'x-hc-source']) delete headers[name]
  const upstream = http.request(url, { method: req.method, headers }, upstreamRes => {
    const responseHeaders = stripHopByHop({ ...upstreamRes.headers })
    res.writeHead(upstreamRes.statusCode || 502, responseHeaders)
    pipeline(upstreamRes, res, () => {})
  })
  upstream.setTimeout(300000, () => upstream.destroy(new Error('upstream timeout')))
  upstream.on('error', () => { if (!res.headersSent) send(res, 502, 'HTTP upstream unavailable.') })
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
  forward(req, res, url)
})
server.on('connect', (req, client, head) => {
  const authority = req.url || ''
  let target
  try { target = new URL(`http://${authority}`) } catch {
    client.end('HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n')
    return
  }
  if (!target.hostname || target.hostname.endsWith('.lzcapp') || !target.port) {
    client.end('HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n')
    return
  }
  const upstream = net.connect(Number(target.port), target.hostname)
  upstream.setTimeout(300000, () => upstream.destroy())
  upstream.once('connect', () => {
    client.write('HTTP/1.1 200 Connection Established\r\n\r\n')
    if (head.length) upstream.write(head)
    client.pipe(upstream)
    upstream.pipe(client)
  })
  upstream.once('error', () => client.end('HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n'))
})
server.listen(listenPort, '127.0.0.1', () => {
  console.log('[lazycat-original-url-proxy] listening on loopback')
})
