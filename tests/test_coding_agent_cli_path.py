from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (ROOT / "lzc-manifest.yml").read_text(encoding="utf-8")
MANAGED_BIN = "/home/agent/.hermes-web-ui/coding-agent/npm/bin"


def test_runtime_path_prefers_studio_managed_coding_agents():
    expected = (
        "PATH=" + MANAGED_BIN
        + ":/home/agent/.local/bin:/opt/hermes/.venv/bin:"
        + "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    )
    assert expected in MANIFEST


def test_setup_persists_managed_path_for_login_and_interactive_shells():
    assert "CODING_AGENT_BIN=" + MANAGED_BIN in MANIFEST
    assert "for PROFILE in /home/agent/.profile /home/agent/.bash_profile /home/agent/.bashrc" in MANIFEST
    assert 'grep -Fq "$CODING_AGENT_BIN" "$PROFILE"' in MANIFEST
    assert 'export PATH="%s:/home/agent/.local/bin:$PATH"' in MANIFEST
