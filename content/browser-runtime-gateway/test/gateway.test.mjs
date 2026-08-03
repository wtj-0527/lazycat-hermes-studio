import assert from 'node:assert/strict'
import { mkdtemp, writeFile, chmod } from 'node:fs/promises'
import { createServer as createHttpServer, request as httpRequest } from 'node:http'
import { connect as tcpConnect } from 'node:net'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'
import { createBrowserRuntimeGateway, readPrivateToken, resolvePrivateEngineAddress } from '../gateway.mjs'

const token = 'test-runtime-token-that-is-longer-than-thirty-two-characters'
const auth = { Authorization: `Bearer ${token}` }

async function listen(server) {
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  return `http://127.0.0.1:${address.port}`
}

async function close(server) {
  if (!server.listening) return
  await new Promise(resolve => {
    server.close(resolve)
    server.closeAllConnections?.()
  })
}

async function jsonRequest(baseUrl, path, { method = 'GET', headers = {}, body } = {}) {
  const response = await fetch(new URL(path, baseUrl), {
    method,
    headers: { ...headers, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  return { status: response.status, body: await response.json() }
}

async function websocketHandshake(baseUrl, path, authorization) {
  const url = new URL(baseUrl)
  return await new Promise((resolve, reject) => {
    const socket = tcpConnect(Number(url.port), url.hostname)
    let response = ''
    socket.once('error', reject)
    socket.on('data', chunk => {
      response += chunk.toString('latin1')
      if (response.includes('\r\n\r\n')) {
        socket.destroy()
        resolve(response)
      }
    })
    socket.once('connect', () => {
      socket.write([
        `GET ${path} HTTP/1.1`,
        `Host: ${url.host}`,
        'Connection: Upgrade',
        'Upgrade: websocket',
        'Sec-WebSocket-Version: 13',
        'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==',
        ...(authorization ? [`Authorization: ${authorization}`] : []),
        '', '',
      ].join('\r\n'))
    })
  })
}

test('token file is private and at least 32 characters', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'browser-runtime-gateway-token-'))
  const file = join(directory, 'token')
  await writeFile(file, `${token}\n`, { mode: 0o600 })
  assert.equal(await readPrivateToken(file), token)
  if (process.platform !== 'win32') {
    await chmod(file, 0o644)
    await assert.rejects(readPrivateToken(file), /permissions/)
  }
})

test('engine endpoint must be private IPv4 before proxy credentials can be forwarded', async () => {
  assert.equal(await resolvePrivateEngineAddress('127.0.0.1'), '127.0.0.1')
  for (const address of ['8.8.8.8', '100.64.0.1', '169.254.169.254']) {
    await assert.rejects(resolvePrivateEngineAddress(address), /not private IPv4/)
    assert.throws(() => createBrowserRuntimeGateway({
      token,
      engineUrl: `http://${address}:3000`,
      egressProxyHost: 'studio.internal',
    }), /not private IPv4/)
  }
})

