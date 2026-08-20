#!/usr/bin/env python3
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "lazycat-projected-mcp-configuration" / "SKILL.md"


class ProjectedMcpSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")

    def test_scans_projection_and_intersects_current_user_visible_apps(self):
        self.assertIn("Select by Current-User Application Visibility", self.text)
        self.assertIn("PackageManager.QueryApplication", self.text)
        self.assertIn("--unix-socket /lzcapp/var/mcp-runtime/lease.sock", self.text)
        self.assertIn("http://localhost/internal/visible-apps", self.text)
        self.assertIn("Do not expose this internal endpoint through nginx", self.text)
        self.assertIn("projected package IDs", self.text)
        self.assertIn("current-user-visible application IDs", self.text)
        self.assertIn("SELECTED_FOR_CURRENT_USER", self.text)
        self.assertIn("SKIPPED_NOT_VISIBLE_TO_CURRENT_USER", self.text)

    def test_protocol_probe_is_not_an_entitlement_gate(self):
        self.assertIn("`initialize` and `tools/list` prove MCP protocol reachability only", self.text)
        self.assertIn("must not be used as proof of current-user application entitlement", self.text)
        self.assertNotIn("valid MCP `initialize` followed by `tools/list` is `AUTHORIZED_FOR_CURRENT_USER`", self.text)

    def test_visibility_lookup_fails_closed_without_destructive_cleanup(self):
        self.assertIn("BLOCKED_CURRENT_USER_APP_VISIBILITY_UNKNOWN", self.text)
        self.assertIn("do not install guessed Providers", self.text)
        self.assertIn("Never remove an existing MCP entry merely because", self.text)
        self.assertNotIn("remove a previously managed entry", self.text)

    def test_uses_canonical_lzcx_and_current_user_ticket_path(self):
        self.assertIn("http://app.<package_id>.lzcx<endpoint>", self.text)
        self.assertIn("current instance user's `X-HC-USER-TICKET`", self.text)
        self.assertIn("Do not read, print, persist, or manually construct the ticket", self.text)

    def test_does_not_require_host_or_application_url_discovery(self):
        self.assertIn("Do not call host-only commands such as `lpk-manager`", self.text)
        self.assertIn("Never depend on host `lpk-manager` or human-facing application URLs", self.text)
        self.assertNotIn("Return the User Access Links", self.text)
        self.assertNotIn("clickable application access link", self.text)

    def test_uses_studio_coding_agent_config_paths(self):
        self.assertIn("~/.claude/mcp.json", self.text)
        self.assertIn("~/.codex/config.toml", self.text)
        self.assertIn("~/.pi/agent/mcp.json", self.text)

    def test_ticket_and_provider_failures_are_distinct(self):
        self.assertIn("wrapper HTTP `428`", self.text)
        self.assertIn("upstream HTTP `401` or `403`", self.text)
        self.assertIn("must not invalidate the captured ticket", self.text)


if __name__ == "__main__":
    unittest.main()
