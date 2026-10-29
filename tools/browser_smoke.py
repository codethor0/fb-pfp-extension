#!/usr/bin/env python3
"""Offline content-flow regressions on synthetic DOM pages, never on Facebook."""
import argparse
import base64
import io
import os
import shutil
import sys
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
    'wrong-name-mentions-picture': 'add(\'<div role="dialog" id="post-dialog" aria-label="Create post"><h2>Create post</h2>\'+TARGET+\'<p>Pick a profile picture angle for this post</p></div>\');',
    'named-wins-over-unnamed': 'add(dialogHtml(CONTENT+TARGET));add(\'<div role="dialog" id="unnamed"><p>profile picture</p><input id="decoy" type="file" accept="image/*"></div>\');',
}
CHANGES = {
    'accepted': 'preview(file);',
    'clearing-input': "e.target.value='';preview(file);",
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
    'cdn-preview': "const img=document.createElement('img');img.src='http://cdn.fb-pfp.fixture/staged.jpg';img.onload=()=>window.__accepted=true;document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'cdn-ninepoint': "const img=document.createElement('img');img.src='http://cdn.fb-pfp.fixture/ninepoint.jpg';img.onload=()=>window.__accepted=true;document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'cdn-wrong': "const img=document.createElement('img');img.src='http://cdn.fb-pfp.fixture/wrong.jpg';img.onload=()=>window.__accepted=true;document.querySelector('[role=\"dialog\"]').appendChild(img);",
    'centered-crop': "const canvas=document.createElement('canvas');canvas.width=canvas.height=180;document.querySelector('[role=\"dialog\"]').appendChild(canvas);const img=new Image();img.onload=()=>{const size=Math.min(img.naturalWidth,img.naturalHeight);canvas.getContext('2d').drawImage(img,(img.naturalWidth-size)/2,(img.naturalHeight-size)/2,size,size,0,0,180,180);window.__accepted=true;};img.src=URL.createObjectURL(file);",
    'hidden-after-verify': 'preview(file);setTimeout(()=>{document.querySelector("#preview").style.display="none";},50);',
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


# LinkedIn fixtures mirror the probed structure in docs/linkedin-adapter-spec.md:
# a cover photo, a top-card empty-alt photo, and a viewer dialog carrying an h2
# "Profile photo" plus img[alt="Profile image"]. Nothing here is a live DOM claim
# beyond that spec.
LI_BASE = r'''
<style>[hidden]{display:none!important}button,img{display:block;margin:12px}#cover{width:792px;height:198px}#avatar,.dup{width:120px;height:120px}</style>
<img id="cover" alt="Cover photo" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">
LI_AVATAR
<script>
const add=html=>document.body.insertAdjacentHTML('beforeend',html);
const viewer=inner=>`<div role="dialog" id="viewer">${inner}</div>`;
const HEADING='<h2>Profile photo</h2>';
const PREVIEW='<img alt="Profile image" id="big" width="400" height="400" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">';
const ACTIONS='<button aria-label="Update photo" id="update">u</button><button aria-label="Dismiss" id="dismiss">x</button>';
LI_LAYOUT
</script>
'''
LI_LAYOUTS = {
    'normal': "document.querySelector('#card').addEventListener('click',()=>add(viewer(HEADING+PREVIEW+ACTIONS)));",
    'missing-heading': "document.querySelector('#card').addEventListener('click',()=>add(viewer('<span>Profile photo</span>'+PREVIEW+ACTIONS)));",
    'missing-preview': "document.querySelector('#card').addEventListener('click',()=>add(viewer(HEADING+ACTIONS+'<span>Profile photo</span>')));",
    'wrong-heading': "document.querySelector('#card').addEventListener('click',()=>add(viewer('<h2>People also viewed</h2><span>Profile photo</span>'+PREVIEW)));",
    'danger-frames': "document.querySelector('#card').addEventListener('click',()=>add(viewer(HEADING+PREVIEW+'<button aria-label=\"Frames\">f</button>'+ACTIONS)));",
}
LI_AVATARS = {
    'normal': '<button id="card"><img id="avatar" alt="" width="120" height="120" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></button>',
    'duplicate': '<button id="card"><img id="avatar" alt="" width="120" height="120" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="></button><img class="dup" alt="" width="120" height="120" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">',
    'absent': '<div id="card"></div>',
}


def li_fixture(layout='normal', avatar='normal'):
    return ('<!doctype html><html><body>'+LI_BASE.replace('LI_AVATAR', LI_AVATARS[avatar])
            .replace('LI_LAYOUT', LI_LAYOUTS[layout])+'</body></html>')


def image_payload(color=(20, 155, 220)):
    output = io.BytesIO()
    Image.new('RGB', (180, 180), color).save(output, 'JPEG')
    return base64.b64encode(output.getvalue()).decode('ascii')


def ninepoint_collision_payload(selected=(20, 155, 220), wrong=(200, 40, 90)):
    """A wrong image that matches the selected photo at the content script's
    legacy nine sample positions (uniform 7x7 blocks keep those pixels stable
    through JPEG recompression) while every other pixel differs materially.
    This exact image passed the old nine-sample comparison in an offline
    reproduction; the full-pixel comparison must reject it."""
    image = Image.new('RGB', (32, 32), wrong)
    for fy in (0.25, 0.5, 0.75):
        for fx in (0.25, 0.5, 0.75):
            cx, cy = int(31 * fx), int(31 * fy)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    image.putpixel(((cx + dx) % 32, (cy + dy) % 32), selected)
    output = io.BytesIO()
    image.save(output, 'JPEG', quality=90)
    return base64.b64encode(output.getvalue()).decode('ascii')


def rectangular_payload(width, height):
    image = Image.new('RGB', (width, height))
    image.putdata([(round(x * 255 / (width - 1)), round(y * 200 / (height - 1)),
                    255 - round(x * 255 / (width - 1)))
                   for y in range(height) for x in range(width)])
    output = io.BytesIO()
    image.save(output, 'JPEG', quality=95)
    return base64.b64encode(output.getvalue()).decode('ascii')


def rebranded_gecko_launcher(play):
    """Prepare a rebranded copy of playwright's Firefox for macOS 27.

    On macOS 27, TCC protects ~/Library/Application Support/Firefox, so any
    command-line-spawned Firefox (playwright's bundled build included) is
    denied its app-data dir and exits with "Could not find profile folder".
    See microsoft/playwright#42768. Pointing the same binary at an identical
    application.ini whose Name/Vendor are distinct makes it resolve a
    non-protected app-data dir instead. -app must be the first argument,
    which playwright cannot express through launch options, so a tiny
    launcher script reorders the arguments before exec'ing the real binary.
    The copy lives in the user cache keyed by the playwright build number
    and is never shipped.
    """
    source_exe = Path(play.firefox.executable_path).resolve()
    bundle = source_exe.parents[2]            # .../firefox-NNNN/firefox/Nightly.app
    build = bundle.parents[1].name            # firefox-NNNN
    cache = Path.home() / '.cache' / 'fb-pfp' / 'gecko-battery' / build
    launcher = cache / 'firefox-launcher.sh'
    if launcher.exists():
        return launcher
    staged = cache / bundle.name
    if not staged.exists():
        shutil.copytree(bundle, staged)
    ini_source = bundle / 'Contents' / 'Resources' / 'application.ini'
    ini_target = staged / 'Contents' / 'Resources' / 'browser' / 'application.ini'
    ini_target.parent.mkdir(parents=True, exist_ok=True)
    text = ini_source.read_text()
    text = text.replace('Vendor=Mozilla', 'Vendor=fbpfp')
    text = text.replace('Name=Firefox', 'Name=fbpfp-battery')
    ini_target.write_text(text)
    real = staged / 'Contents' / 'MacOS' / 'firefox'
    launcher.write_text(f'#!/bin/sh\nexec "{real}" -app "{ini_target}" "$@"\n')
    launcher.chmod(0o755)
    return launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', choices=('chromium', 'firefox'), default='chromium',
                        help='engine to run the synthetic DOM battery on')
    args = parser.parse_args()
    with sync_playwright() as play:
        launch = {'headless': True}
        if args.browser == 'chromium' and os.getenv('CHROMIUM_PATH'):
            launch['executable_path'] = os.environ['CHROMIUM_PATH']
        if args.browser == 'chromium' and os.getenv('CDP_URL'):
            # Branded Chromium builds (Microsoft Edge) refuse a command-line
            # --user-data-dir: their data-dir name is compiled into the brand
            # and macOS TCC denies a CLI-spawned process the protected default
            # dir, so playwright cannot launch them directly. Launch the
            # browser yourself (for Edge: open -na "Microsoft Edge" --args
            # --headless=new --remote-debugging-port=9223 about:blank) and
            # point CDP_URL at http://localhost:9223.
            browser = play.chromium.connect_over_cdp(os.environ['CDP_URL'])
        elif args.browser == 'firefox':
            try:
                browser = play.firefox.launch(headless=True)
            except Exception as first_exc:
                # Environment limitation, not a code failure: macOS 27 TCC
                # denies command-line-spawned Firefox processes access to the
                # TCC-protected app-data dir. See microsoft/playwright#42768.
                # Relaunch once under a rebranded app-data dir; if that also
                # fails, skip. The Chromium pass stays the hard gate.
                try:
                    launcher = rebranded_gecko_launcher(play)
                    browser = play.firefox.launch(executable_path=str(launcher), headless=True)
                    print(f'PASS: firefox relaunched under rebranded app-data dir ({launcher.parent.name})')
                except Exception as second_exc:
                    print(f'SKIP: firefox engine unavailable here: {str(second_exc).splitlines()[0][:160]}')
                    return
        else:
            browser = play.chromium.launch(**launch)
        print(f'PASS: harness launched on {args.browser} {browser.version}')
        try:
            timing_pairs = [('const WAIT_MS = 12000;', 'const WAIT_MS = 900;'),
                            ('const DIALOG_WAIT_MS = 25000;', 'const DIALOG_WAIT_MS = 3000;'),
                            ('const UPLOAD_SETTLE_MS = 2500;', 'const UPLOAD_SETTLE_MS = 150;'),
                            ('const PREVIEW_SETTLE_MS = 600;', 'const PREVIEW_SETTLE_MS = 200;'),
                            ('const SAVE_SETTLE_MS = 1500;', 'const SAVE_SETTLE_MS = 400;'),
                            ('const SAVE_WAIT_MS = 30000;', 'const SAVE_WAIT_MS = 1400;')]

            def apply_test_patches(text, strip_validate=True):
                if strip_validate:
                    # Synthetic page: no live Facebook origin.
                    text = text.replace('    validatePage();', '    /* validatePage stripped by the battery */')
                for before, after in timing_pairs:
                    text = text.replace(before, after)
                return text

            source = apply_test_patches(CONTENT.read_text())

            # Guard tests run the real validatePage against stubbed location
            # pieces, so the fail-closed site guards have offline coverage:
            # disabled adapters, unknown hosts, http, and the login wall.
            guard_source = apply_test_patches(CONTENT.read_text(), strip_validate=False)
            guard_source = (guard_source
                            .replace('location.protocol', '(window.__fakeProto||location.protocol)')
                            .replace('location.hostname', '(window.__fakeHost||location.hostname)')
                            .replace('location.pathname', '(window.__fakePath||location.pathname)'))

            def run(html, publish=False, user_input=False, data=None, routes=None, flaky_routes=None, fail_routes=None):
                page = browser.new_page()
                page.on('filechooser', lambda chooser: None)  # Intercept native pickers in negative fixtures.
                if routes or flaky_routes or fail_routes:
                    def make_handler(payload, extra_headers=None):
                        def handler(route):
                            headers = {'access-control-allow-origin': '*'}
                            headers.update(extra_headers or {})
                            route.fulfill(body=base64.b64decode(payload), content_type='image/jpeg',
                                          headers=headers)
                        return handler
                    for entry in (routes or []):
                        pattern, body = entry[0], entry[1]
                        page.route(pattern, make_handler(body, entry[2] if len(entry) > 2 else None))
                    for pattern, body in (flaky_routes or []):
                        def make_flaky(payload):
                            state = {'requests': 0}
                            def flaky_handler(route):
                                if route.request.resource_type != 'fetch':
                                    # Keep the element load working so the image stays a candidate.
                                    route.fulfill(body=base64.b64decode(payload), content_type='image/jpeg',
                                                  headers={'access-control-allow-origin': '*'})
                                    return
                                state['requests'] += 1
                                if state['requests'] == 1:
                                    route.abort()
                                else:
                                    route.fulfill(body=base64.b64decode(payload), content_type='image/jpeg',
                                                  headers={'access-control-allow-origin': '*'})
                            return flaky_handler
                        page.route(pattern, make_flaky(body))
                    for pattern in (fail_routes or []):
                        def fail_handler(route):
                            if route.request.resource_type != 'fetch':
                                route.fulfill(body=base64.b64decode(image_payload()), content_type='image/jpeg',
                                              headers={'access-control-allow-origin': '*'})
                            else:
                                route.abort()
                        page.route(pattern, fail_handler)
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

            def run_guard(host, proto='https:', path='/'):
                page = browser.new_page()
                page.set_content(fixture())
                page.evaluate('''({proto, host, path}) => {
                  window.chrome = {runtime: {id: "test-ext", onMessage: {addListener(fn) {window.__handler = fn;}}}};
                  window.__fakeProto = proto; window.__fakeHost = host; window.__fakePath = path;
                }''', {'proto': proto, 'host': host, 'path': path})
                page.add_script_tag(content=guard_source)
                reply = page.evaluate('''({data}) => new Promise(resolve => window.__handler(
                    {type: 'PREPARE_PHOTO', data, mime: 'image/jpeg', fileName: 'profile-photo.jpg', publish: false},
                    {id: 'test-ext'}, resolve))''', {'data': image_payload()})
                page.close()
                return reply

            def run_linkedin(layout='normal', avatar='normal', path='/in/self', overrides=()):
                # The LinkedIn adapter runs with its real guards and the real
                # validatePage; only the disabled flag is flipped on inside the
                # injected copy, plus any caller-supplied source overrides.
                page = browser.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.set_content(li_fixture(layout, avatar))
                page.evaluate('window.chrome={runtime:{id:"test-ext",onMessage:{addListener(fn){window.__handler=fn;}}}};')
                source = apply_test_patches(CONTENT.read_text(), strip_validate=False)
                source = source.replace(
                    "      hosts: ['www.linkedin.com'],\n      enabled: false,",
                    "      hosts: ['www.linkedin.com'],\n      enabled: true,")
                for old, new in overrides:
                    assert old in source, old
                    source = source.replace(old, new)
                source = (source
                          .replace('location.protocol', '(window.__fakeProto||location.protocol)')
                          .replace('location.hostname', '(window.__fakeHost||location.hostname)')
                          .replace('location.pathname', '(window.__fakePath||location.pathname)'))
                page.add_script_tag(content=source)
                page.evaluate('''({p}) => {
                  window.__fakeProto = "https:";
                  window.__fakeHost = "www.linkedin.com";
                  window.__fakePath = p;
                }''', {'p': path})
                reply = page.evaluate('''({data}) => new Promise(resolve=>window.__handler(
                    {type:'PREPARE_PHOTO',data,mime:'image/jpeg',fileName:'profile-photo.jpg',publish:false},
                    {id:'test-ext'},resolve))''', {'data': image_payload()})
                assert not errors, errors
                page.close()
                return reply

            for publish in (False, True):
                reply, page = run(fixture(), publish)
                assert reply.get('ok') is True and reply.get('saved') is publish, reply
                assert page.evaluate('window.__saved') == int(publish)
                assert page.evaluate('window.__changed') == ['target']
                page.close()
                print('PASS:', 'explicit Save acknowledged once' if publish else 'loaded preview reviewed without Save')

            reply, page = run(fixture(change='clearing-input'))
            assert reply.get('ok') is True and reply.get('saved') is False, reply
            assert page.evaluate('window.__changed') == ['target']
            assert page.locator('#composer').evaluate('e=>e.files.length') == 0
            page.close()
            print('PASS: an upload handler that clears the input after reading still counts as delivered')

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

            reply, page = run(fixture(change='cdn-preview'), True,
                              routes=[('http://cdn.fb-pfp.fixture/staged.jpg', image_payload())])
            assert reply.get('ok') is True and reply.get('saved') is True, reply
            assert page.evaluate('window.__accepted') is True
            assert page.evaluate('window.__saved') == 1
            page.close()
            print('PASS: a tainted cross-origin CDN preview is re-fetched untainted and verified before Save')

            reply, page = run(fixture(change='cdn-wrong'), True,
                              routes=[('http://cdn.fb-pfp.fixture/wrong.jpg', image_payload((230, 30, 40)))])
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: a cross-origin CDN preview with different pixels never reaches Save')

            reply, page = run(fixture(change='cdn-ninepoint'), True,
                              routes=[('http://cdn.fb-pfp.fixture/ninepoint.jpg', ninepoint_collision_payload())])
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            assert 'Could not verify the selected picture' in reply.get('error', ''), reply
            page.close()
            print('PASS: an image colliding only at the legacy nine sample positions never reaches Save')

            reply, page = run(fixture(change='cdn-preview'), True,
                              flaky_routes=[('http://cdn.fb-pfp.fixture/staged.jpg', image_payload())])
            assert reply.get('ok') is True and reply.get('saved') is True, reply
            assert page.evaluate('window.__saved') == 1
            page.close()
            print('PASS: a transient CDN fetch failure is retried and the preview still verifies before Save')

            reply, page = run(fixture(change='cdn-preview'), True,
                              fail_routes=['http://cdn.fb-pfp.fixture/staged.jpg'])
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: a CDN preview that keeps failing never reaches Save')

            reply, page = run(fixture(change='cdn-preview'), True,
                              routes=[('http://cdn.fb-pfp.fixture/staged.jpg', image_payload(),
                                       {'content-length': str(64 * 1024 * 1024)})])
            assert reply.get('ok') is False and page.evaluate('window.__saved') == 0, reply
            page.close()
            print('PASS: a CDN preview misreporting an oversized Content-Length never reaches Save')

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

            reply, page = run(fixture(layout='wrong-name-mentions-picture'), True)
            assert reply.get('ok') is False and page.evaluate('window.__changed') == [], reply
            assert page.evaluate('window.__saved') == 0
            page.close()
            print('PASS: a dialog with a different name that mentions profile pictures is not the target dialog')

            reply, page = run(fixture(layout='named-wins-over-unnamed'), True)
            assert reply.get('ok') is True and reply.get('saved') is True, reply
            assert page.evaluate('window.__changed') == ['target']
            page.close()
            print('PASS: a named profile-picture dialog wins over an unnamed lookalike')

            # Fail-closed site guards, exercised through the real validatePage
            # with stubbed location pieces. These lock the contracts: enabling
            # an adapter or broadening hosts is a deliberate change that must
            # update this block.
            for host, needle, label in [
                ('www.linkedin.com', 'not enabled in this build', 'linkedin contract stays disabled'),
                ('x.com', 'not enabled in this build', 'x contract stays disabled'),
                ('example.com', 'does not support example.com', 'unknown host is named'),
            ]:
                reply = run_guard(host)
                assert reply.get('ok') is False and needle in reply.get('error', ''), (host, reply)
                print('PASS: site guard:', label)
            reply = run_guard('www.facebook.com', proto='http:')
            assert reply.get('ok') is False and 'runs only on https' in reply.get('error', ''), reply
            print('PASS: site guard refuses http')
            reply = run_guard('www.facebook.com', path='/login.php')
            assert reply.get('ok') is False and 'Log in to Facebook' in reply.get('error', ''), reply
            print('PASS: site guard names the Facebook login wall')
            reply = run_guard('www.facebook.com', path='/codethor0')
            assert reply.get('ok') is True and reply.get('saved') is False, reply
            print('PASS: site guard passes a profile page through to the flow')
            reply = run_guard('www.facebook.com', path='/home')
            assert reply.get('ok') is False and 'No photo selected' in reply.get('error', ''), reply
            print('PASS: site guard refuses the Facebook home timeline')

            # LinkedIn offline half: the real adapter guards run with the
            # disabled flag flipped on inside the injected copy only. Every
            # run must fail closed, because the upload control labels are an
            # open live-probe item (docs/linkedin-adapter-spec.md).
            reply = run_linkedin()
            assert reply.get('ok') is False and 'not been verified against the live site' in reply.get('error', ''), reply
            print('PASS: linkedin stops at the unprobed upload control without staging anything')

            for layout in ('missing-heading', 'missing-preview', 'wrong-heading'):
                reply = run_linkedin(layout=layout)
                assert reply.get('ok') is False and 'did not match its verified structure' in reply.get('error', ''), (layout, reply)
                print('PASS: linkedin dialog identity rejects', layout)

            # Danger labels beside a verified upload action no longer abort the
            # run by themselves; the scoped guard only rejects destructive or
            # ambiguous action candidates. With the upload control still
            # unprobed, the run must now reach the fail-closed upload stop
            # instead of the old blanket danger abort.
            reply = run_linkedin(layout='danger-frames')
            assert reply.get('ok') is False and 'not been verified against the live site' in reply.get('error', ''), reply
            print('PASS: linkedin danger controls beside the upload action do not abort a valid dialog')

            # With a probed upload label injected, the run stages past the
            # danger controls; the fixture simply has no file input to find.
            upload = ("      uploadAction: null,\n", "      uploadAction: /^update photo$/i,\n")
            reply = run_linkedin(layout='danger-frames', overrides=(upload,))
            assert reply.get('ok') is False and 'No file input inside the profile-picture dialog' in reply.get('error', ''), reply
            print('PASS: linkedin stages past danger controls with a unique clean upload action')

            # An upload control whose label also matches a danger pattern is
            # an ambiguity between staging and destruction: fail closed.
            collision = ("      dangerLabels: /^(?:delete|remove|trash|frames?)$/i,\n",
                         "      dangerLabels: /^(?:delete|remove|trash|frames?|update photo)$/i,\n")
            reply = run_linkedin(overrides=(upload, collision))
            assert reply.get('ok') is False and 'destructive control matching the upload action' in reply.get('error', ''), reply
            print('PASS: linkedin danger-overlapping upload label fails closed')

            for avatar in ('duplicate', 'absent'):
                reply = run_linkedin(avatar=avatar)
                assert reply.get('ok') is False and 'Could not uniquely identify' in reply.get('error', ''), (avatar, reply)
                print('PASS: linkedin avatar', avatar, 'stops untouched')

            reply = run_linkedin(path='/feed/')
            assert reply.get('ok') is False and 'Open your own LinkedIn profile' in reply.get('error', ''), reply
            print('PASS: linkedin refuses non-profile pages')

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
                           'unrelated-gallery', 'unrelated-canvas', 'unreadable-preview', 'hidden-after-verify'):
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
                toast = page.locator('#fb-pfp-status').text_content()
                assert 'acknowledged' not in toast and 'did not confirm' in toast, (save, toast)
                page.close()
                print('PASS:', save, 'counts the Save click as used without claiming confirmation')

            reply, page = run(fixture(save='shell-gap-close'), True)
            assert reply.get('ok') is True and reply.get('saved') is True and reply.get('confirmed') is True, reply
            assert page.locator('[role="dialog"]').count() == 0
            assert 'acknowledged' in page.locator('#fb-pfp-status').text_content()
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
