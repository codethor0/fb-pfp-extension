#!/usr/bin/env python3
"""Offline popup UI smoke test with local storage and messaging stubs.
This does not test the real extension worker, browser installation or Facebook.
Requires Python Playwright and Pillow only, and never makes a web request.
"""
import io
import os
import re
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from browser_smoke import rebranded_gecko_launcher  # noqa: E402


def jpeg():
    image = Image.new('RGB', (128,128), (45,132,230))
    file = io.BytesIO()
    image.save(file,format='JPEG')
    return file.getvalue()


def jpeg_with_exif():
    """Landscape 600x400 JPEG carrying camera and GPS EXIF metadata."""
    from PIL.TiffImagePlugin import IFDRational
    image = Image.new('RGB', (600, 400), (200, 90, 30))
    exif = Image.Exif()
    exif[0x010F] = 'Canon'           # Make
    exif[0x0110] = 'EOS R5'          # Model
    exif[0x0132] = '2026:10:29 18:00:00'
    exif[0x8825] = {0: b'\x02\x03\x00\x00', 1: 'N',      # GPS IFD
                    2: (IFDRational(44), IFDRational(58), IFDRational(30)),
                    3: 'W',
                    4: (IFDRational(93), IFDRational(16), IFDRational(0))}
    file = io.BytesIO()
    image.save(file, format='JPEG', exif=exif)
    return file.getvalue()


