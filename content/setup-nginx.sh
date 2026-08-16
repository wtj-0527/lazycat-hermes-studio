#!/bin/sh
# setup-nginx.sh - 初始化 Nginx 配置
set -e

NGINX_CONF="/etc/nginx/nginx.conf"
SOURCE_CONF="/lzcapp/pkg/content/nginx.conf"
MCP_PROXY_GENERATOR="/lzcapp/pkg/content/generate-lazycat-mcp-proxy.sh"
MCP_RUNTIME_DIR="/lzcapp/var/mcp-runtime"
MCP_TOKEN_FILE="$MCP_RUNTIME_DIR/internal-token"

# 确保目录存在并创建实例内 MCP 内部认证随机值。
umask 077
mkdir -p /etc/nginx "$MCP_RUNTIME_DIR"
if [ ! -s "$MCP_TOKEN_FILE" ]; then
    od -An -N32 -tx1 /dev/urandom | tr -d " \n" >"$MCP_TOKEN_FILE.tmp"
    mv "$MCP_TOKEN_FILE.tmp" "$MCP_TOKEN_FILE"
fi
MCP_INTERNAL_TOKEN=$(cat "$MCP_TOKEN_FILE")
export MCP_INTERNAL_TOKEN
export MCP_CATALOG_OUTPUT="$MCP_RUNTIME_DIR/providers.json"

# 复制配置
if [ -f "$SOURCE_CONF" ]; then
    sed "s|__MCP_INTERNAL_TOKEN__|$MCP_INTERNAL_TOKEN|g" "$SOURCE_CONF" >"$NGINX_CONF"
    echo "[setup] nginx.conf copied to $NGINX_CONF"
else
    echo "[setup] WARNING: $SOURCE_CONF not found"
fi

# 开发模式：使用自定义配置
if [ "$DEV_ENABLE" = "1" ] && [ -f "/home/agent/.hermes-studio/nginx.conf" ]; then
    cp "/home/agent/.hermes-studio/nginx.conf" "$NGINX_CONF"
    echo "[setup] Dev mode: using custom nginx.conf"
fi

# 只从 LazyCat 运行时投影的 mcp.yml 生成 allowlist 路由。
if [ -f "$MCP_PROXY_GENERATOR" ]; then
    sh "$MCP_PROXY_GENERATOR"
else
    echo "[setup] WARNING: MCP proxy generator not found"
fi

# setup_script 结束前验证最终 Nginx 配置，失败则阻止使用无效配置。
nginx -t

echo "[setup] Nginx setup complete"
