#!/usr/bin/env python3
"""Replace a staged Chrome Web Store package and resubmit for review.

Drives the maintainer's own logged-in Chromium-family browser (Chrome,
Brave, and others) over the local Chrome DevTools Protocol port. It never
handles credentials itself; the browser session must already be signed in
to the Chrome Web Store developer dashboard.

Typical use after `python3 tools/build_release.py --out dist`:

    python3 tools/store_resubmit.py \
      --publisher YOUR-PUBLISHER-ID --item YOUR-ITEM-ID \
      --zip dist/fb-pfp-extension-v0.2.3-store.zip --wait

Single-pass mode (without --wait) prints one JSON result line and exits,
which suits an external scheduler: 0 submitted, 3 review still pending,
4 browser or session unreachable, 5 unexpected dashboard state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

EXIT_SUBMITTED = 0
EXIT_PENDING = 3
EXIT_UNREACHABLE = 4
EXIT_BLOCKED = 5


def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def manifest_version(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        import json as _json
        return _json.loads(archive.read('manifest.json'))['version']


def find_devconsole_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            if 'webstore/devconsole' in page.url:
                return page
    return None


def check_and_act(page, package_url, zip_path, expected_version, shots):
    """One pass. Returns (status, detail)."""
    page.goto(package_url, timeout=60000)
    page.wait_for_timeout(6000)
    if 'devconsole' not in page.url:
        return 'session_lost', f'redirected to {page.url}'
    text = page.locator('body').inner_text()
    upload = page.locator('text=Upload new package').first
    upload_ready = upload.count() > 0 and upload.is_enabled()
    if 'Pending review' in text and not upload_ready:
        return 'pending_review', 'a review is pending; package tab is locked'
    if not upload_ready:
        return 'pending_review', 'upload control not enabled; treating as locked'

    upload.click(timeout=30000)
    page.wait_for_timeout(3000)
    picker = page.locator('input[type="file"]').first
    if picker.count() == 0:
        page.screenshot(path=str(shots / 'no-picker.png'))
        return 'blocked', 'no file input appeared after the upload click'
    picker.set_input_files(str(zip_path))

    staged = False
    for _ in range(72):  # up to six minutes of server-side validation
        page.wait_for_timeout(5000)
        text = page.locator('body').inner_text()
        if expected_version in text:
            staged = True
            break
        if 'problem' in text.lower():
            page.screenshot(path=str(shots / 'validation-error.png'))
            return 'blocked', 'dashboard rejected the uploaded package'
    page.screenshot(path=str(shots / 'staged.png'))
    if not staged:
        return 'blocked', f'version {expected_version} not shown as staged after six minutes'

    clicked = False
    for _ in range(12):
        submit = page.get_by_text('Submit for review', exact=False).first
        try:
            if submit.count() and submit.is_visible():
                submit.click(timeout=15000)
                page.wait_for_timeout(3000)
                dialogs = page.locator('[role="dialog"]')
                for i in range(dialogs.count()):
                    dialog = dialogs.nth(i)
                    if not dialog.is_visible():
                        continue
                    confirm = dialog.get_by_text('Submit for review', exact=False).first
                    if confirm.count() and confirm.is_visible():
                        confirm.click(timeout=15000)
                        clicked = True
                        break
                break
        except Exception:
            pass
        page.wait_for_timeout(5000)
    page.wait_for_timeout(5000)
    page.screenshot(path=str(shots / 'final.png'))
    final_text = page.locator('body').inner_text()
    if clicked and 'Pending review' in final_text:
        return 'submitted', f'version {expected_version} staged and pending review'
    return 'blocked', 'upload finished but the submit state is unclear; see shots/final.png'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--publisher', required=True, help='Chrome Web Store publisher id')
    parser.add_argument('--item', required=True, help='Chrome Web Store item id')
    parser.add_argument('--zip', required=True, type=Path, help='store ZIP built by build_release.py')
    parser.add_argument('--cdp', default='http://127.0.0.1:9222', help='browser CDP endpoint')
    parser.add_argument('--sha256', help='expected SHA-256 of the ZIP')
    parser.add_argument('--wait', action='store_true', help='poll until the package tab unlocks')
    parser.add_argument('--max-days', type=float, default=7, help='give up after this many days')
    parser.add_argument('--shots', type=Path, default=Path('shots-store'), help='screenshot directory')
    args = parser.parse_args()

    result = {'status': 'error', 'detail': ''}
    exit_code = EXIT_BLOCKED
    try:
        zip_path = args.zip.expanduser().resolve()
        if not zip_path.is_file():
            raise SystemExit(f'store ZIP not found: {zip_path}')
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        if args.sha256 and digest != args.sha256:
            raise SystemExit(f'store ZIP sha256 mismatch: {digest}')
        expected_version = manifest_version(zip_path)
        log(f'upload target: {zip_path.name} version {expected_version} sha256 {digest[:16]}...')
        package_url = (f'https://chrome.google.com/webstore/devconsole/{args.publisher}'
                       f'/{args.item}/edit/package')
        shots = args.shots
        shots.mkdir(parents=True, exist_ok=True)

        from playwright.sync_api import sync_playwright

        deadline = time.time() + args.max_days * 86400
        attempt = 0
        while True:
            attempt += 1
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.connect_over_cdp(args.cdp)
                except Exception as exc:
                    result = {'status': 'waiting_brave', 'detail': f'CDP not reachable: {exc}'}
                    exit_code = EXIT_UNREACHABLE
                    break
                page = find_devconsole_page(browser)
                if page is None:
                    page = browser.contexts[0].new_page()
                try:
                    status, detail = check_and_act(page, package_url, zip_path,
                                                   expected_version, shots)
                except Exception as exc:
                    status, detail = 'blocked', f'unexpected error: {exc}'
                finally:
                    try:
                        browser.close()
                    except Exception:
                        pass
            result = {'status': status, 'detail': detail}
            if status == 'submitted':
                exit_code = EXIT_SUBMITTED
                break
            if status in ('session_lost', 'blocked'):
                exit_code = EXIT_UNREACHABLE if status == 'session_lost' else EXIT_BLOCKED
                break
            log(f'attempt {attempt}: {status}: {detail}')
            if not args.wait or time.time() > deadline:
                exit_code = EXIT_PENDING
                break
            time.sleep(300)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
    print(json.dumps(result))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
