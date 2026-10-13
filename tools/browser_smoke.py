#!/usr/bin/env python3
"""Offline content-flow regressions on synthetic DOM pages, never on Facebook."""
import base64
import io
import os
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'src' / 'content.js'
AVATAR_IMG = '<button id="avatar"><img alt="Profile picture" width="168" height="168" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></button>'
AVATAR_SVG = '<svg role="img" aria-label="Profile picture" id="avatar" width="168" height="168"></svg>'
BASE = r'''
<style>[hidden]{display:none!important}button,img{display:block;margin:12px}img{width:168px;height:168px}</style>
<input id="composer" type="file" accept="image/*,video/*" multiple>
AVATAR
<button id="chooser" hidden>Choose profile picture</button>
<script>
window.__changed=[]; window.__saved=0; window.__premature=0; window.__accepted=false;
const alternate='data:image/jpeg;base64,ALT_PHOTO';
const add=html=>document.body.insertAdjacentHTML('beforeend',html);
const dialogHtml=(inner,id='dialog')=>`<div role="dialog" id="${id}" aria-label="Choose profile picture">${inner}</div>`;
const CLOSE='<button aria-label="Close" id="close">x</button>';
const CONTENT='<h2>Choose profile picture</h2>'+CLOSE+'<div role="button" tabindex="0" id="upload"><span>Upload photo</span></div><button id="save">Save</button>';
const TARGET='<input id="target" type="file" accept="image/*">';
const makeInput=parent=>{const i=document.createElement('input');i.type='file';i.id='target';i.accept='image/*';parent.appendChild(i);return i;};
const preview=file=>{const img=document.createElement('img');img.id='preview';img.src=URL.createObjectURL(file);img.onload=()=>window.__accepted=true;document.querySelector('[role="dialog"]').appendChild(img);};
document.addEventListener('click',e=>{
  if(e.target.closest('#close'))document.querySelector('[role="dialog"]')?.remove();
  if(e.target.closest('#save')){window.__saved++;if(!window.__accepted||document.querySelector('[role="progressbar"]'))window.__premature++;SAVE}
});
document.addEventListener('change',e=>{
 if(e.target.type!=='file'||!e.target.files.length)return;
 window.__changed.push(e.target.id); const file=e.target.files[0]; CHANGE
},true);
document.querySelector('#avatar')?.addEventListener('click',()=>document.querySelector('#chooser').hidden=false);
document.querySelector('#chooser').addEventListener('click',()=>{LAYOUT});
</script>
'''
LAYOUTS = {
    'normal': 'add(dialogHtml(CONTENT+TARGET));',
    'missing-input': 'add(dialogHtml(CONTENT));',
    'slow-content': "add(dialogHtml(CLOSE));setTimeout(()=>document.querySelector('#dialog').innerHTML=CONTENT+TARGET,400);",
    'replaced-shell': "add(dialogHtml(CLOSE));setTimeout(()=>{document.querySelector('#dialog').remove();add(dialogHtml(CONTENT+TARGET,'dialog2'));},400);",
    'portal-input': "add(dialogHtml(CONTENT));document.querySelector('#upload').addEventListener('click',()=>makeInput(document.body).click());",
    'composer-click': "add(dialogHtml(CONTENT));document.querySelector('#upload').addEventListener('click',()=>document.querySelector('#composer').click());",
    'nested-upload': "add(dialogHtml('<div role=\"button\" id=\"outer\"><div role=\"button\" id=\"upload\">Upload photo</div></div><button id=\"save\">Save</button>'));document.querySelector('#upload').addEventListener('click',()=>makeInput(document.querySelector('#dialog')));",
    'ambiguous-inputs': "add(dialogHtml(CONTENT+TARGET+'<input id=\"other\" type=\"file\" accept=\"image/*\">'));",
    'ambiguous-dialogs': 'add(dialogHtml(CONTENT+TARGET));add(dialogHtml(CONTENT+TARGET,"other-dialog"));',
    'existing-preview': "add(dialogHtml(CONTENT+TARGET+'<img id=\"old-preview\" src=\"data:image/gif;base64,R0lGODlhAQABAAAAACw=\">'));",
    'existing-canvas': "add(dialogHtml(CONTENT+TARGET+'<canvas id=\"cropper\" width=\"180\" height=\"180\"></canvas>'));document.querySelector('#cropper').getContext('2d').fillRect(0,0,180,180);",
    'unrelated-user-input': "add(dialogHtml(CONTENT));add('<input id=\"unrelated\" type=\"file\" accept=\"image/*\">');document.querySelector('#upload').addEventListener('click',()=>window.__uploadPressed=true);",
    'late-unrelated-input': "add(dialogHtml(CONTENT));add('<input id=\"unrelated\" type=\"file\" accept=\"image/*\">');document.querySelector('#upload').addEventListener('click',()=>setTimeout(()=>document.querySelector('#unrelated').click(),200));",
    'multiple-requested-inputs': "add(dialogHtml(CONTENT));document.querySelector('#upload').addEventListener('click',()=>{makeInput(document.body).click();makeInput(document.body).click();});",
    'accept-less-input': "add(dialogHtml(CONTENT+'<input id=\"noaccept\" type=\"file\">'));",
}
CHANGES = {
    'accepted': 'preview(file);',
    'delayed': 'setTimeout(()=>preview(file),1700);',
    'ignored': '',
    'rejected': "document.querySelector('[role=\"dialog\"]').insertAdjacentHTML('beforeend','<p role=\"alert\">Upload failed</p>');",
    'broken-preview': "const img=document.createElement('img');img.src='data:image/jpeg;base64,AAAA';document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'busy-preview': "preview(file);const busy=document.createElement('div');busy.setAttribute('role','progressbar');busy.textContent='Uploading';document.querySelector('[role=\"dialog\"]').appendChild(busy);window.__accepted=false;setTimeout(()=>{busy.remove();window.__accepted=true;},500);",
    'replacement-preview': "document.querySelector('[role=\"dialog\"]').remove();add(dialogHtml(CLOSE));setTimeout(()=>{document.querySelector('[role=\"dialog\"]').innerHTML=CONTENT+TARGET;preview(file);},400);",
    'empty-canvas': "const canvas=document.createElement('canvas');canvas.width=180;canvas.height=180;document.querySelector('[role=\"dialog\"]').appendChild(canvas);",
    'canvas-preview': "const canvas=document.createElement('canvas');canvas.width=180;canvas.height=180;document.querySelector('[role=\"dialog\"]').appendChild(canvas);const img=new Image();img.onload=()=>{canvas.getContext('2d').drawImage(img,0,0,180,180);window.__accepted=true;};img.src=URL.createObjectURL(file);",
    'thumbnail-only': "const img=document.createElement('img');img.src=URL.createObjectURL(file);img.style.cssText='width:24px;height:24px';document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'old-picture-copy': "const img=document.createElement('img');img.src=document.querySelector('#old-preview').src;document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'reused-canvas': "const img=new Image();img.onload=()=>setTimeout(()=>{document.querySelector('#cropper').getContext('2d').drawImage(img,0,0,180,180);window.__accepted=true;},500);img.src=URL.createObjectURL(file);",
    'unrelated-gallery': "const img=document.createElement('img');img.src=alternate;document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'unrelated-canvas': "const canvas=document.createElement('canvas');canvas.width=180;canvas.height=180;document.querySelector('[role=\"dialog\"]').appendChild(canvas);const img=new Image();img.onload=()=>canvas.getContext('2d').drawImage(img,0,0,180,180);img.src=alternate;",
    'unrelated-reused-canvas': "const img=new Image();img.onload=()=>document.querySelector('#cropper').getContext('2d').drawImage(img,0,0,180,180);img.src=alternate;",
    'unreadable-preview': "preview(file);CanvasRenderingContext2D.prototype.getImageData=function(){throw new DOMException('Unreadable pixels','SecurityError');};",
    'resized-reencoded': "const img=new Image();img.onload=()=>{const canvas=document.createElement('canvas');canvas.width=canvas.height=120;canvas.getContext('2d').drawImage(img,0,0,120,120);canvas.toBlob(blob=>preview(blob),'image/jpeg',0.7);};img.src=URL.createObjectURL(file);",
    'centered-crop': "const canvas=document.createElement('canvas');canvas.width=canvas.height=180;document.querySelector('[role=\"dialog\"]').appendChild(canvas);const img=new Image();img.onload=()=>{const size=Math.min(img.naturalWidth,img.naturalHeight);canvas.getContext('2d').drawImage(img,(img.naturalWidth-size)/2,(img.naturalHeight-size)/2,size,size,0,0,180,180);window.__accepted=true;};img.src=URL.createObjectURL(file);",
}
SAVES = {
    'close': "document.querySelector('[role=\"dialog\"]').remove();",
    'stuck': '',
    'cancel': "setTimeout(()=>document.querySelector('#close').click(),150);",
    'escape': "setTimeout(()=>{window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));document.querySelector('[role=\"dialog\"]').remove();},150);",
    'error': "setTimeout(()=>document.querySelector('[role=\"dialog\"]').insertAdjacentHTML('beforeend','<p role=\"alert\">Save failed</p>'),150);",
    'unlabelled-shell': "const d=document.querySelector('[role=\"dialog\"]');d.removeAttribute('aria-label');d.innerHTML='Saving...';",
    'shell-gap-error': "document.querySelector('[role=\"dialog\"]').remove();setTimeout(()=>add('<div role=\"dialog\" id=\"waiting\">Saving...</div>'),150);setTimeout(()=>{document.querySelector('#waiting').setAttribute('aria-label','Choose profile picture');document.querySelector('#waiting').innerHTML='<p role=\"alert\">Save failed</p>';},500);",
    'shell-gap-close': "document.querySelector('[role=\"dialog\"]').remove();setTimeout(()=>add('<div role=\"dialog\" id=\"waiting\">Saving...</div>'),150);setTimeout(()=>document.querySelector('#waiting').remove(),500);",
    'unlabelled-cancel': "const d=document.querySelector('[role=\"dialog\"]');d.removeAttribute('aria-label');d.innerHTML=CLOSE;setTimeout(()=>document.querySelector('#close').click(),150);",
}


