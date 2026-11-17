"""Opt-in acceptance against the current local Docker daemon, with disposable containers."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    os.environ.get('DOCKER_RELAY_RUNTIME_TEST') != '1',
    reason='set DOCKER_RELAY_RUNTIME_TEST=1 with cached PostgreSQL/Redis images',
)


def test_real_docker_recovers_after_socket_path_replacement_and_supports_exec():
    upstream = os.environ.get('DOCKER_RELAY_TEST_UPSTREAM', '/var/run/docker.sock')
    run_id = uuid.uuid4().hex[:12]
    env = dict(os.environ)
    for name in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'NODE_OPTIONS'):
        env.pop(name, None)
    # Keep Unix paths below sockaddr_un's length limit.
    with tempfile.TemporaryDirectory(prefix='hdr-') as directory:
        root = Path(directory)
        source, endpoint = root / 'source.sock', root / 'relay.sock'
        source.symlink_to(upstream)
        relay_env = {**env, 'DOCKER_RELAY_LISTEN': str(endpoint), 'DOCKER_RELAY_UPSTREAM': str(source)}
        log = (root / 'relay.log').open('w+')
        process = subprocess.Popen(
            ['node', str(ROOT / 'content/docker-socket-relay.mjs')],
            env=relay_env, stdout=log, stderr=subprocess.STDOUT,
        )
        containers = []

        def docker(*args, input=None):
            try:
                return subprocess.check_output(
                    ['docker', '--host', f'unix://{endpoint}', *args],
                    input=input, env=env, stderr=subprocess.STDOUT, timeout=30,
                )
            except subprocess.CalledProcessError as error:
                if hasattr(error, 'add_note'):
                    error.add_note(error.output.decode(errors='replace'))
                raise

        def health():
            return subprocess.run(
                ['node', str(ROOT / 'content/docker-socket-relay.mjs'), '--check'],
                env=relay_env, capture_output=True, timeout=5,
            ).returncode

        try:
            deadline = time.monotonic() + 5
            while not endpoint.exists():
                assert process.poll() is None, 'relay failed to start'
                assert time.monotonic() < deadline, 'relay socket not created'
                time.sleep(.02)
            before_id = docker('info', '--format', '{{.ID}}').strip()
            assert health() == 0
            source.unlink()
            assert health() != 0
            assert process.poll() is None, 'upstream failure killed the relay'
            source.symlink_to(upstream)
            assert health() == 0
            assert docker('info', '--format', '{{.ID}}').strip() == before_id
            pg = docker(
                'run', '--rm', '-d', '--network', 'none',
                '--label', f'hermes.socket-relay-test={run_id}',
                '--tmpfs', '/var/lib/postgresql:rw,size=256m',
                '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', 'postgres:18.1-alpine3.23',
            ).decode().strip()
            containers.append(pg)
            redis = docker(
                'run', '--rm', '-d', '--network', 'none',
                '--label', f'hermes.socket-relay-test={run_id}',
                '--tmpfs', '/data:rw,size=32m',
                'redis:8.4-alpine', 'redis-server', '--save', '', '--appendonly', 'no',
            ).decode().strip()
            containers.append(redis)
            deadline = time.monotonic() + 20
            while True:
                try:
                    # The image first starts a temporary Unix-only server for
                    # initdb. Wait for the final TCP listener, still confined
                    # to this network=none container, before executing SQL.
                    docker('exec', pg, 'pg_isready', '-h', '127.0.0.1', '-U', 'postgres')
                    break
                except subprocess.CalledProcessError:
                    assert time.monotonic() < deadline, docker('logs', pg).decode()
                    time.sleep(.1)
            result = docker('exec', pg, 'psql', '-h', '127.0.0.1', '-U', 'postgres', '-Atc',
                            'CREATE TEMP TABLE relay_probe(n int); INSERT INTO relay_probe VALUES (20),(22); SELECT sum(n) FROM relay_probe;')
            assert result.decode().splitlines()[-1] == '42'
            assert docker('exec', redis, 'redis-cli', 'PING').strip() == b'PONG'
            assert docker('exec', redis, 'redis-cli', 'SET', 'relay-probe', 'ok').strip() == b'OK'
            assert docker('exec', redis, 'redis-cli', 'GET', 'relay-probe').strip() == b'ok'
            # CLI exec uses HTTP Upgrade and a full-duplex stream, not a normal
            # request/response body. Check binary stdin and a large stdout drain.
            payload = bytes(range(256)) * 8192
            assert docker('exec', '-i', redis, 'cat', input=payload) == payload
            for container in containers:
                info = json.loads(docker('inspect', container))[0]
                assert info['HostConfig']['NetworkMode'] == 'none'
                assert not info['HostConfig']['PortBindings']
        finally:
            try:
                for container in reversed(containers):
                    info = json.loads(docker('inspect', container))[0]
                    assert info['Config']['Labels']['hermes.socket-relay-test'] == run_id
                    docker('stop', '-t', '5', container)
            finally:
                process.terminate()
                process.wait(timeout=5)
                log.close()
