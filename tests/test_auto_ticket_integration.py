#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AutoTicketIntegrationContract(unittest.TestCase):
    def test_manifest_runs_wrapper_only_ticket_lease_sidecar(self):
        manifest = (ROOT / "lzc-manifest.yml").read_text()
        self.assertIn("multi_instance: true", manifest)
        self.assertIn("lazycat-ticket-lease:", manifest)
        self.assertIn("entrypoint: /bin/sh /lzcapp/pkg/content/start-lazycat-ticket-lease.sh", manifest)
        self.assertIn("SOCKET_PATH=/lzcapp/var/mcp-runtime/lease.sock", manifest)
        self.assertIn("CATALOG_FILE=/lzcapp/var/mcp-runtime/providers.json", manifest)
        self.assertIn("SOCKET_GID=101", manifest)
        self.assertNotIn("TEST_ALLOW_LOOPBACK", manifest)
        lease = (ROOT / "content" / "lazycat-ticket-lease.mjs").read_text()
        self.assertIn("0o660", lease)
        self.assertNotIn("0o666", lease)
        self.assertNotIn("build:", manifest)

    def test_nginx_captures_ticket_and_bootstraps_without_exposing_it(self):
        nginx = (ROOT / "content" / "nginx.conf").read_text()
        self.assertIn("location = /lazycat-mcp/capture", nginx)
        self.assertIn("proxy_pass http://unix:/lzcapp/var/mcp-runtime/lease.sock:/internal/capture", nginx)
        self.assertIn("proxy_set_header X-HC-USER-TICKET $http_x_hc_user_ticket", nginx)
        self.assertIn("location = /lazycat-mcp/bootstrap.js", nginx)
        self.assertIn("sub_filter '</head>'", nginx)
        self.assertIn('script type="module"', nginx)
        self.assertIn('proxy_set_header Accept-Encoding ""', nginx)
        self.assertNotIn("X-HC-USER-TICKET $cookie_", nginx)
        self.assertNotIn("X-Internal-Token", nginx)

    def test_generator_routes_only_through_lease_with_validated_target(self):
        generator = (ROOT / "content" / "generate-lazycat-mcp-proxy.sh").read_text()
        self.assertIn("proxy_pass http://unix:/lzcapp/var/mcp-runtime/lease.sock:/internal/proxy", generator)
        self.assertIn("proxy_set_header X-LazyCat-Target http://app.$package_id.lzcx$endpoint", generator)
        self.assertNotRegex(generator, r"proxy_pass http://app\.\$package_id\.lzcx\$endpoint")

    def test_wrapper_startup_injects_projected_servers_before_webui(self):
        manifest = (ROOT / "lzc-manifest.yml").read_text()
        self.assertIn("MCP_NGINX_OUTPUT=/tmp/lazycat-mcp-generated.conf", manifest)
        self.assertIn("MCP_CATALOG_OUTPUT=/tmp/lazycat-mcp-providers.json", manifest)
        self.assertIn("sh /lzcapp/pkg/content/generate-lazycat-mcp-proxy.sh", manifest)
        self.assertIn("/opt/hermes/.venv/bin/python /lzcapp/pkg/content/inject-lazycat-mcp-config.py", manifest)

    def test_bootstrap_only_captures_and_renews_ticket(self):
        script = (ROOT / "content" / "lazycat-mcp-bootstrap.js").read_text()
        self.assertIn("/lazycat-mcp/capture", script)
        self.assertIn("setInterval", script)
        self.assertNotIn("/api/hermes/mcp/servers", script)
        self.assertNotIn("/api/hermes/mcp/reload", script)
        self.assertNotIn("X-HC-USER-TICKET", script)
        self.assertNotIn("document.cookie", script)


if __name__ == "__main__":
    unittest.main()
