#!/bin/sh
# Generate exact-match Nginx routes for LazyCat-exported MCP providers.
set -eu

RESOURCE_ROOT="${MCP_RESOURCE_ROOT:-/lzcapp/run/resources/mcp-providers}"
NGINX_OUTPUT="${MCP_NGINX_OUTPUT:-/etc/nginx/conf.d/lazycat-mcp-generated.conf}"
CATALOG_OUTPUT="${MCP_CATALOG_OUTPUT:-/lzcapp/run/lazycat-mcp-providers.json}"

mkdir -p "$(dirname "$NGINX_OUTPUT")" "$(dirname "$CATALOG_OUTPUT")"
nginx_tmp="${NGINX_OUTPUT}.tmp.$$"
catalog_tmp="${CATALOG_OUTPUT}.tmp.$$"
files_tmp="${TMPDIR:-/tmp}/lazycat-mcp-files.$$"
trap 'rm -f "$nginx_tmp" "$catalog_tmp" "$files_tmp"' EXIT HUP INT TERM

cat >"$nginx_tmp" <<EOF
# generated LazyCat MCP routes; do not edit
location = /lazycat-mcp/providers.json {
    alias $CATALOG_OUTPUT;
    default_type application/json;
    add_header Cache-Control "no-store" always;
}
EOF
printf '[\n' >"$catalog_tmp"
first=1

# Parse the small, documented mcp.yml projection subset without adding a YAML
# runtime dependency to the Nginx image. Fail closed on YAML features outside
# this subset: top-level plain scalar mappings and two-space plain list items.
read_endpoint() {
    awk '
        BEGIN { endpoint_count = 0; list_open = 0 }
        /\r|\t/ { exit 2 }
        /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
        /^[A-Za-z][A-Za-z0-9_-]*:([ ]+.*)?$/ {
            line = $0
            key = line
            sub(/:.*/, "", key)
            value = line
            sub(/^[^:]*:([ ]+)?/, "", value)
            if (value ~ /[][{}]/ || value ~ /: / || value ~ /^[&*!|>"'"'"'%@`?-]/) exit 2
            list_open = (value == "")
            if (key == "endpoint") {
                if (value == "") exit 2
                endpoint = value
                endpoint_count++
            }
            next
        }
        /^  - [A-Za-z0-9._-]+[ ]*$/ {
            if (!list_open) exit 2
            next
        }
        { exit 2 }
        END {
            if (endpoint_count != 1) exit 2
            print endpoint
        }
    ' "$1"
}

if [ -d "$RESOURCE_ROOT" ]; then
    find "$RESOURCE_ROOT" -mindepth 3 -maxdepth 3 -type f -name mcp.yml -print | LC_ALL=C sort >"$files_tmp"
else
    : >"$files_tmp"
fi

while IFS= read -r file; do
    relative=${file#"$RESOURCE_ROOT"/}
    package_id=${relative%%/*}
    rest=${relative#*/}
    resource_id=${rest%%/*}

    case "$package_id" in
        ''|*[!A-Za-z0-9._-]*) echo "[mcp-proxy] skip unsafe package id: $package_id" >&2; continue ;;
    esac
    case "$resource_id" in
        ''|*[!A-Za-z0-9._-]*) echo "[mcp-proxy] skip unsafe resource id: $resource_id" >&2; continue ;;
    esac

    if ! endpoint=$(read_endpoint "$file"); then
        echo "[mcp-proxy] skip $package_id/$resource_id: malformed or unsupported mcp.yml" >&2
        continue
    fi

    case "$endpoint" in
        /*) ;;
        *) echo "[mcp-proxy] skip $package_id/$resource_id: endpoint must be absolute" >&2; continue ;;
    esac
    case "$endpoint" in
        *..*|*://*|*[!A-Za-z0-9._~/?\&=+,:%-]*)
            echo "[mcp-proxy] skip $package_id/$resource_id: unsafe endpoint" >&2
            continue
            ;;
    esac

    proxy_path="/lazycat-mcp/$package_id/$resource_id"
    cat >>"$nginx_tmp" <<EOF

location = $proxy_path {
    proxy_pass http://app.$package_id.lzcx$endpoint;
    proxy_set_header X-HC-USER-TICKET \$http_x_hc_user_ticket;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
EOF

    if [ "$first" -eq 0 ]; then printf ',\n' >>"$catalog_tmp"; fi
    first=0
    printf '  {"package_id":"%s","resource_id":"%s","endpoint":"%s","proxy_path":"%s"}' \
        "$package_id" "$resource_id" "$endpoint" "$proxy_path" >>"$catalog_tmp"
done <"$files_tmp"

printf '\n]\n' >>"$catalog_tmp"
mv "$nginx_tmp" "$NGINX_OUTPUT"
mv "$catalog_tmp" "$CATALOG_OUTPUT"
trap - EXIT HUP INT TERM

echo "[mcp-proxy] generated $(grep -c '^location = /lazycat-mcp/.* {' "$NGINX_OUTPUT") route entries"
