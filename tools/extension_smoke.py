#!/usr/bin/env python3
"""Offline real-extension smoke test using disposable Playwright Chromium.

Loads the packaged Manifest V3 extension, its real service worker, popup,
IndexedDB and content script. Every Facebook request is fulfilled with a
synthetic fixture; no real account is accessed and no real image is uploaded.
"""
import http.server
import io
import os
import re
import shutil
import ssl
import subprocess
import tempfile
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>[hidden]{display:none!important}button,img{display:block;margin:12px}
img{width:80px;height:80px}</style></head><body>
<h1>Local test fixture. Not Facebook.</h1>
<input id="composer" type="file">
<button id="avatar"><img alt="Profile picture" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='blue'/%3E%3C/svg%3E"></button>
<button id="chooser" hidden>Choose profile picture</button>
<div role="dialog" id="dialog" hidden><h2>Choose profile picture</h2>
<input id="pfp-input" type="file" accept="image/*,image/heif,image/heic"><button id="save">Save</button></div>
<script>
window.__saved=0;
document.querySelector('#avatar').addEventListener('click',()=>document.querySelector('#chooser').hidden=false);
document.querySelector('#chooser').addEventListener('click',()=>document.querySelector('#dialog').hidden=false);
document.querySelector('#save').addEventListener('click',()=>{window.__saved++;document.querySelector('#dialog').hidden=true;});
document.querySelector('#pfp-input').addEventListener('change',e=>{
 const img=document.createElement('img');img.id='preview';
 img.src=URL.createObjectURL(e.target.files[0]);document.querySelector('#dialog').appendChild(img);
});
</script></body></html>"""


def start_fixture(directory):
    """Serve the synthetic page over HTTPS on 127.0.0.1 with a throwaway self-signed certificate.

    Chromium is told to map www.facebook.com to this server and to resolve nothing else, so the test
    cannot reach the real Facebook site even if request interception misses a tab opened by the extension.
    """
    if not shutil.which('openssl'):
        raise RuntimeError('openssl is required to create the throwaway test certificate')
    cert, key = os.path.join(directory, 'cert.pem'), os.path.join(directory, 'key.pem')
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=www.facebook.com', '-keyout', key, '-out', cert],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_photo(fmt='JPEG', color=(45, 135, 225)):
    image = Image.new('RGB', (160, 160), color)
    output = io.BytesIO()
    options = {}
    if fmt == 'JPEG':
        exif = Image.Exif()
        exif[271] = 'Synthetic camera'
        options['exif'] = exif
    image.save(output, fmt, **options)
    return output.getvalue()


def library_snapshot(popup):
    return popup.evaluate('''async () => {
      const db = await new Promise((resolve, reject) => {
        const r = indexedDB.open('fb-pfp-library', 1);
        r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error);
      });
      try {
        const photos = await new Promise((resolve, reject) => {
          const r = db.transaction('photos').objectStore('photos').getAll();
          r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error);
        });
        return Promise.all(photos.map(async p => ({id:p.id, name:p.originalName,
          type:p.blob.type, bytes:[...new Uint8Array(await p.blob.arrayBuffer())]})));
      } finally {db.close();}
    }''')


def used_ids(popup):
    return popup.evaluate("async () => (await chrome.storage.local.get('settings')).settings?.usedIds || []")


def assert_no_composer_upload(tab):
    assert tab.locator('#composer').evaluate('(el) => el.files.length') == 0, 'Newsfeed composer touched'
    assert tab.locator('#pfp-input').evaluate('(el) => el.files.length') == 1, 'Profile dialog input empty'


def main():
    fixture_dir = tempfile.mkdtemp(prefix='fb-pfp-fixture-')
    server = start_fixture(fixture_dir)
    args = [
        f'--disable-extensions-except={ROOT}',
        f'--load-extension={ROOT}',
        f'--host-resolver-rules=MAP www.facebook.com 127.0.0.1:{server.server_address[1]}, MAP * ~NOTFOUND, EXCLUDE 127.0.0.1',
        '--ignore-certificate-errors',
        '--no-proxy-server',
    ]
    executable = os.environ.get('CHROMIUM_PATH', '')
    # Branded Chrome removed --load-extension; the pipe-only CDP method loads
    # the same unpacked files inside this disposable test profile.
    method = os.environ.get('EXTENSION_LOAD_METHOD',
                            'cdp' if 'Google Chrome.app' in executable else 'flags')
    if method not in ('flags', 'cdp'):
        raise ValueError('EXTENSION_LOAD_METHOD must be flags or cdp')
    if method == 'cdp':
        args = [arg for arg in args if not arg.startswith(('--load-extension=', '--disable-extensions-except='))]
        args.append('--enable-unsafe-extension-debugging')
    kwargs = {'channel': 'chromium', 'headless': True, 'args': args, 'timeout': 25000}
    if method == 'cdp':
        kwargs['ignore_default_args'] = ['--disable-extensions']
    if executable:
        # Non-bundled Chromium may ignore extension launch flags.
        kwargs.pop('channel')
        kwargs['executable_path'] = executable

    def launch(playwright, profile):
        context = playwright.chromium.launch_persistent_context(profile, **kwargs)
        if method == 'cdp':
            try:
                loaded = context.browser.new_browser_cdp_session().send('Extensions.loadUnpacked', {'path': str(ROOT)})
                context._fb_pfp_extension_id = loaded['id']
            except Exception:
                context.close()
                raise
        context.route(re.compile(r'^https://www\.facebook\.com/.*'),
                      lambda route: route.fulfill(status=200, content_type='text/html', body=HTML))
        return context
    with sync_playwright() as playwright:
        with tempfile.TemporaryDirectory(prefix='fb-pfp-extension-qa-') as profile:
            try:
                context = launch(playwright, profile)
            except PlaywrightError as err:
                raise RuntimeError('Could not launch extension-capable Playwright Chromium. '
                    'Run: python -m playwright install chromium') from err
            try:
                if method == 'cdp':
                    # Playwright can miss workers installed after the persistent
                    # browser context is created. Runtime messages below still
                    # require the real background worker to answer.
                    extension_id = context._fb_pfp_extension_id
                else:
                    worker = context.service_workers[0] if context.service_workers else \
                        context.wait_for_event('serviceworker', timeout=15000)
                    extension_id = worker.url.split('/')[2]
                assert re.fullmatch(r'[a-p]{32}', extension_id), 'Unexpected extension identity'
                popup = context.new_page()
                popup.goto(f'chrome-extension://{extension_id}/src/popup.html', wait_until='domcontentloaded')
                expect(popup.locator('#status')).not_to_be_empty()
                assert popup.locator('#publish').is_disabled(), 'Unconfirmed Change now enabled'
                for count, (fmt, suffix, mime, color) in enumerate([
                    ('JPEG', 'jpg', 'image/jpeg', (45,135,225)),
                    ('PNG', 'png', 'image/png', (225,135,45)),
                    ('WEBP', 'webp', 'image/webp', (135,225,45)),
                ], 1):
                    popup.locator('#picker').set_input_files({
                        'name': f'synthetic-qa.{suffix}', 'mimeType': mime, 'buffer': test_photo(fmt, color)
                    })
                    expect(popup.locator('#count')).to_contain_text(f'{count} / 20', timeout=12000)
                photos = library_snapshot(popup)
                assert len(photos) == 3 and all(p['type'] == 'image/jpeg' for p in photos)
                for photo in photos:
                    assert not Image.open(io.BytesIO(bytes(photo['bytes']))).getexif(), 'Camera metadata retained'
                print('PASS: JPEG, PNG and WebP normalized to JPEG without camera metadata')
                popup.close()
                popup = context.new_page()
                popup.goto(f'chrome-extension://{extension_id}/src/popup.html')
                expect(popup.locator('#count')).to_contain_text('3 / 20', timeout=12000)
                assert library_snapshot(popup) == photos, 'Photo bytes changed after popup reopen'
                with context.expect_page(timeout=12000) as new_tab:
                    popup.locator('#prepare').click()
                review = new_tab.value
                review.wait_for_url(re.compile(r'^https://www\.facebook\.com/'), timeout=12000)
                review.wait_for_selector('#preview', timeout=18000)
                assert_no_composer_upload(review)
                assert review.evaluate('window.__saved') == 0, 'Review clicked Save'
                assert review.locator('#dialog').is_visible(), 'Review dialog closed unexpectedly'
                expect(popup.locator('#status')).to_contain_text('Ready for review', timeout=12000)
                assert used_ids(popup) == [], 'Prepare consumed rotation history'
                print('PASS: full MV3 extension imported image and reviewed without Save')
                popup.locator('#confirm-publish').check()
                with context.expect_page(timeout=12000) as new_tab:
                    popup.locator('#publish').click()
                published = new_tab.value
                published.wait_for_url(re.compile(r'^https://www\.facebook\.com/'), timeout=12000)
                published.wait_for_function('window.__saved === 1', timeout=20000)
                assert_no_composer_upload(published)
                assert not published.locator('#dialog').is_visible(), 'Dialog remained open'
                expect(popup.locator('#status')).to_contain_text('Save acknowledged', timeout=12000)
                first_saved = used_ids(popup)
                assert len(first_saved) == 1, 'Successful Save did not advance rotation'
                assert popup.locator('#publish').is_disabled(), 'Confirmation was not cleared'
                print('PASS: real worker, popup, storage and content script clicked synthetic Save once')
                context.close()
                context = launch(playwright, profile)
                popup = context.new_page()
                popup.goto(f'chrome-extension://{extension_id}/src/popup.html')
                expect(popup.locator('#count')).to_contain_text('3 / 20', timeout=12000)
                assert library_snapshot(popup) == photos, 'Photo bytes changed after browser restart'
                assert used_ids(popup) == first_saved, 'Rotation history lost after browser restart'
                popup.locator('#confirm-publish').check()
                with context.expect_page(timeout=12000) as new_tab:
                    popup.locator('#publish').click()
                second = new_tab.value
                second.wait_for_function('window.__saved === 1', timeout=20000)
                expect(popup.locator('#status')).to_contain_text('Save acknowledged', timeout=12000)
                second_saved = used_ids(popup)
                assert len(second_saved) == 2 and set(first_saved) < set(second_saved), 'Cycle repeated a saved photo'
                print('PASS: exact photo bytes and rotation survive browser/worker restart; cycle does not repeat')
                popup.locator('#schedule').check()
                popup.locator('#save').click()
                expect(popup.locator('#status')).to_contain_text('Daily review saved')
                assert popup.evaluate("async () => !!(await chrome.alarms.get('fb-pfp-daily-review'))")
                with context.expect_page(timeout=45000) as new_tab:
                    popup.evaluate("async () => chrome.alarms.create('fb-pfp-daily-review', {when:Date.now()+1000})")
                scheduled = new_tab.value
                scheduled.wait_for_selector('#preview', timeout=20000)
                expect(scheduled.locator('#dialog')).to_be_visible()
                assert scheduled.evaluate('window.__saved') == 0, 'Scheduled review clicked Save'
                assert used_ids(popup) == second_saved, 'Scheduled review consumed rotation history'
                popup.locator('#schedule').uncheck()
                popup.locator('#save').click()
                expect(popup.locator('#status')).to_contain_text('Preferences saved')
                assert popup.evaluate("async () => !(await chrome.alarms.get('fb-pfp-daily-review'))")
                print('PASS: actual alarm prepares without Save or rotation advance; disabling clears alarm')
                print('PASS: www.facebook.com was mapped to a local fixture and all other hosts were unresolvable; temporary profile destroyed')
            finally:
                context.close()
                server.shutdown()
                shutil.rmtree(fixture_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
