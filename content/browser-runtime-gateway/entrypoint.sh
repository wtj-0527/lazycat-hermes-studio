#!/bin/sh
set -eu
umask 077

TOKEN_FILE=${BROWSER_RUNTIME_TOKEN_FILE:?BROWSER_RUNTIME_TOKEN_FILE is required}
TOKEN_DIR=$(dirname "$TOKEN_FILE")
mkdir -p "$TOKEN_DIR"
chmod 0700 "$TOKEN_DIR"

if [ ! -f "$TOKEN_FILE" ]; then
  TMP_FILE="$TOKEN_FILE.tmp.$$"
  trap 'rm -f "$TMP_FILE"' EXIT HUP INT TERM
  node -e "process.stdout.write(require('node:crypto').randomBytes(32).toString('base64url') + '\n')" > "$TMP_FILE"
  chmod 0600 "$TMP_FILE"
  mv "$TMP_FILE" "$TOKEN_FILE"
  trap - EXIT HUP INT TERM
fi

chmod 0600 "$TOKEN_FILE"
TOKEN_LENGTH=$(tr -d '\r\n' < "$TOKEN_FILE" | wc -c | tr -d ' ')
[ "$TOKEN_LENGTH" -ge 32 ] || { echo 'Browser Runtime token is invalid' >&2; exit 1; }

exec /usr/local/bin/node /lzcapp/pkg/content/browser-runtime-gateway/gateway.mjs
