#!/usr/bin/env python3
"""Offline popup UI smoke test with local storage and messaging stubs.
This does not test the real extension worker, browser installation or Facebook.
Requires Python Playwright and Pillow only, and never makes a web request.
"""
import io
import os
import re
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def jpeg():
    image = Image.new('RGB', (128,128), (45,132,230))
    file = io.BytesIO()
    image.save(file,format='JPEG')
    return file.getvalue()


def main():
    html = (ROOT / 'src/popup.html').read_text()
    html = re.sub(r'<script type="module" src="popup.mjs"></script>', '', html)
    css = (ROOT / 'src/popup.css').read_text()
    # Exercise production image normalization in a real Chromium DOM. Substitute
    # only persistence and Chrome runtime messaging, which require an extension origin.
    images = re.sub(r'export ', '', (ROOT / 'src/images.mjs').read_text())
    popup = (ROOT / 'src/popup.mjs').read_text()
    popup = re.sub(r'^import .+?;\s*$', '', popup, flags=re.MULTILINE)
    prefix = '''
      const __photos=[];
      async function listPhotos(){return [...__photos];}
      async function savePhoto(p){__photos.push(p);return p.id;}
      async function deletePhoto(id){const i=__photos.findIndex(p=>p.id===id); if(i>=0)__photos.splice(i,1);}
      if(!crypto.randomUUID) crypto.randomUUID=()=> '00000000-0000-4000-8000-000000000000';
      window.chrome = window.chrome || {};
      window.chrome.runtime={async sendMessage(message){
        if(message.type==='GET_SETTINGS')return {ok:true,settings:{mode:'cycle',scheduleEnabled:false,scheduleTime:'09:15',lastResult:'Ready.'}};
        if(message.type==='SAVE_SETTINGS')return {ok:true,settings:{...message.settings,
          scheduleTime: message.settings.scheduleTime || '09:15'}};
        if(message.type==='PREPARE_NEXT')return {ok:true,name:'test-image.jpg',saved:false};
        if(message.type==='PUBLISH_NEXT')return window.__unconfirmed
          ? {ok:true,name:'test-image.jpg',saved:true,confirmed:false}
          : {ok:true,name:'test-image.jpg',saved:true,confirmed:true};
        return {ok:false,error:'Unknown'};
      }};
    '''
    with sync_playwright() as playwright:
        launch_args = {'headless': True}
        if os.getenv('CHROMIUM_PATH'):
            launch_args['executable_path'] = os.environ['CHROMIUM_PATH']
        browser=playwright.chromium.launch(**launch_args)
        try:
            page=browser.new_page(viewport={'width':410,'height':780})
            errors=[]
            page.on('pageerror',lambda ex: errors.append(str(ex)))
            page.set_content(html)
            page.add_style_tag(content=css)
            page.add_script_tag(content=prefix + images + '\n' + popup)
            page.wait_for_function("document.querySelector('#prepare').disabled === true")
            assert page.locator('#count').text_content().strip() == '0 / 20'
            assert page.locator('#prepare').is_disabled()
            page.locator('#picker').set_input_files({'name':'test-image.jpg','mimeType':'image/jpeg','buffer':jpeg()})
            page.wait_for_function("document.querySelector('#count').textContent.includes('1 / 20')")
            assert not page.locator('#prepare').is_disabled()
            assert page.locator('#publish').is_disabled()
            page.locator('#confirm-publish').check()
            assert not page.locator('#publish').is_disabled()
            page.locator('#publish').click()
            page.wait_for_function("document.querySelector('#status').textContent.includes('Save acknowledged')")
            assert page.locator('#publish').is_disabled()
            # An unconfirmed Save must never be shown as acknowledged.
            page.evaluate('window.__unconfirmed = true')
            page.locator('#confirm-publish').check()
            page.locator('#publish').click()
            page.wait_for_function("document.querySelector('#status').textContent.includes('did not confirm')")
            unconfirmed_text = page.locator('#status').text_content()
            assert 'acknowledged' not in unconfirmed_text, unconfirmed_text
            assert 'error' in (page.locator('#status').get_attribute('class') or ''), 'unconfirmed Save must use the error style'
            page.evaluate('window.__unconfirmed = false')
            print('PASS: popup does not call an unconfirmed Save acknowledged')
            page.locator('#prepare').click()
            page.wait_for_function("document.querySelector('#status').textContent.includes('Ready for review in the Facebook tab')")
            page.locator('#schedule').check()
            page.locator('#time').fill('08:20')
            page.locator('#save').click()
            page.wait_for_function("document.querySelector('#status').textContent.includes('Daily review saved')")
            page.locator('#photos button').click()
            page.wait_for_function("document.querySelector('#count').textContent.includes('0 / 20')")
            assert not errors, errors
            print('PASS: popup import/remove, explicit publishing confirmation, review and schedule controls')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
