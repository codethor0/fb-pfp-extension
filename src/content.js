// Operates only in the Facebook profile-picture dialog. Does not handle credentials.
(() => {
  'use strict';

  const WAIT_MS = 12000;
  let working = false;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  function visible(element) {
    return !!(element && element.getClientRects().length &&
      getComputedStyle(element).visibility !== 'hidden' &&
      getComputedStyle(element).display !== 'none');
  }

  function label(element) {
    return String(element.getAttribute('aria-label') || element.getAttribute('alt') || element.textContent || '').trim();
  }

  function usableButton(element) {
    return visible(element) && !element.disabled && element.getAttribute('aria-disabled') !== 'true';
  }

  function uniqueClick(root, pattern) {
    const matches = [...root.querySelectorAll('button, [role="button"], [role="menuitem"], [role="link"]')]
      .filter(el => usableButton(el) && pattern.test(label(el)));
    return matches.length === 1 ? matches[0] : null;
  }

  async function waitUntil(find, timeout = WAIT_MS) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      const match = find();
      if (match) return match;
      await sleep(200);
    }
    return null;
  }

  function ownAvatar() {
    // Fail closed on ambiguous matches instead of clicking someone else's image.
    const images = [...document.querySelectorAll('img[alt], [role="img"][aria-label]')].filter(visible);
    const exact = images.filter(el => /^(?:your )?profile picture$/i.test(label(el)));
    if (exact.length === 1) return exact[0];
    if (exact.length > 1) return null;
    const fallback = images.filter(el => /^profile picture\b/i.test(label(el)));
    return fallback.length === 1 ? fallback[0] : null;
  }

  function profileDialog() {
    const matches = [...document.querySelectorAll('[role="dialog"], dialog')]
      .filter(el => visible(el) && /profile picture/i.test(`${el.getAttribute('aria-label') || ''} ${el.textContent || ''}`));
    return matches.length === 1 ? matches[0] : null;
  }

  function showNotice(message, error = false) {
    document.querySelector('#fb-pfp-status')?.remove();
    const node = document.createElement('div');
    node.id = 'fb-pfp-status';
    node.setAttribute('role', 'status');
    node.style.cssText = 'position:fixed;z-index:2147483647;bottom:24px;right:24px;max-width:360px;' +
      'background:#132338;color:white;border:2px solid ' + (error ? '#f87171' : '#38bdf8') +
      ';border-radius:10px;padding:14px 18px;font:14px/1.4 system-ui;box-shadow:0 5px 25px #0006';
    node.textContent = message;
    document.body?.appendChild(node);
  }

  function validatePage() {
    if (location.protocol !== 'https:' || location.hostname !== 'www.facebook.com') {
      throw new Error('This extension runs only on https://www.facebook.com');
    }
    if (/^\/(login|checkpoint)(?:\/|$|\.php)/i.test(location.pathname)) {
      throw new Error('Log in to Facebook in this browser, then retry');
    }
    if (/^\/(?:home(?:\.php)?)?$/i.test(location.pathname)) {
      throw new Error('Facebook did not open your profile. No photo selected.');
    }
  }

  function decodeBytes(base64) {
    if (typeof base64 !== 'string' || base64.length > 4_500_000 ||
        !/^[A-Za-z0-9+/]+={0,2}$/.test(base64)) throw new Error('Invalid or oversized image payload');
    const raw = atob(base64);
    if (raw.length < 3 || raw.length > 3 * 1024 * 1024) throw new Error('Invalid image size');
    const bytes = Uint8Array.from(raw, value => value.charCodeAt(0));
    if (bytes[0] !== 0xff || bytes[1] !== 0xd8 || bytes[2] !== 0xff) throw new Error('Image is not JPEG');
    return bytes;
  }

  async function uploadIntoDialog(bytes) {
    const avatar = await waitUntil(ownAvatar);
    if (!avatar) throw new Error('Could not uniquely identify your own profile picture. Check the English Facebook UI.');
    (avatar.closest('button, [role="button"]') || avatar).click();

    const chooser = await waitUntil(() => uniqueClick(document, /^(?:choose|update) profile picture$/i));
    if (!chooser) throw new Error('Choose profile picture action was not uniquely identified');
    chooser.click();

    const dialog = await waitUntil(profileDialog);
    if (!dialog) throw new Error('Profile-picture dialog did not open; no image was uploaded');
    let input = await waitUntil(() => dialog.querySelector('input[type="file"]'), 4000);
    if (!input) {
      const uploadButton = uniqueClick(dialog, /^(?:upload|add|choose) photo$/i);
      if (uploadButton) uploadButton.click();
      input = await waitUntil(() => dialog.querySelector('input[type="file"]'), 8000);
    }
    if (!input) throw new Error('No file input inside the profile-picture dialog; stopped safely');
    const file = new File([bytes], 'profile-photo.jpg', {type: 'image/jpeg'});
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
    if (input.files?.length !== 1 || input.files[0].size !== bytes.length) {
      throw new Error('Facebook did not receive the selected image file');
    }
    return dialog;
  }

  async function saveIfRequested(dialog) {
    // Intermediate steps vary by Facebook UI version. All clicks stay dialog scoped.
    await sleep(1500);
    let save = uniqueClick(dialog, /^save(?: changes)?$/i);
    for (let attempt = 0; !save && attempt < 2; attempt++) {
      const next = uniqueClick(dialog, /^(?:select photo|next)$/i);
      if (!next) break;
      next.click();
      await sleep(700);
      save = uniqueClick(dialog, /^save(?: changes)?$/i);
    }
    if (!save) save = await waitUntil(() => uniqueClick(dialog, /^save(?: changes)?$/i));
    if (!save) throw new Error('Save button did not become available; no automatic Save attempted');
    save.click();
    const closed = await waitUntil(() => (!dialog.isConnected || !visible(dialog)) && true, 30000);
    if (!closed) throw new Error('Save was clicked but dialog did not close; result is unknown');
    return {ok: true, saved: true, stage: 'save-click-acknowledged'};
  }

  async function run(message) {
    validatePage();
    if (message.mime !== 'image/jpeg' || message.fileName !== 'profile-photo.jpg') {
      throw new Error('Invalid image metadata');
    }
    const bytes = decodeBytes(message.data);
    const dialog = await uploadIntoDialog(bytes);
    if (message.publish !== true) {
      showNotice('fb-pfp: Picture prepared. Check the preview, then click Save yourself.');
      return {ok: true, saved: false, stage: 'review'};
    }
    const result = await saveIfRequested(dialog);
    showNotice('fb-pfp: Save acknowledged by the Facebook dialog. Verify your profile picture.');
    return result;
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== 'PREPARE_PHOTO') return false;
    if (working) {sendResponse({ok: false, error: 'Another operation is in progress'}); return false;}
    working = true;
    run(message)
      .then(sendResponse)
      .catch(error => {
        const explanation = error instanceof Error ? error.message : 'Unexpected profile photo error';
        showNotice(`fb-pfp: ${explanation}`, true);
        sendResponse({ok: false, error: explanation.slice(0, 250)});
      })
      .finally(() => {working = false;});
    return true;
  });
})();