def export_probe(page, source, original_name='probe.jpg', target='linkedin'):
    """Run the production export transform in the page and report the result."""
    import base64
    encoded = base64.b64encode(source).decode()
    return page.evaluate("""async ({encoded, originalName, target}) => {
      const bin = atob(encoded);
      const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const result = await cropSquareForExport(
        new Blob([u8], {type: 'image/jpeg'}), target, originalName);
      const head = new Uint8Array(await result.blob.slice(0, 3).arrayBuffer());
      return {width: result.width, height: result.height, upscaled: result.upscaled,
              fileName: result.fileName, bytes: result.blob.size,
              magic: [...head]};
    }""", {'encoded': encoded, 'originalName': original_name, 'target': target})


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Offline popup UI smoke test.')
    parser.add_argument('--browser', choices=['chromium', 'firefox'], default='chromium',
                        help='Engine to run the popup DOM on (default: chromium).')
    args = parser.parse_args()

    html = (ROOT / 'src/popup.html').read_text()
    html = re.sub(r'<script type="module" src="popup.mjs"></script>', '', html)
    css = (ROOT / 'src/popup.css').read_text()
    # Exercise production image normalization and site-route resolution in a
    # real Chromium DOM. Substitute only persistence and Chrome runtime
    # messaging, which require an extension origin.
    images = re.sub(r'export ', '', (ROOT / 'src/images.mjs').read_text())
    logic = re.sub(r'export ', '', (ROOT / 'src/logic.mjs').read_text())
    popup = (ROOT / 'src/popup.mjs').read_text()
    popup = re.sub(r'^import .+?;\s*$', '', popup, flags=re.MULTILINE)
    prefix = '''
      const __photos=[];
      async function listPhotos(){return [...__photos];}
      async function savePhoto(p){__photos.push(p);return p.id;}
      async function deletePhoto(id){const i=__photos.findIndex(p=>p.id===id); if(i>=0)__photos.splice(i,1);}
      async function getPhoto(id){return __photos.find(p=>p.id===id) || null;}
      if(!crypto.randomUUID){let __n=0; crypto.randomUUID=()=> '00000000-0000-4000-8000-' + String(++__n).padStart(12, '0');}
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
        engine = getattr(playwright, args.browser)
        if args.browser == 'firefox' and sys.platform == 'darwin':
            # macOS 27 TCC protects the default Firefox app-data dir; the
            # rebranded launcher points the same binary at a neutral one.
            launch_args['executable_path'] = str(rebranded_gecko_launcher(playwright))
        browser = engine.launch(**launch_args)
        try:
            page=browser.new_page(viewport={'width':410,'height':780})
            errors=[]
            page.on('pageerror',lambda ex: errors.append(str(ex)))
            page.set_content(html)
            page.add_style_tag(content=css)
            page.add_script_tag(content=prefix + images + '\n' + logic + '\n' + popup)
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

            # --- Local export section (LinkedIn target) ---
            page.wait_for_function("document.querySelector('#export-photo').options.length === 2")
            assert page.locator('#export-download').is_disabled()
            assert page.locator('#export-photo').is_disabled() is False
            library_fingerprint = page.evaluate("""() => __photos[0].blob.arrayBuffer().then(b => {
              const u8 = new Uint8Array(b); let h = 0;
              for (let i = 0; i < u8.length; i++) h = (h * 31 + u8[i]) >>> 0;
              return __photos.length + ':' + u8.length + ':' + h;
            })""")
            # The 128x128 imported photo is below the 400px target: the
            # square preview renders and the upscale warning must show.
            page.locator('#export-photo').select_option(index=1)
            page.wait_for_function("!document.querySelector('#export-preview-wrap').hidden")
            assert page.locator('#export-preview').evaluate('img => img.naturalWidth') == 400
            assert page.locator('#export-warning').is_visible()
            with page.expect_download() as download_info:
                page.locator('#export-download').click()
            download = download_info.value
            assert download.suggested_filename == 'test-image-linkedin-400x400.jpg', download.suggested_filename
            data = download.path().read_bytes()
            assert data[:3] == b'\xff\xd8\xff', 'export must be JPEG'
            exported = Image.open(io.BytesIO(data))
            assert exported.size == (400, 400) and exported.format == 'JPEG'
            assert b'Exif\x00\x00' not in data, 'export must carry no EXIF segment'
            assert page.evaluate(f"""() => __photos[0].blob.arrayBuffer().then(b => {{
              const u8 = new Uint8Array(b); let h = 0;
              for (let i = 0; i < u8.length; i++) h = (h * 31 + u8[i]) >>> 0;
              return __photos.length + ':' + u8.length + ':' + h;
            }})""") == library_fingerprint, 'export must not modify the stored library'
            print('PASS: export previews, warns on upscaling, downloads a 400x400 JPEG, strips EXIF, library untouched')

            # EXIF-laden landscape source: warning stays hidden at exactly
            # 400px short side, GPS/camera metadata is gone from the output.
            page.locator('#picker').set_input_files(
                {'name': 'wide.jpg', 'mimeType': 'image/jpeg', 'buffer': jpeg_with_exif()})
            page.wait_for_function("document.querySelector('#count').textContent.includes('2 / 20')")
            page.locator('#export-photo').select_option(label='wide.jpg')
            page.wait_for_function("!document.querySelector('#export-preview-wrap').hidden")
            assert not page.locator('#export-warning').is_visible()
            with page.expect_download() as download_info:
                page.locator('#export-download').click()
            data = download_info.value.path().read_bytes()
            exported = Image.open(io.BytesIO(data))
            assert exported.size == (400, 400)
            assert b'Exif\x00\x00' not in data, 'GPS/camera EXIF must not survive the export'
            assert not exported.getexif(), 'decoded export must expose no EXIF tags'
            print('PASS: EXIF/GPS metadata removed from exported bytes')

            # Direct probes against the production transform: portrait, odd
            # sizes, undersized source, unknown target, invalid bytes.
            for size, expected_up in (((300, 500), True), ((301, 499), True), ((600, 400), False), ((10, 10), True)):
                probe_image = Image.new('RGB', size, (10, 120, 60))
                buf = io.BytesIO()
                probe_image.save(buf, format='JPEG')
                result = export_probe(page, buf.getvalue())
                assert (result['width'], result['height']) == (400, 400), (size, result)
                assert result['magic'] == [255, 216, 255], 'export must be JPEG'
                assert result['upscaled'] is expected_up, (size, result)
                assert result['fileName'] == 'probe-linkedin-400x400.jpg', result['fileName']
                assert 0 < result['bytes'] <= 3 * 1024 * 1024
            rejected = page.evaluate("""async () => {
              try {
                await cropSquareForExport(new Blob(['junk'], {type: 'image/jpeg'}), 'linkedin');
                return 'resolved';
              } catch (error) { return 'rejected: ' + error.message; }
            }""")
            assert rejected.startswith('rejected:'), rejected
            rejected_target = page.evaluate("""async () => {
              try {
                await cropSquareForExport(new Blob(['junk'], {type: 'image/jpeg'}), 'twitter');
                return 'resolved';
              } catch (error) { return 'rejected: ' + error.message; }
            }""")
            assert rejected_target.startswith('rejected:'), rejected_target
            print('PASS: export handles portrait, odd, undersized, invalid and unknown-target inputs')

            # Stale-async regression: a slow export must never overwrite a
            # newer selection, and deleting the selected picture mid-process
            # must leave the preview reset once the stale run completes.
            page.evaluate("""() => {
              window.__exportDelay = 0;
              const original = cropSquareForExport;
              cropSquareForExport = async (...args) => {
                const delay = window.__exportDelay;
                if (delay) await new Promise(resolve => setTimeout(resolve, delay));
                return original(...args);
              };
            }""")
            page.evaluate('window.__exportDelay = 400')
            page.locator('#export-photo').select_option(label='test-image.jpg')
            page.locator('#export-photo').select_option(label='wide.jpg')
            page.wait_for_function("!document.querySelector('#export-preview-wrap').hidden")
            raced_status = page.locator('#status').text_content()
            assert 'wide-linkedin-400x400.jpg' in raced_status, f'stale export won the race: {raced_status}'
            page.locator('#export-photo').select_option(label='wide.jpg')
            page.locator('.photo', has_text='wide.jpg').locator('button').click()
            page.wait_for_function("document.querySelector('#count').textContent.includes('1 / 20')")
            page.wait_for_timeout(800)
            assert page.evaluate("document.querySelector('#export-preview-wrap').hidden") is True, \
                'stale export repopulated the preview after the selection was deleted'
            assert 'Export ready' not in page.locator('#status').text_content()
            page.evaluate('window.__exportDelay = 0')
            print('PASS: stale async export results cannot overwrite a newer selection or a deletion')

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
