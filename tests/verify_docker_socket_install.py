"""Disposable container acceptance; run on the Docker host so bind sources exist."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', default='docker')
    parser.add_argument('--image', required=True)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--upstream-directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    token = uuid.uuid4().hex[:12]
    label = f'hermes.relay-install-test={token}'
    containers = []
    report = {'image': args.image, 'scenarios': {}, 'network': 'none', 'published_ports': False}

    def docker(*command, check=True):
        result = subprocess.run(
            [args.engine, *command], text=True, capture_output=True, timeout=40,
        )
        if check and result.returncode:
            raise RuntimeError(f'{command[0]} failed: {result.stdout}\n{result.stderr}')
        return result

    def inspect(cid):
        return json.loads(docker('inspect', cid).stdout)[0]

    def wait_health(cid, expected):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            state = inspect(cid)['State']
            if state.get('Health', {}).get('Status') == expected:
                return state['Health']['Status']
            if not state['Running']:
                raise RuntimeError(docker('logs', cid).stdout)
            time.sleep(.2)
        raise RuntimeError(f'health did not reach {expected}: {state}')

    def start(name, command, mounts, health):
        invocation = [
            'run', '-d', '--name', f'hermes-relay-{token}-{name}', '--label', label,
            '--network', 'none', '--health-cmd', health,
            '--health-interval', '1s', '--health-timeout', '2s',
            '--health-retries', '2', '--health-start-period', '1s',
            '-e', 'PORT=8648', '-e', 'HOME=/tmp/relay-install-home',
            '-e', 'HERMES_HOME=/tmp/relay-install-home/hermes',
            '-e', 'HERMES_WEB_UI_HOME=/tmp/relay-install-home/studio',
            '--mount', f'type=bind,src={args.content.resolve()},dst=/lzcapp/pkg/content,readonly',
        ]
        for mount in mounts:
            invocation.extend(['--mount', mount])
        invocation.extend(['--entrypoint', command[0], args.image, *command[1:]])
        cid = docker(*invocation).stdout.strip()
        containers.append(cid)
        return cid

    script = '/lzcapp/pkg/content/docker-socket-relay.mjs'
    try:
        with tempfile.TemporaryDirectory(prefix='relay-install-') as temporary:
            root = Path(temporary)
            for mode in ('legacy', 'migrated'):
                shared = root / mode
                shared.mkdir()
                common = [f'type=bind,src={shared},dst=/run/hermes-docker']
                relay_mounts = list(common)
                if mode == 'migrated':
                    relay_mounts.append(
                        f'type=bind,src={args.upstream_directory.resolve()},dst=/run/playground,readonly'
                    )
                relay = start(mode, ['node', script], relay_mounts, f'node {script} --check-listener')
                health = wait_health(relay, 'healthy')
                diagnostic = docker('exec', relay, 'node', script, '--check', check=False)
                assert (diagnostic.returncode == 0) == (mode == 'migrated')
                main_mounts = list(common)
                if mode == 'legacy':
                    main_mounts.append(
                        f'type=bind,src={args.upstream_directory.resolve()}/docker.sock,dst=/run/docker.sock'
                    )
                web = start(
                    mode + '-web',
                    ['/bin/sh', '-c', 'sh /lzcapp/pkg/content/link-docker-socket.sh && exec /app/bin/start-studio-all.sh'],
                    main_mounts, 'curl -fsS --max-time 2 http://127.0.0.1:8648/livez',
                )
                web_health = wait_health(web, 'healthy')
                info = json.loads(docker(
                    'exec', web, 'curl', '-fsS', '--unix-socket', '/run/docker.sock', 'http://localhost/info'
                ).stdout)
                assert info['ID']
                is_link = docker('exec', web, 'test', '-L', '/run/docker.sock', check=False).returncode == 0
                assert is_link == (mode == 'migrated')
                for cid in (relay, web):
                    container = inspect(cid)
                    assert container['HostConfig']['NetworkMode'] == 'none'
                    assert not container['HostConfig']['PortBindings']
                report['scenarios'][mode] = {
                    'relay_health': health, 'web_health': web_health,
                    'upstream_diagnostic_exit': diagnostic.returncode,
                    'main_docker_connected': True, 'main_uses_relay': is_link,
                    'daemon_id': info['ID'],
                    'relay_mount_targets': [m['Destination'] for m in inspect(relay)['Mounts']],
                }
                if mode == 'legacy':
                    # Reproduce the released regression with the old health command.
                    old_shared = root / 'old-health'
                    old_shared.mkdir()
                    old = start(
                        'old-health', ['node', script],
                        [f'type=bind,src={old_shared},dst=/run/hermes-docker'],
                        f'node {script} --check',
                    )
                    report['old_health_regression_reproduced'] = wait_health(old, 'unhealthy') == 'unhealthy'
                    docker('rm', '-f', '-v', old)
                    containers.remove(old)
                for cid in (web, relay):
                    docker('rm', '-f', '-v', cid)
                    containers.remove(cid)
            assert report['scenarios']['legacy']['daemon_id'] == report['scenarios']['migrated']['daemon_id']
            report['passed'] = True
    finally:
        for cid in reversed(containers):
            assert inspect(cid)['Config']['Labels'].get('hermes.relay-install-test') == token
            docker('rm', '-f', '-v', cid)
        report['content_sha256'] = {
            name: hashlib.sha256((args.content / name).read_bytes()).hexdigest()
            for name in ('docker-socket-relay.mjs', 'link-docker-socket.sh')
        }
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
