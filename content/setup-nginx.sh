#!/bin/sh
# setup-nginx.sh - 初始化 Nginx 配置
set -e

NGINX_CONF="/etc/nginx/nginx.conf"
SOURCE_CONF="/lzcapp/pkg/content/nginx.conf"
MCP_PROXY_GENERATOR="/lzcapp/pkg/content/generate-lazycat-mcp-proxy.sh"

# 确保目录存在
mkdir -p /etc/nginx

# 复制配置
if [ -f "$SOURCE_CONF" ]; then
    cp "$SOURCE_CONF" "$NGINX_CONF"
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
