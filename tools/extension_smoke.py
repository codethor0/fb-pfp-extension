#!/usr/bin/env python3
"""Offline real-extension smoke test using disposable Playwright Chromium.

Loads the packaged Manifest V3 extension, its real service worker, popup,
IndexedDB and content script. Every Facebook request is fulfilled with a
synthetic fixture; no real account is accessed and no real image is uploaded.
"""
import io
import os
import re
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>[hidden]{display:none!important}button,img{display:block;margin:12px}
img{width:80px;height:80px}</style></head><body>
<h1>Local test fixture. Not Facebook.</h1>
<input id="composer" type="file">
<button id="avatar"><img alt="Profile picture" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='blue'/%3E%3C/svg%3E"></button>
<button id="chooser" hidden>Choose profile picture</button>
<div role="dialog" id="dialog" hidden><h2>Choose profile picture</h2>
<input id="pfp-input" type="file"><button id="save">Save</button></div>
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


def test_photo():
    image = Image.new('RGB', (160, 160), (45, 135, 225))
    output = io.BytesIO()
    image.save(output, 'JPEG')
    return output.getvalue()


def assert_no_composer_upload(tab):
    assert tab.locator('#composer').evaluate('(el) => el.files.length') == 0, 'Newsfeed composer touched'
    assert tab.locator('#pfp-input').evaluate('(el) => el.files.length') == 1, 'Profile dialog input empty'


def main():
    args = [
        f'--disable-extensions-except={ROOT}',
        f'--load-extension={ROOT}',
    ]
    kwargs = {'channel': 'chromium', 'headless': True, 'args': args, 'timeout': 25000}
    if os.environ.get('CHROMIUM_PATH'):
        # Non-bundled Chromium may ignore extension launch flags.
        kwargs.pop('channel')
        kwargs['executable_path'] = os.environ['CHROMIUM_PATH']
    with sync_playwright() as playwright:
        with tempfile.TemporaryDirectory(prefix='fb-pfp-extension-qa-') as profile:
            try:
                context = playwright.chromium.launch_persistent_context(profile, **kwargs)
            except PlaywrightError as err:
                raise RuntimeError('Could not launch extension-capable Playwright Chromium. '
                    'Run: python -m playwright install chromium') from err
            try:
                # Never contact the real Facebook site during automated tests.
                context.route(re.compile(r'^https://www\.facebook\.com/.*'),
                              lambda route: route.fulfill(status=200, content_type='text/html', body=HTML))
                worker = context.service_workers[0] if context.service_workers else \
                    context.wait_for_event('serviceworker', timeout=15000)
                extension_id = worker.url.split('/')[2]
                assert re.fullmatch(r'[a-p]{32}', extension_id), 'Unexpected extension identity'
                popup = context.new_page()
                popup.goto(f'chrome-extension://{extension_id}/src/popup.html', wait_until='domcontentloaded')
                popup.wait_for_function("document.querySelector('#status').textContent.length > 0")
                popup.locator('#picker').set_input_files({
                    'name': 'synthetic-qa.jpg', 'mimeType': 'image/jpeg', 'buffer': test_photo()
                })
                popup.wait_for_function("document.querySelector('#count').textContent.includes('1 / 20')", timeout=12000)
                with context.expect_page(timeout=12000) as new_tab:
                    popup.locator('#prepare').click()
                review = new_tab.value
                review.wait_for_url(re.compile(r'^https://www\.facebook\.com/'), timeout=12000)
                review.wait_for_selector('#preview', timeout=18000)
                assert_no_composer_upload(review)
                assert review.evaluate('window.__saved') == 0, 'Review clicked Save'
                assert review.locator('#dialog').is_visible(), 'Review dialog closed unexpectedly'
                popup.wait_for_function("document.querySelector('#status').textContent.includes('Ready for review')", timeout=12000)
                print('PASS: full MV3 extension imported image and reviewed without Save')
                popup.locator('#confirm-publish').check()
                with context.expect_page(timeout=12000) as new_tab:
                    popup.locator('#publish').click()
                published = new_tab.value
                published.wait_for_url(re.compile(r'^https://www\.facebook\.com/'), timeout=12000)
                published.wait_for_function('window.__saved === 1', timeout=20000)
                assert_no_composer_upload(published)
                assert not published.locator('#dialog').is_visible(), 'Dialog remained open'
                popup.wait_for_function("document.querySelector('#status').textContent.includes('Save acknowledged')", timeout=12000)
                print('PASS: real worker, popup, storage and content script clicked synthetic Save once')
                print('PASS: no real Facebook network request; isolated temporary profile destroyed')
            finally:
                context.close()


if __name__ == '__main__':
    main()
