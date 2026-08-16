#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INJECTOR = ROOT / "content" / "inject-lazycat-mcp-config.py"


class LazyCatMcpConfigInjectionTest(unittest.TestCase):
    def run_injector(self, config_text, providers):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.yaml"
            catalog = root / "providers.json"
            config.write_text(config_text, encoding="utf-8")
            catalog.write_text(json.dumps(providers), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INJECTOR)],
                env={**os.environ, "HERMES_CONFIG_FILE": str(config), "MCP_CATALOG_FILE": str(catalog)},
                text=True,
                capture_output=True,
            )
            return result, config.read_text(encoding="utf-8")

    def test_adds_ticket_free_projected_entries_without_losing_user_config(self):
        provider = {
            "package_id": "cloud.lazycat.app.todo",
            "resource_id": "default",
            "proxy_path": "/lazycat-mcp/cloud.lazycat.app.todo/default",
        }
        result, text = self.run_injector("theme: dark\nmcp_servers:\n  user-server:\n    url: https://example.test/mcp\n", [provider])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("theme: dark", text)
        self.assertIn("user-server:", text)
        self.assertIn("lazycat-projected--cloud.lazycat.app.todo--default:", text)
        self.assertIn("url: http://nginx/lazycat-mcp/cloud.lazycat.app.todo/default", text)
        self.assertNotIn("ticket", text.lower())

    def test_is_idempotent_and_preserves_colliding_user_entry(self):
        provider = {
            "package_id": "cloud.lazycat.app.todo",
            "resource_id": "default",
            "proxy_path": "/lazycat-mcp/cloud.lazycat.app.todo/default",
        }
        config = "mcp_servers:\n  lazycat-projected--cloud.lazycat.app.todo--default:\n    url: https://user.example/mcp\n"
        first, text1 = self.run_injector(config, [provider])
        second, text2 = self.run_injector(text1, [provider])
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(text1, text2)
        self.assertIn("https://user.example/mcp", text2)
        self.assertNotIn("http://nginx/lazycat-mcp/cloud.lazycat.app.todo/default", text2)

    def test_preserves_explicit_disabled_state_for_owned_entry(self):
        provider = {
            "package_id": "cloud.lazycat.app.todo",
            "resource_id": "default",
            "proxy_path": "/lazycat-mcp/cloud.lazycat.app.todo/default",
        }
        config = "mcp_servers:\n  lazycat-projected--cloud.lazycat.app.todo--default:\n    url: http://nginx/lazycat-mcp/cloud.lazycat.app.todo/default\n    enabled: false\n"
        result, text = self.run_injector(config, [provider])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("enabled: false", text)

    def test_invalid_catalog_fails_closed_without_touching_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.yaml"
            catalog = root / "providers.json"
            original = "theme: dark\n"
            config.write_text(original, encoding="utf-8")
            catalog.write_text('[{"package_id":"bad/pkg","resource_id":"default","proxy_path":"/x"}]', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(INJECTOR)],
                env={**os.environ, "HERMES_CONFIG_FILE": str(config), "MCP_CATALOG_FILE": str(catalog)},
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_removes_only_exact_owned_orphans(self):
        config = """mcp_servers:
  lazycat-projected--orphan.pkg--default:
    url: http://nginx/lazycat-mcp/orphan.pkg/default
  lazycat-projected--user:
    url: https://user.example/mcp
"""
        result, text = self.run_injector(config, [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("lazycat-projected--orphan.pkg--default", text)
        self.assertIn("lazycat-projected--user", text)


if __name__ == "__main__":
    unittest.main()
