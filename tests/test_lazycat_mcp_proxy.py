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
        self.assertIn("proxy_pass http://unix:/lzcapp/var/mcp-runtime/lease.sock:/internal/proxy;", nginx)
        self.assertIn("proxy_set_header X-LazyCat-Target http://app.cloud.lazycat.app.todolist.lzcx/api/mcp;", nginx)
        self.assertIn("location = /lazycat-mcp/community.lazycat.czyt.smarticky/smarticky", nginx)
        self.assertIn("proxy_set_header X-LazyCat-Target http://app.community.lazycat.czyt.smarticky.lzcx/mcp?view=default;", nginx)
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
            ("cloud.lazycat.app.encoded-dot", "default", "endpoint: /api/%2e%2e/admin\n"),
            ("cloud.lazycat.app.encoded-slash", "default", "endpoint: /api%2Fadmin\n"),
            ("cloud.lazycat.app.encoded-backslash", "default", "endpoint: /api%5cadmin\n"),
            ("cloud.lazycat.app.encoded-mixed", "default", "endpoint: /api/%2E%2e/admin\n"),
            ("cloud.lazycat.app.double-encoded", "default", "endpoint: /api/%252e%252e/admin\n"),
            ("cloud.lazycat.app.variable", "default", "endpoint: /mcp?$arg_target\n"),
            ("cloud.lazycat.app.nospace", "default", "endpoint:/should-not-be-a-mapping\n"),
            ("cloud.lazycat.app.tab", "default", "endpoint: /mcp\tbad\n"),
            ("cloud.lazycat.app.control", "default", "name: bad\vvalue\nendpoint: /accepted\n"),
            ("cloud.lazycat.app.duplicate-key", "default", "name: first\nname: second\nendpoint: /accepted\n"),
            ("cloud.lazycat.app.invalid-yaml", "default", "this: [is: not: yaml\nendpoint: /accepted-anyway\n"),
            ("cloud.lazycat.app.nested", "default", "server:\n  endpoint: /nested\n"),
            ("cloud.lazycat.app.multiline", "default", "endpoint: /mcp\nendpoint: /second\n"),
            ("cloud.lazycat.app.missing", "default", "name: missing endpoint\n"),
        ])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cloud.lazycat.app.good", nginx)
        self.assertNotIn("attacker.invalid", nginx)
        self.assertNotIn("cloud.lazycat.app.traversal", nginx)
        self.assertNotIn("cloud.lazycat.app.encoded-dot", nginx)
        self.assertNotIn("cloud.lazycat.app.encoded-slash", nginx)
        self.assertNotIn("cloud.lazycat.app.encoded-backslash", nginx)
        self.assertNotIn("cloud.lazycat.app.encoded-mixed", nginx)
        self.assertNotIn("cloud.lazycat.app.double-encoded", nginx)
        self.assertNotIn("cloud.lazycat.app.variable", nginx)
        self.assertNotIn("cloud.lazycat.app.nospace", nginx)
        self.assertNotIn("cloud.lazycat.app.tab", nginx)
        self.assertNotIn("cloud.lazycat.app.control", nginx)
        self.assertNotIn("cloud.lazycat.app.duplicate-key", nginx)
        self.assertNotIn("cloud.lazycat.app.invalid-yaml", nginx)
        self.assertNotIn("cloud.lazycat.app.nested", nginx)
        self.assertNotIn("cloud.lazycat.app.multiline", nginx)
        self.assertNotIn("cloud.lazycat.app.missing", nginx)
        self.assertIsInstance(catalog, list)
        assert isinstance(catalog, list)
        self.assertEqual([item["package_id"] for item in catalog], ["cloud.lazycat.app.good"])

    def test_empty_resource_tree_still_emits_valid_empty_outputs(self):
        result, nginx, catalog = self.run_generator([])

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generated LazyCat MCP routes", nginx)
        self.assertEqual(catalog, [])

    def test_anchors_each_resource_to_its_discovered_inode(self):
        script = GENERATOR.read_text(encoding="utf-8")
        self.assertIn('exec 3<"$file"', script)
        self.assertIn("stat -Lc '%d:%i'", script)
        self.assertIn('opened_identity" != "$expected_identity', script)
        self.assertIn('readlink -f "/proc/$$/fd/3"', script)
        self.assertIn('cat <&3 >"$snapshot_tmp"', script)
        self.assertIn('exec 4<"$snapshot_tmp"', script)
        self.assertIn('rm -f "$snapshot_tmp"', script)
        self.assertIn('read_endpoint "/proc/$$/fd/4"', script)

    def test_rejects_file_replaced_between_discovery_and_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "resources" / "mcp-providers"
            resource = root / "cloud.lazycat.app.race" / "default"
            resource.mkdir(parents=True)
            mcp_yaml = resource / "mcp.yml"
            mcp_yaml.write_text("endpoint: /original\n", encoding="utf-8")
            output = tmp_path / "generated.conf"
            catalog_path = tmp_path / "providers.json"

            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            real_sort = subprocess.run(
                ["sh", "-c", "command -v sort"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            sort_wrapper = bin_dir / "sort"
            sort_wrapper.write_text(
                "#!/bin/sh\n"
                f'"{real_sort}" "$@"\n'
                'replacement="${RACE_FILE}.replacement"\n'
                "printf 'endpoint: /replaced\\n' >\"$replacement\"\n"
                'mv "$replacement" "$RACE_FILE"\n',
                encoding="utf-8",
            )
            sort_wrapper.chmod(0o755)

            result = subprocess.run(
                ["sh", str(GENERATOR)],
                cwd=REPO,
                env={
                    **os.environ,
                    "PATH": f"{bin_dir}:{os.environ['PATH']}",
                    "RACE_FILE": str(mcp_yaml),
                    "MCP_RESOURCE_ROOT": str(root),
                    "MCP_NGINX_OUTPUT": str(output),
                    "MCP_CATALOG_OUTPUT": str(catalog_path),
                },
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("resource changed after discovery", result.stderr)
            self.assertNotIn("cloud.lazycat.app.race", output.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(catalog_path.read_text(encoding="utf-8")), [])

    def test_rejects_symlinks_that_escape_or_alias_the_resource_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "resources" / "mcp-providers"
            output = tmp_path / "generated.conf"
            catalog_path = tmp_path / "providers.json"
            outside = tmp_path / "outside"
            outside.mkdir()
            (outside / "mcp.yml").write_text("endpoint: /outside\n", encoding="utf-8")

            package = root / "cloud.lazycat.app.symlink"
            package.mkdir(parents=True)
            (package / "resource-dir").symlink_to(outside, target_is_directory=True)

            file_resource = package / "file"
            file_resource.mkdir()
            (file_resource / "mcp.yml").symlink_to(outside / "mcp.yml")

            real_resource = package / "real"
            real_resource.mkdir()
            (real_resource / "mcp.yml").write_text("endpoint: /real\n", encoding="utf-8")
            (root / "cloud.lazycat.app.package-link").symlink_to(package, target_is_directory=True)

            result = subprocess.run(
                ["sh", str(GENERATOR)],
                cwd=REPO,
                env={
                    **os.environ,
                    "MCP_RESOURCE_ROOT": str(root),
                    "MCP_NGINX_OUTPUT": str(output),
                    "MCP_CATALOG_OUTPUT": str(catalog_path),
                },
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            nginx = output.read_text(encoding="utf-8")
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertNotIn("/resource-dir", nginx)
            self.assertNotIn("/file", nginx)
            self.assertNotIn("cloud.lazycat.app.package-link", nginx)
            self.assertIn("/lazycat-mcp/cloud.lazycat.app.symlink/real", nginx)
            self.assertEqual(
                [(item["package_id"], item["resource_id"]) for item in catalog],
                [("cloud.lazycat.app.symlink", "real")],
            )

    def test_snapshot_path_replacement_cannot_change_parsed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "resources" / "mcp-providers"
            resource = root / "cloud.lazycat.app.snapshot" / "default"
            resource.mkdir(parents=True)
            (resource / "mcp.yml").write_text("endpoint: /original\n", encoding="utf-8")
            output = tmp_path / "generated.conf"
            catalog_path = tmp_path / "providers.json"

            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            real_od = subprocess.run(
                ["sh", "-c", "command -v od"], check=True, text=True, capture_output=True
            ).stdout.strip()
            od_wrapper = bin_dir / "od"
            od_wrapper.write_text(
                "#!/bin/sh\n"
                "printf 'endpoint: /replaced\\n' >\"${TMPDIR}/lazycat-mcp-snapshot.$$\"\n"
                f'exec "{real_od}" "$@"\n',
                encoding="utf-8",
            )
            od_wrapper.chmod(0o755)

            result = subprocess.run(
                ["sh", str(GENERATOR)],
                cwd=REPO,
                env={
                    **os.environ,
                    "PATH": f"{bin_dir}:{os.environ['PATH']}",
                    "TMPDIR": str(tmp_path),
                    "MCP_RESOURCE_ROOT": str(root),
                    "MCP_NGINX_OUTPUT": str(output),
                    "MCP_CATALOG_OUTPUT": str(catalog_path),
                },
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            nginx = output.read_text(encoding="utf-8")
            self.assertIn("app.cloud.lazycat.app.snapshot.lzcx/original", nginx)
            self.assertNotIn("/replaced", nginx)


if __name__ == "__main__":
    unittest.main()
