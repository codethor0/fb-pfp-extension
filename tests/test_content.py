"""End-to-end test of fb-pfp-extension content.js against a mock Facebook page.

Loads a static HTML page that reproduces the profile-page structure (cover
avatar, menu item, dialog with a file input and Save button), injects the
real content.js with a chrome.runtime stub, and sends it the same message
popup.js sends. Verifies both the dry-run path and the full save path,
including that a random File lands on the input and Save actually fires.
"""
import pathlib
import sys

from playwright.sync_api import sync_playwright

# Resolve the extension root relative to this test file, so the test runs
# from any checkout without machine-specific paths.
EXT = pathlib.Path(__file__).resolve().parent.parent
content_js = (EXT / "content.js").read_text()

MOCK = """
<!DOCTYPE html><html><body>
<img aria-label="Profile picture" src="x" style="width:50px;height:50px">
<div role="menuitem" style="width:100px;height:20px">Update profile picture</div>
<div role="dialog" style="width:300px;height:200px">
  <span>Choose profile picture</span>
  <input type="file">
  <div role="button">Save</div>
</div>
<script>
  window.__saved = 0;
  document.querySelectorAll("[role='button']").forEach(b =>
    b.addEventListener("click", () => {
      if (/^save/i.test(b.textContent)) {
        window.__saved++;
        setTimeout(() => b.closest("[role='dialog']").remove(), 200);
      }
    }));
  window.__picked = null;
  document.querySelector("input[type=file]").addEventListener("change", e => {
    window.__picked = e.target.files[0] ? e.target.files[0].name : null;
  });
</script>
</body></html>
"""

IMAGE = {"name": "me.jpg", "type": "image/jpeg", "data": b"\xff\xd8\xff fake-jpeg-bytes"}


def run_case(pw, dry_run, expect_saved):
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.route("https://www.facebook.com/me", lambda route: route.fulfill(body=MOCK, content_type="text/html"))
    page.goto("https://www.facebook.com/me")
    page.evaluate(
        """([src, stub]) => {
            window.chrome = { runtime: { onMessage: { addListener: (fn) => { window.__handler = fn; } } } };
            eval(src);
            window.__send = (msg) => new Promise((resolve) => window.__handler(msg, {}, resolve));
        }""",
        [content_js, None],
    )
    reply = page.evaluate(
        "(msg) => window.__send(msg)",
        {"type": "fb-pfp:run", "image": IMAGE, "dryRun": dry_run},
    )
    picked = page.evaluate("window.__picked")
    saved = page.evaluate("window.__saved")
    browser.close()
    assert reply.get("ok"), f"run failed: {reply}"
    assert picked == "me.jpg", f"file never reached the input (picked={picked})"
    if expect_saved:
        assert saved == 1, f"Save never clicked (saved={saved})"
    else:
        assert saved == 0, "dry run must not click Save"
    return reply


with sync_playwright() as pw:
    dry = run_case(pw, dry_run=True, expect_saved=False)
    print("dry run:", dry)
    full = run_case(pw, dry_run=False, expect_saved=True)
    print("full run:", full)
print("ALL CONTENT-SCRIPT TESTS PASSED")
