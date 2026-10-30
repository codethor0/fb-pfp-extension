#!/usr/bin/env python3
"""Installed-extension acceptance test for Microsoft Edge on macOS.

Runs the real unpacked extension (manifest, service worker, popup, content
script, IndexedDB, alarms) in real Microsoft Edge against a local fixture
that impersonates www.facebook.com through --host-resolver-rules, so nothing
touches the network or a real account.

Edge cannot be playwright-launched on macOS (its data-dir name is compiled
into the brand and TCC denies a CLI-spawned process the protected default
dir), so this test launches Edge headless through LaunchServices and connects
over CDP, the same pattern as the DOM battery's CDP_URL path.

Usage:
    python3 tools/edge_acceptance.py

The test drives:
  1. service worker install and settings round-trip
  2. image import through the real popup page into IndexedDB
  3. browser restart: extension storage is verified flushed to disk, and a
     fresh browser session boots and imports cleanly. The cross-restart
     library readback itself cannot run headless (Edge headless uses a
     throwaway scoped profile, and Edge 156 blocks CDP on the default
     profile), so that one assertion is a headed manual acceptance step.
  4. daily-review scheduling through chrome.alarms
  5. the review flow end to end: popup -> worker -> new tab on the mapped
     fixture -> content script stages the photo and verifies the preview,
     with Save never clicked

Prerequisites: Microsoft Edge installed, nothing on port 9223 or 8443.
"""

import http.server
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from browser_smoke import fixture, image_payload  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# A fresh port per run: Edge can leave headless instances behind that ignore
# cleanup, and a stale instance answering a fixed port makes the next run
# attach to the wrong browser. Cleanup resolves the processes that own this
# port and verifies they are Microsoft Edge before signalling anything, so
# no pattern-matched kill can touch an unrelated user process.
CDP_PORT = 9333 + (os.getpid() % 200)
HTTPS_PORT = 8443
CHECKS = []


def ok(name, detail=''):
    CHECKS.append((name, detail))
    print(f'PASS: {name}' + (f' ({detail})' if detail else ''))


def fail(name, detail):
    print(f'FAIL: {name}: {detail}')
    sys.exit(1)


def wait_cdp(timeout=30):
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://localhost:{CDP_PORT}/json/version', timeout=2) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.5)
    fail('edge launch', f'no CDP answer on {CDP_PORT}')


def launch_edge():
    stop_edge()
    rules = f'MAP www.facebook.com 127.0.0.1:{HTTPS_PORT}'
    subprocess.run([
        'open', '-na', 'Microsoft Edge', '--args',
        '--headless=new',
        f'--remote-debugging-port={CDP_PORT}',
        f'--load-extension={ROOT}',
        f'--disable-extensions-except={ROOT}',
        f'--host-resolver-rules={rules}',
        '--ignore-certificate-errors',
        '--no-first-run', '--disable-session-crashed-bubble',
        'about:blank',
    ], check=True)
    info = wait_cdp()
    ok('edge launched headless via LaunchServices', info.get('Browser', ''))


def edge_pids_on_port():
    """PIDs holding the CDP port that verifiably belong to Microsoft Edge.

    Cleanup only ever signals processes resolved from the port this run
    owns, and only after `ps` confirms the process is Edge. No pattern
    matching against command lines, so an unrelated process that happens
    to mention the port number is never touched.
    """
    out = subprocess.run(
        ['lsof', '-nP', '-ti', f':{CDP_PORT}'],
        capture_output=True, text=True).stdout.split()
    pids = []
    for pid in out:
        comm = subprocess.run(
            ['ps', '-p', pid, '-o', 'comm='],
            capture_output=True, text=True).stdout.strip()
        if 'Edge' in comm:
            pids.append(pid)
    return pids


def stop_edge(grace=20):
    for pid in edge_pids_on_port():
        subprocess.run(['kill', '-TERM', pid], check=False)
    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            socket.create_connection(('localhost', CDP_PORT), timeout=1).close()
        except OSError:
            return
        time.sleep(0.5)
    # Anything still holding the port ignored SIGTERM; make sure it is gone
    # before the next launch, or wait_cdp can attach to a stale instance.
    # Re-resolve the owners and verify they are still Edge before SIGKILL:
    # a SIGKILL can cost unflushed extension storage, so it is the last
    # resort after a long grace, never the first move, and it only ever
    # lands on PIDs this function resolved itself.
    for pid in edge_pids_on_port():
        subprocess.run(['kill', '-9', pid], check=False)
    time.sleep(1)


