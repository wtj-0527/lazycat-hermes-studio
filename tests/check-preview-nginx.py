#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else "content/nginx.conf")
text = path.read_text()
required = [
    "map $http_x_forwarded_host $effective_forwarded_host {",
    '""      $http_host;',
    "default $http_x_forwarded_host;",
    "map $effective_forwarded_host $upstream_port {",
    "map $upstream_port $upstream_host {",
    "8651    localhost:8651;",
    "default $effective_forwarded_host;",
    "proxy_set_header Host $upstream_host;",
    "proxy_set_header X-Forwarded-Host $effective_forwarded_host;",
    "proxy_http_version 1.1;",
    "proxy_set_header Upgrade $http_upgrade;",
    "proxy_set_header Connection $connection_upgrade;",
]
forbidden = [
    "location /preview/ {",
    "proxy_pass http://hermes-webui:8651/;",
    "map $http_x_forwarded_host $upstream_port {",
    "proxy_set_header X-Forwarded-Host $http_x_forwarded_host;",
]
missing = [directive for directive in required if directive not in text]
present = [directive for directive in forbidden if directive in text]
if missing:
    print("missing expected nginx directives:", file=sys.stderr)
    print("\n".join(missing), file=sys.stderr)
    raise SystemExit(1)
if present:
    print("deprecated nginx directives are still present:", file=sys.stderr)
    print("\n".join(present), file=sys.stderr)
    raise SystemExit(1)
print("preview nginx contract: PASS")
