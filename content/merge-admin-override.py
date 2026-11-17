#!/usr/bin/env python3
"""Generate a repaired administrator override; never write host config automatically."""
import argparse
import copy
from pathlib import Path
import yaml


def merge(admin, packaged):
    result = copy.deepcopy(admin or {})
    services = result.setdefault('services', {})
    webui = services.setdefault('hermes-webui', {})
    # Retire only our known old bind in the generated candidate. A custom
    # endpoint needs explicit review, not silent removal or a hidden fallback.
    volumes = []
    for item in webui.get('volumes') or []:
        source, destination = mount_paths(item)
        if destination in ('/run/docker.sock', '/var/run/docker.sock'):
            if source != '/data/playground/docker.sock':
                raise ValueError(f'custom Docker endpoint {destination}; review manually')
            continue
        volumes.append(item)
    if 'volumes' in webui:
        webui['volumes'] = volumes
    for name, required in packaged['services'].items():
        target = services.setdefault(name, {})
        for key in ('cap_add', 'devices', 'volumes'):
            if key not in required:
                continue
            values = list(target.get(key) or [])
            for item in required[key]:
                if item not in values:
                    if key == 'volumes' and any(
                        mount_paths(existing) == mount_paths(item)
                        and mount_read_only(existing) == mount_read_only(item)
                        for existing in values
                    ):
                        continue
                    if key in ('devices', 'volumes'):
                        _, destination = mount_paths(item)
                        for existing in values:
                            if mount_paths(existing)[1] == destination:
                                raise ValueError(f'conflicting {name} {key} target {destination}; review manually')
                    values.append(copy.deepcopy(item))
            target[key] = values
    if 'SYS_ADMIN' in (webui.get('cap_drop') or []):
        raise ValueError('administrator explicitly drops SYS_ADMIN; review manually')
    return result


def mount_paths(item):
    if isinstance(item, dict):
        return item.get('source'), item.get('target')
    return tuple(item.split(':')[:2])


def mount_read_only(item):
    if isinstance(item, dict):
        return bool(item.get('read_only', False))
    fields = item.split(':')
    return len(fields) > 2 and 'ro' in fields[2].split(',')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('administrator_override')
    parser.add_argument('packaged_override')
    parser.add_argument('output')
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists():
        parser.error('output already exists; choose a new path')
    admin = yaml.safe_load(Path(args.administrator_override).read_text())
    packaged = yaml.safe_load(Path(args.packaged_override).read_text())
    result = merge(admin, packaged)
    with out.open('x') as f:
        yaml.safe_dump(result, f, sort_keys=False)


if __name__ == '__main__':
    main()
