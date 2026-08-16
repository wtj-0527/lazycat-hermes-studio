#!/bin/sh
set -eu
LEASE_SCRIPT="${LEASE_SCRIPT:-/lzcapp/pkg/content/lazycat-ticket-lease.mjs}"
SOCKET_PATH="${SOCKET_PATH:?SOCKET_PATH is required}"
SOCKET_GID="${SOCKET_GID:-101}"
mkdir -p "$(dirname "$SOCKET_PATH")"
chown 0:"$SOCKET_GID" "$(dirname "$SOCKET_PATH")"
chmod 0750 "$(dirname "$SOCKET_PATH")"
exec /usr/local/bin/node "$LEASE_SCRIPT"