test('gateway enforces auth, mandatory egress, exact session release, and generic response fields', async t => {
  const upstreamRequests = []
  const engine = createHttpServer(async (request, response) => {
    const chunks = []
    for await (const chunk of request) chunks.push(Buffer.from(chunk))
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : null
    upstreamRequests.push({ method: request.method, url: request.url, body })
    response.setHeader('Content-Type', 'application/json')
    if (request.method === 'POST' && request.url === '/v1/sessions') {
      response.end(JSON.stringify({
        id: body.sessionId,
        websocketUrl: `ws://127.0.0.1:${engine.address().port}/engine/cdp?runtime=${body.sessionId}`,
      }))
      return
    }
    if (request.method === 'POST' && request.url === `/v1/sessions/${body?.sessionId || 'session-a'}/release`) {
      response.end(JSON.stringify({ success: true }))
      return
    }
    if (request.method === 'POST' && request.url === '/v1/sessions/session-a/release') {
      response.end(JSON.stringify({ success: true }))
      return
    }
    response.statusCode = 404
    response.end(JSON.stringify({ error: 'not_found' }))
  })
  const engineUrl = await listen(engine)
  const gateway = createBrowserRuntimeGateway({ token, engineUrl, egressProxyHost: 'studio.internal' })
  const gatewayUrl = await listen(gateway)
  t.after(async () => { await close(gateway); await close(engine) })

  assert.equal((await jsonRequest(gatewayUrl, '/health')).status, 200)
  assert.equal((await jsonRequest(gatewayUrl, '/v1/sessions', { method: 'POST', body: {} })).status, 401)
  assert.equal((await jsonRequest(gatewayUrl, '/v1/sessions', {
    method: 'POST', headers: auth,
    body: { sessionId: 'session-a', ownerKey: '7:work', profile: 'work' },
  })).status, 400)

  assert.equal((await jsonRequest(gatewayUrl, '/v1/sessions', {
    method: 'POST', headers: auth,
    body: {
      sessionId: 'session-a', ownerKey: '7:work', profile: 'work',
      egressProxyUrl: 'http://proxy-user:proxy-pass@untrusted.internal:43123',
    },
  })).status, 400)

  const created = await jsonRequest(gatewayUrl, '/v1/sessions', {
    method: 'POST', headers: auth,
    body: {
      sessionId: 'session-a', ownerKey: '7:work', profile: 'work',
      egressProxyUrl: 'http://proxy-user:proxy-pass@studio.internal:43123',
    },
  })
  assert.equal(created.status, 200)
  assert.deepEqual(created.body, {
    id: 'session-a',
    cdpUrl: `${gatewayUrl.replace('http:', 'ws:')}/v1/sessions/session-a/cdp`,
    liveViewUrl: `${gatewayUrl.replace('http:', 'ws:')}/v1/sessions/session-a/live/{pageId}`,
  })
  assert.deepEqual(upstreamRequests[0], {
    method: 'POST', url: '/v1/sessions',
    body: { sessionId: 'session-a', proxyUrl: 'http://proxy-user:proxy-pass@studio.internal:43123' },
  })

  const conflict = await jsonRequest(gatewayUrl, '/v1/sessions', {
    method: 'POST', headers: auth,
    body: {
      sessionId: 'session-b', ownerKey: '8:work', profile: 'work',
      egressProxyUrl: 'http://proxy-user:proxy-pass@studio.internal:43123',
    },
  })
  assert.equal(conflict.status, 409)
  assert.equal((await jsonRequest(gatewayUrl, '/v1/sessions/wrong/release', { method: 'POST', headers: auth })).status, 409)
  assert.equal((await jsonRequest(gatewayUrl, '/v1/sessions/session-a/release', { method: 'POST', headers: auth })).status, 200)
  assert.equal(upstreamRequests.at(-1).url, '/v1/sessions/session-a/release')
})

test('gateway authenticates and fences CDP/live-view upgrades before proxying exact paths', async t => {
  const upgrades = []
  const engine = createHttpServer(async (request, response) => {
    const chunks = []
    for await (const chunk of request) chunks.push(Buffer.from(chunk))
    const body = chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {}
    response.setHeader('Content-Type', 'application/json')
    if (request.method === 'POST' && request.url === '/v1/sessions') {
      response.end(JSON.stringify({
        id: body.sessionId,
        websocketUrl: `ws://127.0.0.1:${engine.address().port}/engine/cdp?runtime=${body.sessionId}`,
      }))
      return
    }
    response.statusCode = 404
    response.end(JSON.stringify({ error: 'not_found' }))
  })
  engine.on('upgrade', (request, socket) => {
    upgrades.push(request.url)
    socket.end('HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n')
  })
  const engineUrl = await listen(engine)
  const gateway = createBrowserRuntimeGateway({ token, engineUrl, egressProxyHost: 'studio.internal' })
  const gatewayUrl = await listen(gateway)
  t.after(async () => { await close(gateway); await close(engine) })

  await jsonRequest(gatewayUrl, '/v1/sessions', {
    method: 'POST', headers: auth,
    body: {
      sessionId: 'session-a', ownerKey: '7:work', profile: 'work',
      egressProxyUrl: 'http://proxy-user:proxy-pass@studio.internal:43123',
    },
  }).catch(() => undefined)

  assert.match(await websocketHandshake(gatewayUrl, '/v1/sessions/session-a/cdp', ''), /401 Unauthorized/)
  assert.match(await websocketHandshake(gatewayUrl, '/v1/sessions/wrong/cdp', `Bearer ${token}`), /409 Conflict/)
  assert.match(await websocketHandshake(gatewayUrl, '/v1/sessions/session-a/cdp', `Bearer ${token}`), /101 Switching Protocols/)
  assert.match(await websocketHandshake(gatewayUrl, '/v1/sessions/session-a/live/page-1', `Bearer ${token}`), /101 Switching Protocols/)
  assert.deepEqual(upgrades, [
    '/engine/cdp?runtime=session-a',
    '/v1/sessions/session-a/cast?pageId=page-1',
  ])
})
