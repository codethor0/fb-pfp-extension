#!/usr/bin/env python3
"""Installed-extension acceptance test for the Firefox package on macOS.

Builds the real Firefox ZIP with tools/build_firefox.py, launches the
rebranded Gecko build that macOS 27 allows (the default Firefox app-data
dir is TCC-protected for CLI-spawned processes; see
microsoft/playwright#42768), and temporarily installs the package through
WebDriver BiDi, the one supported automation surface that accepts an
unsigned build. The test proves the exact release archive parses, installs,
and boots its real event page in Firefox.

Usage:
    python3 tools/firefox_acceptance.py

Known platform limit: neither the Juggler harness nor WebDriver BiDi will
navigate to moz-extension pages in this build, so the popup Download button
cannot be exercised against the installed extension here. That check stays
NOT TESTED on Firefox (it is covered on real Chromium and real Edge, and
the production export code runs in the real Firefox DOM in CI through
tools/popup_smoke.py). This harness reports what it proves and never marks
untested behavior as passing.

Everything the run creates (profile, build output under dist/) is removed
on exit. The user's Firefox profile and Downloads folder are never touched.
"""

import base64
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GECKO_ID = 'fb-pfp@codethor0.github.io'
BIDI_PORT = 9225
CHECKS = []


def ok(name, detail=''):
    CHECKS.append((name, detail))
    print(f'PASS: {name}' + (f' ({detail})' if detail else ''))


def fail(name, detail):
    print(f'FAIL: {name}: {detail}')
    sys.exit(1)


def build_package():
    run = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_firefox.py')],
                         capture_output=True, text=True, cwd=ROOT)
    if run.returncode != 0:
        fail('build', f'build_firefox.py exited {run.returncode}: {run.stderr.strip()[:300]}')
    zips = sorted((ROOT / 'dist').glob('fb-pfp-extension-v*-firefox.zip'),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        fail('build', 'no Firefox zip produced')
    ok('firefox package built', f'{zips[0].name} {zips[0].stat().st_size} bytes')
    return zips[0]


def bidi_install(port, package, profile):
    """Install the built package through WebDriver BiDi.

    Firefox 155 appDisables unsigned extensions registered directly in the
    profile database even with signature checks relaxed, while temporary
    installs through the supported automation surface load without signing.
    RemoteAgent speaks WebDriver BiDi on --remote-debugging-port, and its
    webExtension.install command accepts the built archive as base64. The
    websockets client runs on its own event loop in a thread because the
    playwright API owns the main loop.

    Returns the addon's internal UUID read back from the profile prefs,
    which doubles as proof the extension activated (Firefox assigns the
    UUID at load time).
    """
    import asyncio
    import re
    try:
        import websockets
    except ImportError:
        fail('bidi install', 'the websockets package is required for the BiDi step')

    payload = base64.b64encode(package.read_bytes()).decode()
    outcome = {}

    async def session():
        async with websockets.connect(f'ws://localhost:{port}/session',
                                      max_size=None) as ws:
            counter = 0

            async def command(method, params=None):
                nonlocal counter
                counter += 1
                await ws.send(json.dumps(
                    {'id': counter, 'method': method, 'params': params or {}}))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get('id') == counter:
                        return message

            await command('session.new',
                          {'capabilities': {'alwaysMatch': {'browserName': 'firefox'}}})
            reply = await command(
                'webExtension.install',
                {'extensionData': {'type': 'base64', 'value': payload}})
            if reply.get('type') != 'success':
                fail('bidi install', f'webExtension.install failed {reply}')
            outcome['id'] = reply['result']['extension']
            # Wait for Firefox to load the addon far enough to assign its
            # internal UUID and persist it to the profile.
            deadline = time.time() + 60
            uuid = None
            while time.time() < deadline:
                prefs = profile / 'prefs.js'
                if prefs.exists():
                    for line in prefs.read_text(errors='replace').splitlines():
                        if 'extensions.webextensions.uuids' not in line:
                            continue
                        match = re.search(r'uuids", "(.*)"\);', line)
                        if not match:
                            continue
                        try:
                            uuids = json.loads(json.loads(f'"{match.group(1)}"'))
                        except ValueError:
                            continue
                        uuid = uuids.get(GECKO_ID) or uuid
                if uuid:
                    break
                await asyncio.sleep(0.5)
            outcome['uuid'] = uuid

    def run():
        try:
            asyncio.run(session())
        except SystemExit:
            raise
        except Exception as exc:
            fail('bidi install', str(exc)[:300])

    thread = threading.Thread(target=run)
    thread.start()
    thread.join(timeout=180)
    if thread.is_alive():
        fail('bidi install', 'BiDi session never completed')
    if outcome.get('id') != GECKO_ID:
        fail('bidi install', f'unexpected addon id {outcome.get("id")}')
    if not outcome.get('uuid'):
        fail('bidi install', 'internal UUID never appeared; the addon did not activate')
    ok('extension temporarily installed from the built package',
       f'{outcome["id"]} uuid {outcome["uuid"]}')
    return outcome['uuid']


def event_page_booted(profile):
    """Confirm the real extension code executed inside Firefox.

    IndexedDB-backed extension storage is migrated lazily by the event page
    the first time the extension runs; the migration pref for our id only
    appears if the real background module booted and touched storage.
    """
    prefs = profile / 'prefs.js'
    if not prefs.exists():
        fail('event page', 'prefs.js missing')
    if f'ExtensionStorageIDB.migrated.{GECKO_ID}' not in prefs.read_text(errors='replace'):
        fail('event page', 'extension storage migration pref never appeared')
    ok('real event page booted (extension storage migration recorded)')


def main():
    tmp = Path(tempfile.mkdtemp(prefix='fb-pfp-firefox-'))
    profile = tmp / 'profile'
    profile.mkdir()
    package = build_package()
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from browser_smoke import rebranded_gecko_launcher
        from playwright.sync_api import sync_playwright
        with sync_playwright() as play:
            launcher = rebranded_gecko_launcher(play)
            (profile / 'user.js').write_text(
                'user_pref("remote.enabled", true);\n'
                'user_pref("remote.active", true);\n')
            context = play.firefox.launch_persistent_context(
                str(profile), executable_path=str(launcher), headless=True,
                args=[f'--remote-debugging-port={BIDI_PORT}'])
            try:
                ok('firefox launched', context.browser.version)
                bidi_install(BIDI_PORT, package, profile)
                event_page_booted(profile)
            finally:
                context.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(ROOT / 'dist', ignore_errors=True)

    print('NOTE: popup Download button acceptance is NOT TESTED on Firefox: '
          'neither Juggler nor WebDriver BiDi will navigate to moz-extension '
          'pages in this build. The export download is accepted on real '
          'Chromium and real Edge, and the production export code runs in the '
          'real Firefox DOM in CI via tools/popup_smoke.py.')
    print(f'ACCEPTANCE: {len(CHECKS)} checks passed on the Firefox package')


if __name__ == '__main__':
    main()
