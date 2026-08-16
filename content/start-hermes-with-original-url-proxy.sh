#!/bin/sh
set -eu
PROXY_SCRIPT=/lzcapp/pkg/content/lazycat-original-url-proxy.mjs
PROXY_PID=
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
