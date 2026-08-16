#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GENERATOR = REPO / "content" / "generate-lazycat-mcp-proxy.sh"


class LazycatMcpProxyGeneratorTest(unittest.TestCase):
    def run_generator(self, providers):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "resources" / "mcp-providers"
            output = Path(tmp) / "generated.conf"
            catalog = Path(tmp) / "providers.json"
            for package_id, resource_id, mcp_yaml in providers:
                target = root / package_id / resource_id
                target.mkdir(parents=True, exist_ok=True)
                (target / "mcp.yml").write_text(mcp_yaml, encoding="utf-8")
            result = subprocess.run(
                ["sh", str(GENERATOR)],
                cwd=REPO,
                env={
                    **os.environ,
                    "MCP_RESOURCE_ROOT": str(root),
                    "MCP_NGINX_OUTPUT": str(output),
                    "MCP_CATALOG_OUTPUT": str(catalog),
                },
                text=True,
                capture_output=True,
            )
            return result, output.read_text() if output.exists() else "", json.loads(catalog.read_text()) if catalog.exists() else None

    def test_generates_exact_allowlisted_routes_and_catalog(self):
        result, nginx, catalog = self.run_generator([
            ("cloud.lazycat.app.todolist", "default", "endpoint: /api/mcp\n"),
            ("community.lazycat.czyt.smarticky", "smarticky", "endpoint: /mcp?view=default\n"),
        ])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("location = /lazycat-mcp/cloud.lazycat.app.todolist/default", nginx)
        self.assertIn("proxy_pass http://app.cloud.lazycat.app.todolist.lzcx/api/mcp;", nginx)
        self.assertIn("proxy_set_header X-HC-USER-TICKET $http_x_hc_user_ticket;", nginx)
        self.assertIn("location = /lazycat-mcp/community.lazycat.czyt.smarticky/smarticky", nginx)
        self.assertIn("proxy_pass http://app.community.lazycat.czyt.smarticky.lzcx/mcp?view=default;", nginx)
        self.assertEqual(
            catalog,
            [
                {
                    "package_id": "cloud.lazycat.app.todolist",
                    "resource_id": "default",
                    "endpoint": "/api/mcp",
                    "proxy_path": "/lazycat-mcp/cloud.lazycat.app.todolist/default",
                },
                {
                    "package_id": "community.lazycat.czyt.smarticky",
                    "resource_id": "smarticky",
                    "endpoint": "/mcp?view=default",
                    "proxy_path": "/lazycat-mcp/community.lazycat.czyt.smarticky/smarticky",
                },
            ],
        )

    def test_skips_unsafe_or_malformed_resources(self):
        result, nginx, catalog = self.run_generator([
            ("cloud.lazycat.app.good", "default", "endpoint: /mcp\n"),
            ("cloud.lazycat.app.bad", "default", "endpoint: http://attacker.invalid/mcp\n"),
            ("cloud.lazycat.app.traversal", "default", "endpoint: /api/../admin\n"),
            ("cloud.lazycat.app.variable", "default", "endpoint: /mcp?$arg_target\n"),
            ("cloud.lazycat.app.nospace", "default", "endpoint:/should-not-be-a-mapping\n"),
            ("cloud.lazycat.app.tab", "default", "endpoint: /mcp\tbad\n"),
            ("cloud.lazycat.app.invalid-yaml", "default", "this: [is: not: yaml\nendpoint: /accepted-anyway\n"),
            ("cloud.lazycat.app.nested", "default", "server:\n  endpoint: /nested\n"),
            ("cloud.lazycat.app.multiline", "default", "endpoint: /mcp\nendpoint: /second\n"),
            ("cloud.lazycat.app.missing", "default", "name: missing endpoint\n"),
        ])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cloud.lazycat.app.good", nginx)
        self.assertNotIn("attacker.invalid", nginx)
        self.assertNotIn("cloud.lazycat.app.traversal", nginx)
        self.assertNotIn("cloud.lazycat.app.variable", nginx)
        self.assertNotIn("cloud.lazycat.app.nospace", nginx)
        self.assertNotIn("cloud.lazycat.app.tab", nginx)
        self.assertNotIn("cloud.lazycat.app.invalid-yaml", nginx)
        self.assertNotIn("cloud.lazycat.app.nested", nginx)
        self.assertNotIn("cloud.lazycat.app.multiline", nginx)
        self.assertNotIn("cloud.lazycat.app.missing", nginx)
        self.assertEqual([item["package_id"] for item in catalog], ["cloud.lazycat.app.good"])

    def test_empty_resource_tree_still_emits_valid_empty_outputs(self):
        result, nginx, catalog = self.run_generator([])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generated LazyCat MCP routes", nginx)
        self.assertEqual(catalog, [])


if __name__ == "__main__":
    unittest.main()
