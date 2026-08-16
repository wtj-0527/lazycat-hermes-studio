import assert from 'node:assert/strict'
import test from 'node:test'
import { captureLazyCatTicket } from '../content/lazycat-mcp-bootstrap.js'

test('captures ticket through the wrapper endpoint without reading it', async () => {
  const calls = []
  await captureLazyCatTicket(async (url, init) => {
    calls.push({ url, init })
    return { ok: true, status: 204 }
  })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/lazycat-mcp/capture')
  assert.equal(calls[0].init.method, 'POST')
  assert.equal(calls[0].init.credentials, 'same-origin')
  assert.equal(JSON.stringify(calls[0]).includes('ticket'), false)
})

test('rejects a failed capture so the caller can apply bounded retry policy', async () => {
  await assert.rejects(
    captureLazyCatTicket(async () => ({ ok: false, status: 401 })),
    /HTTP 401/,
  )
})