def start_fixture_server(certfile, keyfile):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = fixture().encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', HTTPS_PORT), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(certfile=certfile, keyfile=keyfile)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def make_cert(tmp):
    cert = os.path.join(tmp, 'fb.pem')
    key = os.path.join(tmp, 'fb.key')
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
        '-keyout', key, '-out', cert, '-days', '2',
        '-subj', '/CN=www.facebook.com',
        '-addext', 'subjectAltName=DNS:www.facebook.com',
    ], check=True, capture_output=True)
    return cert, key


def extension_targets(play):
    """Return (extension_id, popup_url) discovered from live targets."""
    for ctx in play.contexts if hasattr(play, 'contexts') else []:
        pass
    return None


def cleanup_scoped_profiles(before, attempts=3):
    """Remove only the scoped headless profiles this run created.

    Edge headless cannot be pointed at a custom data dir on macOS, so
    every launch litters a throwaway scoped_dir* profile under the
    headless data root. Pre-existing directories are never touched;
    only directories that appeared after the run's snapshot are removed,
    with a short retry because Edge tears down asynchronously after its
    debugging port closes.
    """
    root = Path.home() / 'Library/Application Support/Microsoft Edge-headless'
    if not root.is_dir():
        return
    for _ in range(attempts):
        leftovers = [d for d in root.glob('scoped_dir*') if d not in before]
        if not leftovers:
            return
        for d in leftovers:
            shutil.rmtree(d, ignore_errors=True)
        time.sleep(1)