def fixture(layout='normal', change='accepted', save='close', avatar=AVATAR_IMG):
    return ('<!doctype html><html><body>'+BASE.replace('AVATAR', avatar).replace('LAYOUT', LAYOUTS[layout])
            .replace('CHANGE', CHANGES[change]).replace('SAVE', SAVES[save])
            .replace('ALT_PHOTO', image_payload((230, 30, 40)))+'</body></html>')


def image_payload(color=(20, 155, 220)):
    output = io.BytesIO()
    Image.new('RGB', (180, 180), color).save(output, 'JPEG')
    return base64.b64encode(output.getvalue()).decode('ascii')


def rectangular_payload(width, height):
    image = Image.new('RGB', (width, height))
    image.putdata([(round(x * 255 / (width - 1)), round(y * 200 / (height - 1)),
                    255 - round(x * 255 / (width - 1)))
                   for y in range(height) for x in range(width)])
    output = io.BytesIO()
    image.save(output, 'JPEG', quality=95)
    return base64.b64encode(output.getvalue()).decode('ascii')


def main():
    with sync_playwright() as play:
        launch = {'headless': True}
        if os.getenv('CHROMIUM_PATH'):
            launch['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = play.chromium.launch(**launch)
        try:
            source = CONTENT.read_text().replace('    validatePage();', '    // Synthetic page: no live Facebook origin.')
            for before, after in [('const WAIT_MS = 12000;', 'const WAIT_MS = 900;'),
                                  ('const DIALOG_WAIT_MS = 25000;', 'const DIALOG_WAIT_MS = 3000;'),
                                  ('const UPLOAD_SETTLE_MS = 2500;', 'const UPLOAD_SETTLE_MS = 150;'),
                                  ('const PREVIEW_SETTLE_MS = 600;', 'const PREVIEW_SETTLE_MS = 200;'),
                                  ('const SAVE_SETTLE_MS = 1500;', 'const SAVE_SETTLE_MS = 400;'),
                                  ('const SAVE_WAIT_MS = 30000;', 'const SAVE_WAIT_MS = 1400;')]:
                source = source.replace(before, after)

            def run(html, publish=False, user_input=False, data=None):
                page = browser.new_page()
                page.on('filechooser', lambda chooser: None)  # Intercept native pickers in negative fixtures.
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.set_content(html)
                page.evaluate('window.chrome={runtime:{id:"test-ext",onMessage:{addListener(fn){window.__handler=fn;}}}};')
                page.add_script_tag(content=source)
                payload = {'data': data or image_payload(), 'publish': publish}
                if user_input:
                    page.evaluate('''({data,publish})=>{window.__reply=null;window.__handler(
                        {type:'PREPARE_PHOTO',data,mime:'image/jpeg',fileName:'profile-photo.jpg',publish},{id:'test-ext'},reply=>window.__reply=reply);}''', payload)
                    page.wait_for_function('window.__uploadPressed===true')
                    page.locator('#unrelated').click()
                    page.wait_for_function('window.__reply!==null')
                    reply = page.evaluate('window.__reply')
                else:
                    reply = page.evaluate('''({data,publish})=>new Promise(resolve=>window.__handler(
                        {type:'PREPARE_PHOTO',data,mime:'image/jpeg',fileName:'profile-photo.jpg',publish},{id:'test-ext'},resolve))''', payload)
                assert not errors, errors
                assert page.locator('#composer').evaluate('e=>e.files.length') == 0
                assert page.evaluate('window.__premature') == 0, 'Save was clicked before upload readiness'
                return reply, page

            for publish in (False, True):
                reply, page = run(fixture(), publish)
                assert reply.get('ok') is True and reply.get('saved') is publish, reply
                assert page.evaluate('window.__saved') == int(publish)
                assert page.evaluate('window.__changed') == ['target']
                page.close()
                print('PASS:', 'explicit Save acknowledged once' if publish else 'loaded preview reviewed without Save')

            for layout in ('slow-content', 'replaced-shell', 'portal-input', 'nested-upload'):
                reply, page = run(fixture(layout=layout, avatar=AVATAR_SVG if layout == 'slow-content' else AVATAR_IMG))
                assert reply.get('ok') is True and reply.get('saved') is False, (layout, reply)
                assert page.evaluate('window.__changed') == ['target']
                assert page.evaluate('window.__saved') == 0
                page.close()
                print('PASS:', layout, 'uploads only the selected dialog input')

            for change in ('delayed', 'busy-preview', 'replacement-preview', 'canvas-preview', 'resized-reencoded'):
                reply, page = run(fixture(change=change), True)
                assert reply.get('ok') is True and reply.get('saved') is True, (change, reply)
                assert page.evaluate('window.__accepted') is True
                assert page.evaluate('window.__saved') == 1
                page.close()
                print('PASS:', change, 'waits for upload readiness before Save')

            for width, height in ((360, 180), (180, 360)):
                reply, page = run(fixture(change='centered-crop'), True, data=rectangular_payload(width, height))
                assert reply.get('ok') is True and reply.get('saved') is True, reply
                page.close()
                print(f'PASS: a centered crop of the selected {width}x{height} JPEG is recognized')

            for layout in ('missing-input', 'composer-click', 'ambiguous-inputs', 'ambiguous-dialogs',
                           'late-unrelated-input', 'multiple-requested-inputs', 'accept-less-input'):
                reply, page = run(fixture(layout=layout), True)
                assert reply.get('ok') is False, (layout, reply)
                assert page.evaluate('window.__changed') == []
                assert page.evaluate('window.__saved') == 0
                if layout == 'composer-click':
                    assert 'picker requested yes' in reply.get('error', ''), reply
                page.close()
                print('PASS:', layout, 'stops before upload or Save')

            reply, page = run(fixture(layout='unrelated-user-input'), True, user_input=True)
            assert reply.get('ok') is False and page.evaluate('window.__changed') == [], reply
            assert page.evaluate('window.__saved') == 0
            assert 'picker requested no' in reply.get('error', ''), reply
            page.close()
            print('PASS: a native user click on an unrelated file input cannot redirect the upload')

            reply, page = run(fixture())
            assert reply.get('ok') is True, reply
            changed = page.evaluate('window.__changed')
            foreign = page.evaluate('''new Promise(resolve=>window.__handler(
                {type:'PREPARE_PHOTO',data:'AAAA',mime:'image/jpeg',fileName:'profile-photo.jpg',publish:true},
                {id:'not-test-ext'},resolve))''')
            assert foreign.get('ok') is False and 'unknown sender' in foreign.get('error', ''), foreign
            assert page.evaluate('window.__saved') == 0
            assert page.evaluate('window.__changed') == changed
            page.close()
            print('PASS: a message from another extension id is ignored')

            for change in ('ignored', 'rejected', 'broken-preview', 'empty-canvas', 'thumbnail-only',
                           'unrelated-gallery', 'unrelated-canvas', 'unreadable-preview'):
                reply, page = run(fixture(change=change), True)
                assert reply.get('ok') is False, (change, reply)
                assert page.evaluate('window.__saved') == 0
                page.close()
                print('PASS:', change, 'does not report success or click Save')

            reply, page = run(fixture(change='ignored'))
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: review does not claim a picture was prepared when the upload was ignored')

            reply, page = run(fixture(layout='existing-preview', change='old-picture-copy'), True)
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: existing picture and a copy of it are not mistaken for the uploaded preview')

            reply, page = run(fixture(layout='existing-canvas', change='reused-canvas'), True)
            assert reply.get('ok') is True and reply.get('saved') is True, reply
            page.close()
            print('PASS: a reused crop canvas becomes ready after its picture changes')

            reply, page = run(fixture(layout='existing-canvas', change='ignored'), True)
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: an unchanged crop canvas is not mistaken for the uploaded picture')

            reply, page = run(fixture(layout='existing-canvas', change='unrelated-reused-canvas'), True)
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: unrelated pixels in a reused crop canvas do not authorize Save')

            for save in ('stuck', 'cancel', 'escape', 'error', 'unlabelled-shell', 'shell-gap-error', 'unlabelled-cancel'):
                reply, page = run(fixture(save=save), True)
                assert (reply.get('ok') is True and reply.get('saved') is True
                        and reply.get('confirmed') is False), (save, reply)
                assert page.evaluate('window.__saved') == 1
                page.close()
                print('PASS:', save, 'counts the Save click as used without claiming confirmation')

            reply, page = run(fixture(save='shell-gap-close'), True)
            assert reply.get('ok') is True and reply.get('saved') is True and reply.get('confirmed') is True, reply
            assert page.locator('[role="dialog"]').count() == 0
            page.close()
            print('PASS: replacement shell must finish closing before acknowledgement')

            avatars = {
                'aria label without alt': '<button id="avatar"><img aria-label="Profile picture" width="168" height="168" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></button>',
                'title name': '<button id="avatar"><svg role="img" title="Your profile picture" width="168" height="168"></svg></button>',
                'large and sticky': AVATAR_IMG+'<img alt="Profile picture" style="width:40px;height:40px" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">',
                'unique prefix SVG': '<svg id="avatar" role="img" aria-label="Profile picture actions" width="168" height="168"></svg>',
            }
            for name, avatar in avatars.items():
                reply, page = run(fixture(avatar=avatar))
                assert reply.get('ok') is True, (name, reply)
                page.close()
                print('PASS: avatar', name)
            for name, avatar in {
                'comparable duplicates': AVATAR_IMG+'<svg role="img" aria-label="Profile picture" width="160" height="160"></svg>',
                'other person': '<img alt="Other Person\'s profile picture" width="168" height="168">',
                'prefix label': '<img alt="Profile picture of Other Person" width="168" height="168">',
                'prefix inside banner': '<div role="banner"><svg id="avatar" role="img" aria-label="Profile picture actions" width="168" height="168"></svg></div>',
                'ambiguous prefix SVGs': '<svg id="avatar" role="img" aria-label="Profile picture actions" width="168" height="168"></svg><svg role="img" aria-label="Profile picture options" width="168" height="168"></svg>',
            }.items():
                reply, page = run(fixture(avatar=avatar))
                assert reply.get('ok') is False, (name, reply)
                assert page.evaluate('window.__changed') == []
                assert page.evaluate('window.__saved') == 0
                page.close()
                print('PASS: avatar', name, 'stops untouched')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
