#!/usr/bin/env python3
"""Build the Firefox variant of the extension with no new dependencies.

Firefox MV3 has no background service workers; it runs background.scripts
as an event page. The source manifest stays Chromium-clean (the Chrome Web
Store rejects browser_specific_settings), so this tool writes a transformed
manifest for the Firefox zip:

- background.service_worker becomes background.scripts with type module,
  pointing at the same src/background.mjs tree the Chromium worker uses.
  Firefox honors type module for background scripts, so no wrapper is needed.
- browser_specific_settings.gecko is added with the add-on id, a
  strict_min_version of 140.0 (the built-in data consent prompt exists on
  desktop from 140 and on Android from 142), and the data collection
  declaration AMO has required for every new add-on since 2025-11-03. This
  extension collects nothing, so the declaration is required: ["none"].
- minimum_chrome_version is dropped.

The archive is unsigned by design: install it from about:debugging, or
submit it to addons.mozilla.org, which signs approved versions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = [
    'manifest.json',
    'src/background.mjs', 'src/content.js',
    'src/logic.mjs', 'src/library.mjs', 'src/transfer.mjs', 'src/images.mjs',
    'src/popup.html', 'src/popup.css', 'src/popup.mjs',
    'icons/icon16.png', 'icons/icon48.png', 'icons/icon128.png',
    'README.md', 'LICENSE', 'PRIVACY.md', 'SECURITY.md',
]
GECKO_ID = 'fb-pfp@codethor.github.io'
STRICT_MIN_VERSION = '140.0'
STRICT_MIN_VERSION_ANDROID = '142.0'
NO_DATA_COLLECTION = {'required': ['none']}


def firefox_manifest() -> bytes:
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    worker = manifest.pop('background')
    if worker.get('type') != 'module' or not worker.get('service_worker'):
        raise ValueError('Chromium manifest must keep a module service_worker')
    manifest['background'] = {'scripts': [worker['service_worker']], 'type': 'module'}
    manifest.pop('minimum_chrome_version', None)
    manifest['browser_specific_settings'] = {
        'gecko': {
            'id': GECKO_ID,
            'strict_min_version': STRICT_MIN_VERSION,
            'data_collection_permissions': NO_DATA_COLLECTION,
        },
        'gecko_android': {'strict_min_version': STRICT_MIN_VERSION_ANDROID},
    }
    return (json.dumps(manifest, indent=2, ensure_ascii=True) + '\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', default='dist', help='Output directory')
    args = parser.parse_args()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    version = json.loads((ROOT / 'manifest.json').read_text())['version']
    transformed = firefox_manifest()

    path = out / f'fb-pfp-extension-v{version}-firefox.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel in RUNTIME:
            data = transformed if rel == 'manifest.json' else (ROOT / rel).read_bytes()
            zi = zipfile.ZipInfo(rel, (2026, 10, 11, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o100644 << 16
            archive.writestr(zi, data)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        names = archive.namelist()
        assert manifest['background'] == {
            'scripts': ['src/background.mjs'], 'type': 'module',
        }, 'Wrong Firefox background'
        gecko = manifest['browser_specific_settings']['gecko']
        assert gecko['id'] == GECKO_ID, 'Wrong gecko id'
        assert gecko['strict_min_version'] == STRICT_MIN_VERSION, 'Wrong desktop floor'
        assert gecko['data_collection_permissions'] == NO_DATA_COLLECTION, 'Missing AMO data declaration'
        assert manifest['browser_specific_settings']['gecko_android']['strict_min_version'] == STRICT_MIN_VERSION_ANDROID, 'Wrong Android floor'
        assert 'service_worker' not in manifest['background'], 'service_worker leaked into Firefox manifest'
        assert 'minimum_chrome_version' not in manifest, 'Chrome-only key leaked into Firefox manifest'
        assert 'src/background.mjs' in names, 'Background missing'
        assert len(names) == len(set(names)), 'Duplicate archive entries'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f'{path.name}: {path.stat().st_size} bytes, sha256={digest}')
    print('PASS: Firefox ZIP has an event-page module background, gecko id, and the AMO no-data declaration')


if __name__ == '__main__':
    main()