def main():
    tmp = tempfile.mkdtemp(prefix='fb-pfp-edge-')
    scoped_root = Path.home() / 'Library/Application Support/Microsoft Edge-headless'
    scoped_before = set(scoped_root.glob('scoped_dir*')) if scoped_root.is_dir() else set()
    photo = os.path.join(tmp, 'photo.jpg')
    with open(photo, 'wb') as fh:
        import base64
        fh.write(base64.b64decode(image_payload()))
    cert, key = make_cert(tmp)
    server = start_fixture_server(cert, key)

    launch_edge()
    try:
        with sync_playwright() as play:
            browser = play.chromium.connect_over_cdp(f'http://localhost:{CDP_PORT}')
            context = browser.contexts[0]

            # Find the extension's service worker and learn its id.
            worker = None
            deadline = time.time() + 20
            while time.time() < deadline and worker is None:
                # Edge ships its own built-in extensions whose workers also
                # appear here; ours is the only one running our service
                # worker entry.
                workers = [w for w in context.service_workers
                           if w.url.endswith('/src/background.mjs')]
                worker = workers[0] if workers else None
                if worker is None:
                    time.sleep(0.5)
            if worker is None:
                fail('service worker', 'no extension service worker target appeared')
            ext_id = worker.url.split('/')[2]
            ok('service worker installed', f'id {ext_id}')

            # Drive the real popup page: it is an extension page, so its
            # chrome.storage view is the same IndexedDB the worker uses.
            popup = context.new_page()
            popup.goto(f'chrome-extension://{ext_id}/src/popup.html')
            # Round-trip real settings through the real service worker:
            # SAVE_SETTINGS from the popup page writes IndexedDB via the worker.
            roundtrip = popup.evaluate('''async () => {
              const reply = await chrome.runtime.sendMessage(
                {type: 'SAVE_SETTINGS', settings: {mode: 'random', scheduleEnabled: false, scheduleTime: '09:15'}});
              const stored = await chrome.storage.local.get('settings');
              return {ok: reply.ok, mode: stored.settings && stored.settings.mode};
            }''')
            if roundtrip.get('ok') is not True or roundtrip.get('mode') != 'random':
                fail('settings round-trip', f'unexpected reply {roundtrip}')
            ok('settings round-trip through worker and real storage')
            popup.evaluate('''async () => {
              await chrome.runtime.sendMessage(
                {type: 'SAVE_SETTINGS', settings: {mode: 'cycle', scheduleEnabled: false, scheduleTime: '09:15'}});
            }''')
            popup.locator('#picker').set_input_files(photo)
            deadline = time.time() + 20
            while time.time() < deadline:
                if '1 / 20' in (popup.locator('#count').text_content() or ''):
                    break
                time.sleep(0.5)
            else:
                fail('image import', 'library count never reached 1 / 20')
            stored = popup.evaluate('''async () => {
              const {listPhotos} = await import('./library.mjs');
              const photos = await listPhotos();
              return photos.map(p => ({name: p.originalName, w: p.width, h: p.height}));
            }''')
            if len(stored) != 1 or stored[0]['w'] < 1:
                fail('image import', f'unexpected stored photos {stored}')
            ok('image import through real popup into IndexedDB', stored[0]['name'])

            # Export: select the stored photo in the real popup, confirm the
            # square preview renders, then run the production transform
            # against the real IndexedDB blob. The library must be identical
            # afterwards and the JPEG must carry no EXIF segment.
            popup.locator('#export-photo').select_option(index=1)
            deadline = time.time() + 20
            while time.time() < deadline:
                if popup.evaluate("!document.querySelector('#export-preview-wrap').hidden"):
                    break
                time.sleep(0.5)
            else:
                fail('export', 'export preview never appeared')
            if popup.locator('#export-preview').evaluate('img => img.naturalWidth') != 400:
                fail('export', 'preview is not the 400px square crop')
            scrollable = popup.evaluate(
                'document.body.scrollHeight > document.body.clientHeight')
            export_result = popup.evaluate('''async () => {
              const {listPhotos} = await import('./library.mjs');
              const {cropSquareForExport} = await import('./images.mjs');
              const photos = await listPhotos();
              const source = photos[0].blob;
              const result = await cropSquareForExport(source, 'linkedin', photos[0].originalName);
              const bytes = new Uint8Array(await result.blob.arrayBuffer());
              let binary = '';
              bytes.forEach(b => binary += String.fromCharCode(b));
              const after = await listPhotos();
              return {count: after.length, storedBytes: after[0].blob.size,
                sourceBytes: source.size, width: result.width, height: result.height,
                upscaled: result.upscaled, fileName: result.fileName, type: result.blob.type,
                data: btoa(binary)};
            }''')
            data = base64.b64decode(export_result['data'])
            if (export_result['width'], export_result['height']) != (400, 400) \
                    or export_result['type'] != 'image/jpeg':
                fail('export', f"unexpected output {export_result['width']}x{export_result['height']} {export_result['type']}")
            if export_result['fileName'] != 'photo-linkedin-400x400.jpg':
                fail('export', f"unexpected filename {export_result['fileName']}")
            if data[:3] != b'\xff\xd8\xff' or b'Exif\x00\x00' in data:
                fail('export', 'output is not a clean metadata-free JPEG')
            if export_result['count'] != 1 or export_result['storedBytes'] != export_result['sourceBytes']:
                fail('export', 'library changed during export')
            ok('export square-crops the IndexedDB photo to a clean 400x400 JPEG',
               f"{export_result['fileName']} upscaled={export_result['upscaled']} scrollable={scrollable}")
            ok('export left the stored library byte-identical')

            # Schedule: enable the daily review and confirm the alarm exists.
            popup.locator('#schedule').check()
            popup.locator('#save').click()
            alarm = popup.evaluate(
                "async () => (await chrome.alarms.get('fb-pfp-daily-review'))?.scheduledTime || null")
            if not alarm:
                fail('scheduling', 'fb-pfp-daily-review alarm missing after save')
            ok('daily-review alarm scheduled', time.strftime('%H:%M %Y-%m-%d', time.localtime(alarm / 1000)))
            popup.locator('#schedule').uncheck()
            popup.locator('#save').click()

            # Restart the browser and confirm the library persisted.
            popup.close()
            browser.close()
            stop_edge()

            # Edge headless gives every launch a throwaway scoped profile
            # (its brand data dir cannot be overridden and macOS TCC denies
            # the CLI-spawned default), and Edge 156 blocks CDP on the real
            # default profile, so cross-restart persistence cannot be
            # exercised headless. What can be proven headless is that the
            # data reached disk: the scoped profile holds non-empty storage
            # for this extension. The cross-restart check itself is a
            # headed, manual acceptance step on real Edge.
            profiles = sorted(scoped_root.glob(f'scoped_dir*/Default'),
                               key=lambda p: p.stat().st_mtime, reverse=True)
            disk_ok = False
            for profile in profiles:
                settings_dir = profile / 'Local Extension Settings' / ext_id
                idb = profile / 'IndexedDB' / f'chrome-extension_{ext_id}_0.indexeddb.leveldb'
                if settings_dir.is_dir() and any(settings_dir.iterdir()) and idb.is_dir() and any(idb.iterdir()):
                    disk_ok = True
                    break
            if not disk_ok:
                fail('storage flush', 'extension storage never reached disk in the scoped profile')
            ok('extension storage flushed to disk (scoped headless profile)')

            launch_edge()
            browser = play.chromium.connect_over_cdp(f'http://localhost:{CDP_PORT}')
            context = browser.contexts[0]
            popup = context.new_page()
            popup.goto(f'chrome-extension://{ext_id}/src/popup.html')
            popup.locator('#picker').set_input_files(photo)
            deadline = time.time() + 20
            while time.time() < deadline:
                if '1 / 20' in (popup.locator('#count').text_content() or ''):
                    break
                time.sleep(0.5)
            else:
                fail('fresh session', 're-import failed in the fresh browser session')
            ok('fresh browser session boots and imports cleanly')
            print('NOTE: cross-restart library persistence needs the headed manual pass; '
                  'Edge headless uses a throwaway profile and Edge 156 blocks CDP on the default profile.')

            # Review flow end to end against the mapped fixture site. The
            # operation is verified through the popup status first: CDP
            # attach mode surfaces the new tab to playwright only after the
            # worker's messaging completes, so tab discovery cannot be the
            # completion signal. Fixture assertions then run over a raw CDP
            # session attached to the facebook.com target.
            popup.locator('#prepare').click()
            deadline = time.time() + 60
            status = ''
            while time.time() < deadline:
                status = popup.locator('#status').text_content() or ''
                if 'Ready for review' in status or status.startswith(('Operation failed', 'photo.jpg:')):
                    break
                time.sleep(0.5)
            if 'Ready for review' not in status:
                fail('review flow', f'operation did not complete: {status}')

            # The facebook tab becomes visible to playwright only once the
            # worker's messaging completes (lazy attachment in CDP attach
            # mode), so discover it after the status settles.
            fb_tab = None
            deadline = time.time() + 20
            while time.time() < deadline and fb_tab is None:
                for ctx in browser.contexts:
                    for page in ctx.pages:
                        if page.url.startswith('https://www.facebook.com/'):
                            fb_tab = page
                            break
                if fb_tab is None:
                    time.sleep(0.5)
            if fb_tab is None:
                fail('review flow', 'facebook tab not attached after operation completed')
            state = fb_tab.evaluate('''() => ({
              changed: window.__changed, saved: window.__saved,
              premature: window.__premature,
              preview: Boolean(document.querySelector('#preview')),
            })''')
            if not (state['preview'] and state['changed']):
                fail('review flow', f'preview never staged: {state}')
            if state['saved'] != 0 or state['premature'] != 0:
                fail('review flow', f'Save was touched: {state}')
            ok('review flow staged the photo on the mapped fixture', f"input {state['changed']}")
            ok('Save untouched in review mode', f"saved={state['saved']} premature={state['premature']}")
            ok('popup reported ready for review')

            browser.close()
    finally:
        stop_edge()
        server.shutdown()
        server.server_close()
        cleanup_scoped_profiles(scoped_before)
        shutil.rmtree(tmp, ignore_errors=True)

    print(f'ACCEPTANCE: {len(CHECKS)} checks passed on Microsoft Edge')


if __name__ == '__main__':
    main()
