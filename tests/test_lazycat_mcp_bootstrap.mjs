import assert from 'node:assert/strict'
import test from 'node:test'
import { managedName, syncManagedMcp } from '../content/lazycat-mcp-bootstrap.js'

const ok = body => ({ ok: true, status: body == null ? 204 : 200, json: async () => body })

function harness(providers, servers) {
  const calls = []
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url, method: init.method || 'GET', body: init.body && JSON.parse(init.body) })
    if (url === '/lazycat-mcp/capture') return ok(null)
    if (url === '/lazycat-mcp/providers.json') return ok(providers)
    if (url === '/api/hermes/mcp/servers' && !init.method) return ok({ servers })
    return ok({ ok: true })
  }
  return { calls, run: () => syncManagedMcp(fetchImpl) }
}

const provider = { package_id: 'cloud.lazycat.app.todo', resource_id: 'default', proxy_path: '/lazycat-mcp/cloud.lazycat.app.todo/default' }

test('adds a deterministic ticket-free managed server', async () => {
  const h = harness([provider], [])
  await h.run()
  const add = h.calls.find(call => call.method === 'POST' && call.url === '/api/hermes/mcp/servers')
  assert.equal(add.body.name, managedName(provider))
  assert.deepEqual(add.body.config, { url: 'http://nginx/lazycat-mcp/cloud.lazycat.app.todo/default' })
  assert.equal(h.calls.at(-1).url, '/api/hermes/mcp/reload')
})

test('does not overwrite an unmarked colliding user server', async () => {
  const name = managedName(provider)
  const h = harness([provider], [{ name, raw_config: { url: 'http://user.example/mcp' } }])
  await h.run()
  assert.equal(h.calls.some(call => ['PATCH', 'DELETE'].includes(call.method)), false)
  assert.equal(h.calls.some(call => call.url === '/api/hermes/mcp/reload'), false)
})

test('updates a marked managed server and removes only marked orphans', async () => {
  const name = managedName(provider)
  const h = harness([provider], [
    { name, raw_config: { url: 'http://nginx/lazycat-mcp/cloud.lazycat.app.todo/default' } },
    { name: 'lazycat-projected--orphan--default', raw_config: { url: 'http://nginx/lazycat-mcp/orphan/default' } },
    { name: 'lazycat-projected--user', raw_config: { url: 'http://user.example/mcp' } },
  ])
  await h.run()
  assert.equal(h.calls.some(call => call.method === 'PATCH'), false)
  assert.equal(h.calls.some(call => call.method === 'DELETE' && call.url.endsWith('lazycat-projected--orphan--default')), true)
  assert.equal(h.calls.some(call => call.url.endsWith('lazycat-projected--user') && ['PATCH', 'DELETE'].includes(call.method)), false)
})
