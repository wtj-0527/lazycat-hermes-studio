#!/opt/hermes/.venv/bin/python
"""Idempotently inject ticket-free LazyCat MCP routes into Hermes config."""
import fcntl
import json
import os
import re
import tempfile
from pathlib import Path

import yaml

PREFIX = "lazycat-projected--"
ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
PKG_RE = re.compile(r"^[A-Za-z0-9.-]+$")


def managed_name(provider):
    return PREFIX + f"{provider['package_id']}--{provider['resource_id']}"


def expected_url(package_id, resource_id):
    return f"http://nginx/lazycat-mcp/{package_id}/{resource_id}"


def is_owned(name, config):
    if not isinstance(name, str) or not name.startswith(PREFIX) or not isinstance(config, dict):
        return False
    if set(config) - {"url", "enabled"}:
        return False
    suffix = name[len(PREFIX):]
    if "--" not in suffix:
        return False
    package_id, resource_id = suffix.rsplit("--", 1)
    if not PKG_RE.fullmatch(package_id) or not ID_RE.fullmatch(resource_id):
        return False
    return config.get("url") == expected_url(package_id, resource_id)


def load_desired(catalog_path):
    providers = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(providers, list):
        raise ValueError("provider catalog must be an array")
    desired = {}
    for provider in providers:
        if not isinstance(provider, dict):
            raise ValueError("provider entry must be an object")
        package_id = provider.get("package_id")
        resource_id = provider.get("resource_id")
        proxy_path = provider.get("proxy_path")
        if not isinstance(package_id, str) or not PKG_RE.fullmatch(package_id):
            raise ValueError("invalid provider package_id")
        if not isinstance(resource_id, str) or not ID_RE.fullmatch(resource_id):
            raise ValueError("invalid provider resource_id")
        expected_path = f"/lazycat-mcp/{package_id}/{resource_id}"
        if proxy_path != expected_path:
            raise ValueError("provider proxy_path mismatch")
        desired[managed_name(provider)] = {"url": f"http://nginx{expected_path}"}
    return desired


def atomic_save(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.safe_dump(config, stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main():
    config_path = Path(os.environ.get("HERMES_CONFIG_FILE", "/home/agent/.hermes/config.yaml"))
    catalog_path = Path(os.environ.get("MCP_CATALOG_FILE", "/tmp/lazycat-mcp-providers.json"))
    desired = load_desired(catalog_path)
    lock_path = config_path.with_suffix(config_path.suffix + ".lazycat-mcp.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        else:
            config = {}
        if not isinstance(config, dict):
            raise ValueError("Hermes config root must be an object")
        servers = config.get("mcp_servers") or {}
        if not isinstance(servers, dict):
            raise ValueError("mcp_servers must be an object")
        updated = dict(servers)
        for name, server in list(updated.items()):
            if is_owned(name, server) and name not in desired:
                del updated[name]
        for name, server in desired.items():
            existing = updated.get(name)
            if existing is None:
                updated[name] = server
            elif is_owned(name, existing):
                replacement = dict(server)
                if isinstance(existing.get("enabled"), bool):
                    replacement["enabled"] = existing["enabled"]
                updated[name] = replacement
        if updated:
            config["mcp_servers"] = updated
        else:
            config.pop("mcp_servers", None)
        if updated != servers:
            atomic_save(config_path, config)
            print(f"[lazycat-mcp] reconciled {len(desired)} projected servers")
        else:
            print(f"[lazycat-mcp] projected servers already current ({len(desired)})")


if __name__ == "__main__":
    main()
