#!/usr/bin/env python3
"""Generate a repaired administrator override; never write host config automatically."""
import argparse
import copy
from pathlib import Path
import yaml


def merge(admin, packaged):
    result = copy.deepcopy(admin or {})
    services = result.setdefault('services', {})
    target = services.setdefault('hermes-webui', {})
    required = packaged['services']['hermes-webui']
    for key in ('cap_add', 'devices', 'volumes'):
        values = list(target.get(key) or [])
        for item in required.get(key, []):
            if item not in values:
                # Do not silently introduce conflicting destination mounts.
                if key in ('devices', 'volumes'):
                    destination = item.split(':')[1]
                    for existing in values:
                        dest = (existing.get('target') if isinstance(existing, dict)
                                else existing.split(':')[1])
                        if dest == destination:
                            raise ValueError(f'conflicting {key} target {destination}; review manually')
                values.append(item)
        target[key] = values
    if 'SYS_ADMIN' in (target.get('cap_drop') or []):
        raise ValueError('administrator explicitly drops SYS_ADMIN; review manually')
    return result


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
