const PREFIX = '[lazycat-mcp]'
const log = (event, fields = {}) => console.info(PREFIX, event, fields)

export async function captureTicket(fetchImpl = fetch, event = 'capture.ok') {
  try {
    const response = await fetchImpl('/lazycat-mcp/capture', {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
    })
    if (response.ok) {
      log(event, { status: response.status })
      return true
    }
    log(event === 'capture.ok' ? 'capture.failed' : 'capture.renew.failed', { status: response.status })
  } catch {
    log(event === 'capture.ok' ? 'capture.failed' : 'capture.renew.failed', { category: 'network_error' })
  }
  return false
}

if (typeof window !== 'undefined') {
  log('bootstrap.loaded', { version: '2026.08.16.1409', mode: 'manual_mcp_original_url' })
  captureTicket(fetch, 'capture.ok')
  setInterval(() => captureTicket(fetch, 'capture.renew.ok'), 5 * 60 * 1000)
}
