/* fb-pfp content script: drives the Facebook "Choose profile picture" dialog.
 *
 * Mirrors the design rules of the audited Python CLI (github.com/codethor0/
 * fb-profile-pic-automation):
 * - Every lookup is by visible text, never generated class names.
 * - The file input is only ever touched inside the profile-picture dialog,
 *   never page-wide (a page-wide input could belong to the post composer).
 * - Randomized pauses instead of fixed delays.
 * - Dry run stops before Save; a run only succeeds after the dialog closes.
 *
 * Injected by popup.js after the profile page has loaded. Exposes a single
 * message handler; removes itself when done.
 */

(function () {
  if (window.__fbPfpInstalled) return;
  window.__fbPfpInstalled = true;

  const TEXT = {
    dialog: /profile picture/i,
    menuItem: /(choose|update) profile picture/i,
    uploadFallback: /upload photo|add photo|choose photo/i,
    save: /^save( changes)?$/i,
    next: [/^select photo$/i, /^next$/i],
  };

  const sleep = (ms) =>
    new Promise((r) => setTimeout(r, ms + Math.floor(Math.random() * 700)));

  const fail = (msg) => ({ ok: false, error: msg });

  function visible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  async function waitFor(findFn, what, timeoutMs = 15000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const el = findFn();
      if (el && visible(el)) return el;
      await sleep(250);
    }
    throw new Error(`${what} did not appear`);
  }

  function byText(selector, pattern, root = document) {
    for (const el of root.querySelectorAll(selector)) {
      const label = (el.getAttribute("aria-label") || el.textContent || "").trim();
      if (pattern.test(label)) return el;
    }
    return null;
  }

  function profileDialog() {
    for (const el of document.querySelectorAll('[role="dialog"]')) {
      if (TEXT.dialog.test(el.textContent || "")) return el;
    }
    return null;
  }

  async function clickAvatar() {
    // Prefer the exact accessible name; fall back to the first in-document
    // match, which on a profile page is the cover avatar (it precedes feed
    // images in DOM order).
    const exact = document.querySelector('img[aria-label="Profile picture"]');
    const loose = () => {
      for (const el of document.querySelectorAll('img[aria-label]')) {
        if (/profile picture/i.test(el.getAttribute("aria-label"))) return el;
      }
      return null;
    };
    const avatar = (exact && visible(exact)) ? exact : await waitFor(loose, "Profile-picture avatar");
    await sleep(600);
    avatar.click();
  }

  async function handFileToDialog(fileData, name, type) {
    const dialog = await waitFor(profileDialog, "Profile-picture dialog");
    let input = dialog.querySelector("input[type='file']");
    if (!input) {
      const btn = byText("div[role='button'],button", TEXT.uploadFallback, dialog);
      if (btn) {
        await sleep(500);
        btn.click();
      }
      input = await waitFor(() => dialog.querySelector("input[type='file']"), "File input in dialog");
    }
    const file = new File([fileData], name, { type });
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function saveIfNeeded(dryRun) {
    const dialog = await waitFor(profileDialog, "Profile-picture dialog (save)");
    if (dryRun) return { saved: false };

    const saveBtn = () => byText("div[role='button'],button", TEXT.save, dialog);
    let btn = saveBtn();
    if (!btn) {
      for (const pattern of TEXT.next) {
        const next = byText("div[role='button'],button", pattern, dialog);
        if (next) {
          await sleep(800);
          next.click();
          break;
        }
      }
      btn = await waitFor(saveBtn, "Save button");
    }
    await sleep(600);
    btn.click();
    // Success means the dialog actually closed.
    const deadline = Date.now() + 30000;
    while (Date.now() < deadline) {
      if (!profileDialog()) return { saved: true };
      await sleep(500);
    }
    throw new Error("Dialog did not close after Save");
  }

  async function run(image, dryRun) {
    if (!/facebook\.com/.test(location.hostname)) {
      return fail("Not on facebook.com");
    }
    const path = location.pathname.toLowerCase().replace(/\/+$/, "").replace(/\.php$/, "");
    if (path === "/login" || path === "/checkpoint" || path.startsWith("/checkpoint/")) {
      return fail("Facebook is asking to log in. Log in, then retry.");
    }
    try {
      await clickAvatar();
      const menuItem = await waitFor(
        () => byText('[role="menuitem"],div[role="button"],a[role="link"]', TEXT.menuItem),
        "'Choose profile picture' menu item"
      );
      await sleep(900);
      menuItem.click();
      await handFileToDialog(image.data, image.name, image.type);
      await sleep(1500);
      const result = await saveIfNeeded(dryRun);
      return result.saved
        ? { ok: true, saved: true }
        : { ok: true, saved: false };
    } catch (err) {
      return fail(String((err && err.message) || err));
    }
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (!msg || msg.type !== "fb-pfp:run") return false;
    run(msg.image, msg.dryRun).then(sendResponse);
    return true; // async response
  });
})();
