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

export async function syncManagedMcp(fetchImpl = fetch, auth = {}, logger = () => {}) {
  const apiKey = typeof auth.apiKey === 'string' ? auth.apiKey.trim() : ''
  const profile = typeof auth.profile === 'string' && auth.profile.trim() ? auth.profile.trim() : 'default'
  if (!apiKey) throw new Error('Studio authentication is not ready')
  logger('sync.start', { profile_ready: true })

  const json = async (url, init = {}) => {
    const isStudioApi = url.startsWith('/api/hermes/mcp/')
    const headers = { ...(init.headers || {}) }
    if (isStudioApi) {
      headers.Authorization = `Bearer ${apiKey}`
      headers['X-Hermes-Profile'] = profile
    }
    const response = await fetchImpl(url, { credentials: 'same-origin', cache: 'no-store', ...init, headers })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    if (response.status === 204) return null
    const body = await response.json()
    if (body && !Array.isArray(body) && body.ok === false) throw new Error('MCP management rejected')
    return body
  }

  await json('/lazycat-mcp/capture', { method: 'POST' })
  logger('capture.ok')
  const providers = await json('/lazycat-mcp/providers.json')
  logger('catalog.ok', { providers: providers.length })
  const state = await json('/api/hermes/mcp/servers')
  const serverList = state.servers || []
  logger('studio.list.ok', { existing: serverList.length })
  const servers = new Map(serverList.map(server => [server.name, server]))
  const desired = new Map(providers.map(provider => [managedName(provider), { url: expectedUrl(provider) }]))

  let changed = false
  let added = 0
  let updated = 0
  let removed = 0
  for (const [name, config] of desired) {
    const existing = servers.get(name)
    if (existing && !isOwnedConfig(name, existing.raw_config)) continue
    const method = existing ? 'PATCH' : 'POST'
    const url = existing ? `/api/hermes/mcp/servers/${encodeURIComponent(name)}` : '/api/hermes/mcp/servers'
    const body = existing ? { config } : { name, config }
    if (!existing || existing.raw_config?.url !== config.url) {
      await json(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (existing) {
        updated += 1
        logger('studio.update.ok', { completed: updated })
      } else {
        added += 1
        logger('studio.add.ok', { completed: added })
      }
      changed = true
    }
  }

  for (const server of servers.values()) {
    if (isOwnedConfig(server.name, server.raw_config) && !desired.has(server.name)) {
      await json(`/api/hermes/mcp/servers/${encodeURIComponent(server.name)}`, { method: 'DELETE' })
      removed += 1
      logger('studio.remove.ok', { completed: removed })
      changed = true
    }
  }
  if (changed) {
    await json('/api/hermes/mcp/reload', { method: 'POST' })
    logger('studio.reload.ok')
  }
  logger('sync.complete', { providers: providers.length, existing: serverList.length, added, updated, removed, reloaded: changed })
}

if (typeof window !== 'undefined') {
  const log = (event, fields = {}) => console.info('[lazycat-mcp]', event, fields)
  const classify = error => {
    const message = error instanceof Error ? error.message : ''
    if (message === 'Studio authentication is not ready') return 'auth_not_ready'
    if (/^HTTP [0-9]{3}$/.test(message)) return 'http_error'
    if (message === 'MCP management rejected') return 'management_rejected'
    return 'unexpected'
  }
  const capture = async () => {
    try {
      const response = await fetch('/lazycat-mcp/capture', { method: 'POST', credentials: 'same-origin', cache: 'no-store' })
      log(response.ok ? 'capture.renew.ok' : 'capture.renew.failed', { status: response.status })
    } catch {
      log('capture.renew.failed', { category: 'network_error' })
    }
  }
  const auth = () => ({
    apiKey: localStorage.getItem('hermes_api_key') || '',
    profile: localStorage.getItem('hermes_active_profile_name') || 'default',
  })
  let retries = 0
  const run = async () => {
    log('bootstrap.attempt', { attempt: retries + 1 })
    try {
      await syncManagedMcp(fetch, auth(), log)
    } catch (error) {
      const category = classify(error)
      if (retries++ < 20) {
        log('bootstrap.retry', { attempt: retries, category, delay_ms: 500 })
        setTimeout(run, 500)
      } else {
        log('bootstrap.failed', { attempts: retries, category })
      }
    }
  }
  log('bootstrap.loaded', { version: '2026.08.16.1326' })
  if (navigator.locks?.request) navigator.locks.request('lazycat-managed-mcp-sync', run)
  else run()
  setInterval(capture, 5 * 60 * 1000)
}
