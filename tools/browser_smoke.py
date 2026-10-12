#!/usr/bin/env python3
"""Offline DOM smoke tests for review, explicit Save, and failure handling.
This is a synthetic page and does not test Facebook or a real extension install.
"""
import base64
import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'src' / 'content.js'


def fixture(has_dialog_input=True):
    image_input = '<input id="pfp-input" type="file">' if has_dialog_input else '<p>No file input</p>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
        [hidden]{{display:none!important}} button,img{{display:block;margin:12px}} img{{width:80px;height:80px}}
        </style></head><body>
        <h1>Offline test fixture, not Facebook</h1>
        <input id="composer" type="file">
        <button id="avatar"><img alt="Profile picture" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='80' height='80' fill='blue'/%3E%3C/svg%3E"></button>
        <button id="chooser" hidden>Choose profile picture</button>
        <div role="dialog" id="dialog" hidden><h2>Choose profile picture</h2>
          {image_input}<button id="save">Save</button></div>
        <script>
          window.__saved=0;
          document.querySelector('#avatar').addEventListener('click',()=>document.querySelector('#chooser').hidden=false);
          document.querySelector('#chooser').addEventListener('click',()=>document.querySelector('#dialog').hidden=false);
          document.querySelector('#save').addEventListener('click',()=>{{window.__saved++;document.querySelector('#dialog').hidden=true;}});
          const f=document.querySelector('#pfp-input');
          if(f) f.addEventListener('change',()=>{{
            const pic=document.createElement('img');pic.id='preview';pic.src=URL.createObjectURL(f.files[0]);
            document.querySelector('#dialog').appendChild(pic);
          }});
        </script></body></html>'''


def image_payload():
    image = Image.new('RGB', (180, 180), (20, 155, 220))
    buf = io.BytesIO()
    image.save(buf, format='JPEG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


def main():
    with sync_playwright() as play:
        launch_args = {'headless': True}
        if os.getenv('CHROMIUM_PATH'):
            launch_args['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = play.chromium.launch(**launch_args)
        try:
            source = CONTENT.read_text().replace('    validatePage();', '    // Synthetic DOM fixture; skip live Facebook origin check.')
            source = source.replace('const WAIT_MS = 12000;', 'const WAIT_MS = 900;')
            source = source.replace(']), 4000);', ']), 450);').replace(']), 8000);', ']), 450);')

            def run_case(has_dialog_input, publish):
                page = browser.new_page()
                page.set_content(fixture(has_dialog_input))
                page.evaluate('''window.chrome={runtime:{onMessage:{addListener(fn){window.__handler=fn;}}}};''')
                page.add_script_tag(content=source)
                reply = page.evaluate('''({data,publish}) => new Promise(resolve => {
                  window.__handler({type:'PREPARE_PHOTO',data,mime:'image/jpeg',
                    fileName:'profile-photo.jpg',publish}, {}, resolve);
                })''', {'data': image_payload(), 'publish': publish})
                return reply, page

            review, page = run_case(True, False)
            assert review.get('ok') is True and review.get('saved') is False, review
            assert page.locator('#preview').count() == 1
            assert page.locator('#pfp-input').evaluate('e=>e.files.length') == 1
            assert page.locator('#composer').evaluate('e=>e.files.length') == 0
            assert page.evaluate('window.__saved') == 0
            print('PASS: review opens dialog, composer untouched, Save untouched')
            page.close()

            published, page = run_case(True, True)
            assert published.get('ok') is True and published.get('saved') is True, published
            assert page.evaluate('window.__saved') == 1
            assert page.locator('#composer').evaluate('e=>e.files.length') == 0
            assert not page.locator('#dialog').is_visible()
            print('PASS: explicit change clicks Save once and sees dialog close')
            page.close()

            negative, page = run_case(False, True)
            assert negative.get('ok') is False, negative
            assert 'No file input' in negative.get('error', ''), negative
            assert page.evaluate('window.__saved') == 0
            assert page.locator('#composer').evaluate('e=>e.files.length') == 0
            print('PASS: missing profile-dialog file input stops without publishing')
            page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    main()
