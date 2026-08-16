export const PREFIX = 'lazycat-projected--'
export const managedName = provider => PREFIX + `${provider.package_id}--${provider.resource_id}`.replace(/[^A-Za-z0-9._-]/g, '-')
const expectedUrl = provider => `http://nginx${provider.proxy_path}`

function isOwnedConfig(name, config) {
  if (!name.startsWith(PREFIX) || !config || typeof config !== 'object') return false
  if (Object.keys(config).some(key => !['url', 'enabled'].includes(key))) return false
  const suffix = name.slice(PREFIX.length)
  const split = suffix.lastIndexOf('--')
  if (split <= 0) return false
  const packageId = suffix.slice(0, split)
  const resourceId = suffix.slice(split + 2)
  if (!/^[A-Za-z0-9.-]+$/.test(packageId) || !/^[A-Za-z0-9._-]+$/.test(resourceId)) return false
  return config.url === `http://nginx/lazycat-mcp/${packageId}/${resourceId}`
}

export async function syncManagedMcp(fetchImpl = fetch) {
  const json = async (url, init) => {
    const response = await fetchImpl(url, { credentials: 'same-origin', cache: 'no-store', ...init })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    if (response.status === 204) return null
    const body = await response.json()
    if (body && !Array.isArray(body) && body.ok === false) throw new Error('MCP management rejected')
    return body
  }

  await json('/lazycat-mcp/capture', { method: 'POST' })
  const [providers, state] = await Promise.all([
    json('/lazycat-mcp/providers.json'),
    json('/api/hermes/mcp/servers'),
  ])
  const servers = new Map((state.servers || []).map(server => [server.name, server]))
  const desired = new Map(providers.map(provider => [managedName(provider), { url: expectedUrl(provider) }]))

  let changed = false
  for (const [name, config] of desired) {
    const existing = servers.get(name)
    if (existing && !isOwnedConfig(name, existing.raw_config)) continue
    const method = existing ? 'PATCH' : 'POST'
    const url = existing ? `/api/hermes/mcp/servers/${encodeURIComponent(name)}` : '/api/hermes/mcp/servers'
    const body = existing ? { config } : { name, config }
    if (!existing || existing.raw_config?.url !== config.url) {
      await json(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      changed = true
    }
  }

  for (const server of servers.values()) {
    if (isOwnedConfig(server.name, server.raw_config) && !desired.has(server.name)) {
      await json(`/api/hermes/mcp/servers/${encodeURIComponent(server.name)}`, { method: 'DELETE' })
      changed = true
    }
  }
  if (changed) await json('/api/hermes/mcp/reload', { method: 'POST' })
}

if (typeof window !== 'undefined') {
  const capture = () => fetch('/lazycat-mcp/capture', { method: 'POST', credentials: 'same-origin', cache: 'no-store' }).catch(() => {})
  const run = () => syncManagedMcp().catch(() => {})
  if (navigator.locks?.request) navigator.locks.request('lazycat-managed-mcp-sync', run)
  else run()
  setInterval(capture, 5 * 60 * 1000)
}
