#!/bin/sh
set -eu
TOKEN_FILE="${INTERNAL_TOKEN_FILE:?INTERNAL_TOKEN_FILE is required}"
LEASE_SCRIPT="${LEASE_SCRIPT:-/lzcapp/pkg/content/lazycat-ticket-lease.mjs}"
WAIT_SECONDS="${TOKEN_WAIT_SECONDS:-30}"
i=0
while [ ! -s "$TOKEN_FILE" ]; do
    i=$((i + 1))
    if [ "$i" -ge "$WAIT_SECONDS" ]; then
        echo "[lazycat-ticket-lease] internal token unavailable" >&2
        exit 1
    fi
    sleep 1
done
exec /usr/local/bin/node "$LEASE_SCRIPT"
