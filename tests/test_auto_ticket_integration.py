#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

import yaml

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

    def test_manifest_dynamically_scopes_canonical_mcp_hosts_without_global_http_proxy(self):
        manifest = (ROOT / "lzc-manifest.yml").read_text()
        self.assertNotRegex(manifest, r"(?m)^\s*-\s*(?:HTTP_PROXY|http_proxy|HTTPS_PROXY|https_proxy)=")
        self.assertIn("ORIGINAL_URL_PROXY_PORT=80", manifest)
        self.assertNotIn("ORIGINAL_MCP_HOST=", manifest)
        self.assertNotIn("wtj.manager.", manifest)
        self.assertNotIn("lazycat-agent-browser-skill.lzcapp", manifest)
        self.assertIn("/lzcapp/var/mcp-runtime:/lzcapp/var/mcp-runtime", manifest)
        self.assertNotIn("entrypoint:", yaml.safe_load(manifest)["services"]["hermes-webui"])
        self.assertIn("NODE_OPTIONS=--import=/lzcapp/pkg/content/lazycat-original-url-proxy.mjs", manifest)
        webui_setup = yaml.safe_load(manifest)["services"]["hermes-webui"]["setup_script"]
        self.assertIn("generate-lazycat-mcp-proxy.sh", webui_setup)
        self.assertIn("MCP_HOSTS_OUTPUT", webui_setup)
        self.assertIn("/etc/hosts", webui_setup)
        self.assertIn("127.0.0.1", webui_setup)
        proxy = (ROOT / "content" / "lazycat-original-url-proxy.mjs").read_text()
        self.assertIn("server.listen(listenPort, '127.0.0.1'", proxy)
        self.assertNotIn("0.0.0.0", proxy)

    def test_services_never_mix_setup_script_with_entrypoint_or_command(self):
        manifest = yaml.safe_load((ROOT / "lzc-manifest.yml").read_text())
        for name, service in manifest["services"].items():
            if "setup_script" not in service:
                continue
            self.assertNotIn("entrypoint", service, name)
            self.assertNotIn("command", service, name)

    def test_bootstrap_only_captures_and_renews_ticket(self):
        script = (ROOT / "content" / "lazycat-mcp-bootstrap.js").read_text()
        self.assertIn("/lazycat-mcp/capture", script)
        self.assertIn("capture.ok", script)
        self.assertIn("capture.renew.ok", script)
        self.assertNotIn("/api/hermes/mcp/servers", script)
        self.assertNotIn("/api/hermes/mcp/reload", script)
        self.assertNotIn("hermes_api_key", script)
        self.assertNotIn("Authorization", script)
        self.assertNotIn("X-Hermes-Profile", script)
        self.assertNotIn("/lazycat-mcp/providers.json", script)
        self.assertNotIn("config.yaml", script)
        self.assertNotIn("X-HC-USER-TICKET", script)
        self.assertNotIn("document.cookie", script)


if __name__ == "__main__":
    unittest.main()
