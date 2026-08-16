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
snapshot_dir=$(mktemp -d "${TMPDIR:-/tmp}/lazycat-mcp.XXXXXX")
snapshot_tmp="$snapshot_dir/mcp.yml"
trap 'rm -f "$nginx_tmp" "$catalog_tmp" "$files_tmp"; rm -rf "$snapshot_dir"' 0 HUP INT TERM

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
    # YAML 1.2 forbids C0 controls other than LF. We intentionally reject CR
    # and TAB too because this strict subset has no quoted scalars.
    if ! LC_ALL=C od -An -tu1 "$1" | awk '
        { for (i = 1; i <= NF; i++) if (($i >= 0 && $i <= 9) || ($i >= 11 && $i <= 31) || $i == 127) exit 1 }
    '; then
        return 2
    fi
    awk '
        BEGIN { endpoint_count = 0; list_open = 0 }
        /^[[:space:]]*$/ || /^[[:space:]]*#/ { next }
        /^[A-Za-z][A-Za-z0-9_-]*:($|[ ]+.*$)/ {
            line = $0
            key = line
            sub(/:.*/, "", key)
            if (seen[key]++) exit 2
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
    resource_root_real=$(readlink -f "$RESOURCE_ROOT")
    : >"$files_tmp"
    for package_dir in "$RESOURCE_ROOT"/*; do
        [ -d "$package_dir" ] || continue
        [ ! -L "$package_dir" ] || continue
        for resource_dir in "$package_dir"/*; do
            [ -d "$resource_dir" ] || continue
            [ ! -L "$resource_dir" ] || continue
            [ -f "$resource_dir/mcp.yml" ] || continue
            [ ! -L "$resource_dir/mcp.yml" ] || continue
            file_identity=$(stat -Lc '%d:%i' "$resource_dir/mcp.yml" 2>/dev/null || true)
            [ -n "$file_identity" ] || continue
            printf '%s\t%s\n' "$resource_dir/mcp.yml" "$file_identity" >>"$files_tmp"
        done
    done
    LC_ALL=C sort -o "$files_tmp" "$files_tmp"
else
    : >"$files_tmp"
fi

tab=$(printf '\t')
while IFS="$tab" read -r file expected_identity; do
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

    # Pin the resource to an open descriptor before validating its origin.
    # Replacing the pathname afterwards cannot redirect reads from this FD.
    if ! exec 3<"$file"; then
        echo "[mcp-proxy] skip $package_id/$resource_id: cannot open mcp.yml" >&2
        continue
    fi
    opened_identity=$(stat -Lc '%d:%i' "/proc/$$/fd/3" 2>/dev/null || true)
    if [ -z "$opened_identity" ] || [ "$opened_identity" != "$expected_identity" ]; then
        exec 3<&-
        echo "[mcp-proxy] skip $package_id/$resource_id: resource changed after discovery" >&2
        continue
    fi
    expected_file="$resource_root_real/$package_id/$resource_id/mcp.yml"
    opened_file=$(readlink -f "/proc/$$/fd/3" 2>/dev/null || true)
    if [ "$opened_file" != "$expected_file" ]; then
        exec 3<&-
        echo "[mcp-proxy] skip $package_id/$resource_id: resource escaped projection root" >&2
        continue
    fi
    if ! cat <&3 >"$snapshot_tmp"; then
        exec 3<&-
        echo "[mcp-proxy] skip $package_id/$resource_id: cannot snapshot mcp.yml" >&2
        continue
    fi
    exec 3<&-

    # Pin the private snapshot to an FD and unlink its pathname before parsing.
    # Both validation passes reopen this descriptor through procfs, so pathname
    # replacement cannot change the bytes between validation and parsing.
    if ! exec 4<"$snapshot_tmp"; then
        rm -f "$snapshot_tmp"
        echo "[mcp-proxy] skip $package_id/$resource_id: cannot open snapshot" >&2
        continue
    fi
    rm -f "$snapshot_tmp"
    if ! endpoint=$(read_endpoint "/proc/$$/fd/4"); then
        exec 4<&-
        echo "[mcp-proxy] skip $package_id/$resource_id: malformed or unsupported mcp.yml" >&2
        continue
    fi
    exec 4<&-

    case "$endpoint" in
        /*) ;;
        *) echo "[mcp-proxy] skip $package_id/$resource_id: endpoint must be absolute" >&2; continue ;;
    esac
    case "$endpoint" in
        *..*|*://*|*%*|*[!A-Za-z0-9._~/?\&=+,:-]*)
            echo "[mcp-proxy] skip $package_id/$resource_id: unsafe endpoint" >&2
            continue
            ;;
    esac

    proxy_path="/lazycat-mcp/$package_id/$resource_id"
    cat >>"$nginx_tmp" <<EOF

location = $proxy_path {
    proxy_pass http://lazycat-ticket-lease:8787/internal/proxy;
    proxy_set_header X-Internal-Token "$MCP_INTERNAL_TOKEN";
    proxy_set_header X-LazyCat-Target http://app.$package_id.lzcx$endpoint;
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
trap - 0 HUP INT TERM

echo "[mcp-proxy] generated $(grep -c '^location = /lazycat-mcp/.* {' "$NGINX_OUTPUT") route entries"
