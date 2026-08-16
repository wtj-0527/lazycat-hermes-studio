#!/bin/sh
set -eu
PROXY_SCRIPT=/lzcapp/pkg/content/lazycat-original-url-proxy.mjs
PROXY_PID=
: "${ORIGINAL_MCP_HOST:?ORIGINAL_MCP_HOST is required}"
case "$ORIGINAL_MCP_HOST" in
    *[!a-z0-9.-]*|.*|*.) echo "invalid ORIGINAL_MCP_HOST" >&2; exit 1 ;;
esac
# Scope interception to the one verified original MCP hostname. No global
# HTTP_PROXY is set, so unrelated provider/OAuth/integration traffic is untouched.
if ! grep -Fqx "127.0.0.1 $ORIGINAL_MCP_HOST" /etc/hosts 2>/dev/null; then
    printf '127.0.0.1 %s\n' "$ORIGINAL_MCP_HOST" >> /etc/hosts
fi
cleanup() {
    if [ -n "$PROXY_PID" ]; then kill "$PROXY_PID" 2>/dev/null || true; fi
}
trap cleanup HUP INT TERM EXIT
/usr/local/bin/node "$PROXY_SCRIPT" &
PROXY_PID=$!
# Fail closed if the loopback proxy exits during startup.
sleep 0.2
if ! kill -0 "$PROXY_PID" 2>/dev/null; then
    wait "$PROXY_PID"
    exit 1
fi
/usr/local/bin/node dist/server/index.js
status=$?
exit "$status"
