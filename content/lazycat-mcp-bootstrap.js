export async function captureTicket(fetchImpl = fetch) {
  try {
    const response = await fetchImpl('/lazycat-mcp/capture', {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
    })
    return response.ok
  } catch {
    return false
  }
}

if (typeof window !== 'undefined') {
  captureTicket(fetch)
  setInterval(() => captureTicket(fetch), 5 * 60 * 1000)
}
