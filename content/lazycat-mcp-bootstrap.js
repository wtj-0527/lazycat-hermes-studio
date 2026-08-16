export async function captureLazyCatTicket(fetchImpl = fetch) {
  const response = await fetchImpl('/lazycat-mcp/capture', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
}

if (typeof window !== 'undefined') {
  const capture = () => captureLazyCatTicket().catch(() => {})
  capture()
  setInterval(capture, 5 * 60 * 1000)
}
