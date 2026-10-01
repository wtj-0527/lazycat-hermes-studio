from pathlib import Path
import os
import subprocess
import yaml
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def test_mount_fail_stops_before_snapshot():
    script = yaml.safe_load((ROOT / 'lzc-manifest.yml').read_text())['services']['hermes-webui']['setup_script']
    assert script.index('check-rootfs-overlay.sh') < script.index('ROOTFS=')
    assert 'refusing non-persistent startup' in script
    assert 'expected 6 persistent rootfs mounts' in script


def test_probe_failure_cleans_only_disposable_directory(tmp_path):
    script = (ROOT / 'content/check-rootfs-overlay.sh').read_text().replace('/lzcapp/cache/', str(tmp_path) + '/')
    binpath = tmp_path / 'bin'; binpath.mkdir()
    for cmd, status in [('mount', 1), ('umount', 0)]:
        p = binpath / cmd; p.write_text(f'#!/bin/sh\nexit {status}\n'); p.chmod(0o755)
    marker = tmp_path / 'upper'; marker.mkdir(); (marker / 'gh').write_text('preserved')
    env = dict(os.environ, PATH=str(binpath) + ':' + os.environ['PATH'])
    result = subprocess.run(['sh', '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'overlay mount preflight failed' in result.stderr
    assert (marker / 'gh').read_text() == 'preserved'
    assert not list(tmp_path.glob('.overlay-preflight.*'))


def test_merge_preserves_ports_and_rejects_conflicts():
    spec = importlib.util.spec_from_file_location('merge', ROOT / 'tools/merge-admin-override.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    packaged = yaml.safe_load((ROOT / 'lzc-build.yml').read_text())['compose_override']
    admin = {'services': {'nginx': {'ports': ['127.0.0.1:19700:80']}}}
    merged = module.merge(admin, packaged)
    assert merged['services']['nginx']['ports'] == ['127.0.0.1:19700:80']
    assert merged['services']['hermes-webui']['cap_add'] == ['SYS_ADMIN']
    import pytest
    with pytest.raises(ValueError):
        module.merge({'services': {'hermes-webui': {'cap_drop': ['SYS_ADMIN']}}}, packaged)


def test_probe_success_cleans_directory(tmp_path):
    script = (ROOT / 'content/check-rootfs-overlay.sh').read_text().replace('/lzcapp/cache/', str(tmp_path) + '/')
    binpath = tmp_path / 'bin'; binpath.mkdir()
    for cmd in ('mount', 'umount'):
        p = binpath / cmd; p.write_text('#!/bin/sh\nexit 0\n'); p.chmod(0o755)
    result = subprocess.run(['sh', '-c', script], env=dict(os.environ, PATH=str(binpath) + ':' + os.environ['PATH']))
    assert result.returncode == 0
    assert not list(tmp_path.glob('.overlay-preflight.*'))
