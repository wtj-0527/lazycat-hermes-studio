import assert from 'node:assert/strict'
import test from 'node:test'
import { captureTicket } from '../content/lazycat-mcp-bootstrap.js'

async function withLogs(run) {
  const original = console.info
  const logs = []
  console.info = (...args) => logs.push(args)
  try {
    const result = await run()
    return { result, logs }
  } finally {
    console.info = original
  }
}

test('captures a ticket context without sending Studio credentials', async () => {
  const calls = []
  const { result, logs } = await withLogs(() => captureTicket(async (url, init) => {
    calls.push({ url, init })
    return { ok: true, status: 204 }
  }))
  assert.equal(result, true)
  assert.deepEqual(calls, [{
    url: '/lazycat-mcp/capture',
    init: { method: 'POST', credentials: 'same-origin', cache: 'no-store' },
  }])
  assert.deepEqual(logs, [['[lazycat-mcp]', 'capture.ok', { status: 204 }]])
  const rendered = JSON.stringify({ calls, logs })
  assert.equal(rendered.includes('Authorization'), false)
  assert.equal(rendered.includes('X-Hermes-Profile'), false)
  assert.equal(rendered.includes('X-HC-USER-TICKET'), false)
})

test('logs a bounded renewal success event', async () => {
  const { result, logs } = await withLogs(() => captureTicket(
    async () => ({ ok: true, status: 204 }),
    'capture.renew.ok',
  ))
  assert.equal(result, true)
  assert.deepEqual(logs, [['[lazycat-mcp]', 'capture.renew.ok', { status: 204 }]])
})

test('logs only status when capture is rejected', async () => {
  const { result, logs } = await withLogs(() => captureTicket(
    async () => ({ ok: false, status: 403, text: async () => 'secret response body' }),
  ))
  assert.equal(result, false)
  assert.deepEqual(logs, [['[lazycat-mcp]', 'capture.failed', { status: 403 }]])
  assert.equal(JSON.stringify(logs).includes('secret response body'), false)
})

test('logs a bounded category for network errors', async () => {
  const { result, logs } = await withLogs(() => captureTicket(async () => {
    throw new Error('credential-bearing network detail')
  }, 'capture.renew.ok'))
  assert.equal(result, false)
  assert.deepEqual(logs, [['[lazycat-mcp]', 'capture.renew.failed', { category: 'network_error' }]])
  assert.equal(JSON.stringify(logs).includes('credential-bearing'), false)
})
