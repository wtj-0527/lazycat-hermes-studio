import assert from 'node:assert/strict'
import test from 'node:test'
import { captureTicket } from '../content/lazycat-mcp-bootstrap.js'

async function withoutConsoleOutput(run) {
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
  const { result, logs } = await withoutConsoleOutput(() => captureTicket(async (url, init) => {
    calls.push({ url, init })
    return { ok: true, status: 204 }
  }))
  assert.equal(result, true)
  assert.deepEqual(calls, [{
    url: '/lazycat-mcp/capture',
    init: { method: 'POST', credentials: 'same-origin', cache: 'no-store' },
  }])
  assert.deepEqual(logs, [])
  const rendered = JSON.stringify({ calls, logs })
  assert.equal(rendered.includes('Authorization'), false)
  assert.equal(rendered.includes('X-Hermes-Profile'), false)
  assert.equal(rendered.includes('X-HC-USER-TICKET'), false)
})

test('renews without writing to the browser console', async () => {
  const { result, logs } = await withoutConsoleOutput(() => captureTicket(
    async () => ({ ok: true, status: 204 }),
  ))
  assert.equal(result, true)
  assert.deepEqual(logs, [])
})

test('rejects without writing response details to the browser console', async () => {
  const { result, logs } = await withoutConsoleOutput(() => captureTicket(
    async () => ({ ok: false, status: 403, text: async () => 'secret response body' }),
  ))
  assert.equal(result, false)
  assert.deepEqual(logs, [])
  assert.equal(JSON.stringify(logs).includes('secret response body'), false)
})

test('handles network errors without writing to the browser console', async () => {
  const { result, logs } = await withoutConsoleOutput(() => captureTicket(async () => {
    throw new Error('credential-bearing network detail')
  }))
  assert.equal(result, false)
  assert.deepEqual(logs, [])
  assert.equal(JSON.stringify(logs).includes('credential-bearing'), false)
})
