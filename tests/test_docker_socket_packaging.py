import importlib.util
import os
from pathlib import Path
import socket
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_directory_mount_is_limited_to_relay_and_health_does_not_gate_studio():
    manifest = yaml.safe_load((ROOT / 'lzc-manifest.yml').read_text())
    override = yaml.safe_load((ROOT / 'lzc-build.yml').read_text())['compose_override']
    services = manifest['services']
    relay = services['docker-socket-relay']
    webui = services['hermes-webui']
    assert relay['image'] == webui['image']
    assert relay['entrypoint'] == '/usr/local/bin/node /lzcapp/pkg/content/docker-socket-relay.mjs'
    assert override['services']['docker-socket-relay']['volumes'] == [
        '/data/playground:/run/playground:ro'
    ]
    assert not override['services']['hermes-webui'].get('volumes')
    shared = '/lzcapp/var/docker-runtime:/run/hermes-docker'
    assert shared in relay['binds'] and shared in webui['binds']
    assert not any('playground' in bind for bind in webui['binds'])
    assert '--check' in relay['healthcheck']['test']
    assert webui['healthcheck']['test'] == [
        'CMD', 'curl', '-f', 'http://127.0.0.1:8648/livez'
    ]
    assert 'depends_on' not in webui
    assert 'depends_on' not in override['services']['hermes-webui']
    assert not relay.get('ports')
    assert not override['services']['docker-socket-relay'].get('ports')
    assert manifest['application']['health_check']['test_url'] == 'http://hermes-webui:8648'
    setup = webui['setup_script']
    assert setup.index('link-docker-socket.sh') < setup.index('docker info')
    # Packaged runtime and ticket sidecar must share the same pinned image.
    assert relay['image'] == services['lazycat-ticket-lease']['image']


def link(client, upstream):
    return subprocess.run(
        ['sh', str(ROOT / 'content/link-docker-socket.sh')],
        env={**os.environ, 'DOCKER_CLIENT_SOCKET': str(client), 'DOCKER_RELAY_LISTEN': str(upstream)},
        text=True, capture_output=True, timeout=3,
    )


def test_default_endpoint_tracks_relay_socket_replacement_and_link_is_idempotent(tmp_path):
    client, relay = tmp_path / 'docker.sock', tmp_path / 'relay.sock'
    # Setup may finish before the sidecar starts; a dangling link is intentional.
    assert link(client, relay).returncode == 0
    assert client.is_symlink()
    assert link(client, relay).returncode == 0
    with socket.socket(socket.AF_UNIX) as first, socket.socket(socket.AF_UNIX) as second:
        first.bind(str(relay))
        old = client.stat().st_ino
        relay.unlink()
        second.bind(str(relay))
        assert client.stat().st_ino != old
        assert client.stat().st_ino == relay.stat().st_ino


@pytest.mark.parametrize('kind', ['file', 'socket', 'symlink'])
def test_setup_does_not_destroy_existing_custom_endpoint(tmp_path, kind):
    client, relay = tmp_path / 'docker.sock', tmp_path / 'relay.sock'
    listener = None
    if kind == 'file':
        client.write_text('preserve')
    elif kind == 'socket':
        listener = socket.socket(socket.AF_UNIX)
        listener.bind(str(client))
    else:
        client.symlink_to(tmp_path / 'custom.sock')
    before = client.lstat()
    try:
        result = link(client, relay)
        assert result.returncode == 1
        assert 'leaving it intact' in result.stderr
        assert client.lstat().st_ino == before.st_ino
    finally:
        if listener is not None:
            listener.close()


def merger():
    spec = importlib.util.spec_from_file_location('merge_override', ROOT / 'tools/merge-admin-override.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.merge


@pytest.mark.parametrize('legacy', [
    '/data/playground/docker.sock:/var/run/docker.sock',
    {'type': 'bind', 'source': '/data/playground/docker.sock', 'target': '/run/docker.sock'},
])
def test_admin_override_migration_preserves_custom_settings_and_adds_relay(legacy):
    packaged = yaml.safe_load((ROOT / 'lzc-build.yml').read_text())['compose_override']
    admin = {'services': {
        'nginx': {'ports': ['127.0.0.1:19700:80']},
        'hermes-webui': {'volumes': [legacy, '/custom/data:/custom/data:ro']},
    }}
    merged = merger()(admin, packaged)
    assert merged['services']['nginx'] == admin['services']['nginx']
    assert merged['services']['hermes-webui']['volumes'] == ['/custom/data:/custom/data:ro']
    assert merged['services']['hermes-webui']['cap_add'] == ['SYS_ADMIN']
    assert merged['services']['hermes-webui']['devices'] == ['/dev/fuse:/dev/fuse']
    assert merged['services']['docker-socket-relay']['volumes'] == ['/data/playground:/run/playground:ro']
    assert admin['services']['hermes-webui']['volumes'][0] == legacy
    assert merger()(merged, packaged) == merged


@pytest.mark.parametrize('services', [
    {'hermes-webui': {'volumes': ['/custom/docker.sock:/var/run/docker.sock']}},
    {'docker-socket-relay': {'volumes': ['/wrong:/run/playground:ro']}},
    {'docker-socket-relay': {'volumes': ['/data/playground:/run/playground:rw']}},
])
def test_conflicting_admin_mounts_require_review(services):
    packaged = yaml.safe_load((ROOT / 'lzc-build.yml').read_text())['compose_override']
    with pytest.raises(ValueError, match='review manually'):
        merger()({'services': services}, packaged)


def test_equivalent_long_form_relay_mount_is_preserved():
    packaged = yaml.safe_load((ROOT / 'lzc-build.yml').read_text())['compose_override']
    existing = {'type': 'bind', 'source': '/data/playground', 'target': '/run/playground',
                'read_only': True, 'bind': {'create_host_path': False}}
    admin = {'services': {'docker-socket-relay': {'volumes': [existing]}}}
    merged = merger()(admin, packaged)
    assert merged['services']['docker-socket-relay']['volumes'] == [existing]


def test_bundled_admin_migration_tool_matches_the_tested_tool():
    assert (ROOT / 'content/merge-admin-override.py').read_bytes() == (
        ROOT / 'tools/merge-admin-override.py'
    ).read_bytes()
