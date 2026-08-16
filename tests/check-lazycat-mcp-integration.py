#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
nginx = (root / "content/nginx.conf").read_text()
setup = (root / "content/setup-nginx.sh").read_text()

required_nginx = [
    "include /etc/nginx/conf.d/lazycat-mcp-generated.conf;",
]
required_setup = [
    'MCP_PROXY_GENERATOR="/lzcapp/pkg/content/generate-lazycat-mcp-proxy.sh"',
    'sh "$MCP_PROXY_GENERATOR"',
    "nginx -t",
]
forbidden = [
    "location /lazycat-mcp/todolist",
    "app.cloud.lazycat.app.todolist.lzcx",
]

missing = [item for item in required_nginx if item not in nginx]
missing += [item for item in required_setup if item not in setup]
present = [item for item in forbidden if item in nginx or item in setup]
if missing:
    print("missing MCP proxy integration:", file=sys.stderr)
    print("\n".join(missing), file=sys.stderr)
    raise SystemExit(1)
if present:
    print("hard-coded MCP provider routes are forbidden:", file=sys.stderr)
    print("\n".join(present), file=sys.stderr)
    raise SystemExit(1)
print("LazyCat MCP proxy integration contract: PASS")
