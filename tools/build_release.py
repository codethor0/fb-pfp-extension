#!/usr/bin/env python3
"""Create reproducible, allowlisted extension archives with no personal media."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = [
    'manifest.json',
    'src/background.mjs', 'src/content.js', 'src/logic.mjs', 'src/library.mjs',
    'src/transfer.mjs', 'src/images.mjs', 'src/popup.html', 'src/popup.css',
    'src/popup.mjs', 'icons/icon16.png', 'icons/icon48.png', 'icons/icon128.png',
    'README.md', 'LICENSE', 'PRIVACY.md', 'SECURITY.md',
]
SAFE_TEXT = {'.md', '.json', '.yml', '.yaml', '.html', '.css', '.mjs', '.js', '.py', '.txt', '.sh'}
SAFE_FILES = {'.gitignore', 'LICENSE', 'Makefile'}
SKIP_DIRS = {'.git', '.verify-venv', '.venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache', 'coverage'}
BAD_MARKERS = [r'/Users/(?!you/)[\w.-]+/', r'github_pat_[A-Za-z0-9_]{20,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']


def confirm_file(relative: str) -> bytes:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
        raise ValueError(f'Missing or unsafe file: {relative}')
    data = path.read_bytes()
    if (relative not in {f'icons/icon{x}.png' for x in (16,48,128)} and
            not re.fullmatch(r'docs/(?:demo\.gif|screenshot-[a-z]+\.png)', relative)):
        try:
            text = data.decode('utf-8')
        except UnicodeError as exc:
            raise ValueError(f'Unexpected binary file: {relative}') from exc
        for pattern in BAD_MARKERS:
            if re.search(pattern, text):
                raise ValueError(f'Private data marker in {relative}')
        if '\u2013' in text or '\u2014' in text:
            raise ValueError(f'Unsupported punctuation in {relative}')
    return data


def all_source_paths() -> list[str]:
    files = []
    for path in ROOT.rglob('*'):
        if path.is_dir():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.startswith('.') and part != '.github' and part != '.gitignore' for part in rel.parts):
            continue
        name = rel.as_posix()
        if name.startswith('icons/') and name in RUNTIME:
            files.append(name)
        elif re.fullmatch(r'docs/(?:demo\.gif|screenshot-[a-z]+\.png)', name):
            # Synthetic marketing assets, allowlisted like the icons.
            files.append(name)
        elif path.suffix in SAFE_TEXT or name in SAFE_FILES:
            files.append(name)
        else:
            raise ValueError(f'Unapproved source file: {name}')
    return sorted(files)


def package(out: Path, name: str, files: list[str], prefix: str = '') -> Path:
    path = out / name
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel in files:
            data = confirm_file(rel)
            zi = zipfile.ZipInfo(prefix + rel, (2026, 10, 11, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o100644 << 16
            archive.writestr(zi, data)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), 'Duplicate archive entries'
        assert not any('/.git/' in x or 'profile_pics' in x for x in names), 'Unsafe archive entries'
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='dist', help='Output directory')
    args = parser.parse_args()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    version = json.loads((ROOT / 'manifest.json').read_text())['version']
    source_files = all_source_paths()
    files = [
        package(out, f'fb-pfp-extension-v{version}-store.zip', RUNTIME),
        package(out, f'fb-pfp-extension-v{version}-install.zip', RUNTIME, 'fb-pfp-extension/'),
        package(out, f'fb-pfp-extension-v{version}-source.zip', source_files, 'fb-pfp-extension/'),
    ]
    checksums = []
    for file in files:
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        checksums.append(f'{digest}  {file.name}')
        print(f'{file.name}: {file.stat().st_size} bytes, sha256={digest}')
    (out / f'fb-pfp-extension-v{version}-SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n')
    with zipfile.ZipFile(files[0]) as archive:
        assert 'manifest.json' in archive.namelist() and all(not x.startswith('fb-pfp-extension/') for x in archive.namelist()), 'Store ZIP has wrong root'
    print('PASS: store ZIP has manifest.json at archive root; no extra media or private files')


if __name__ == '__main__':
    main()
