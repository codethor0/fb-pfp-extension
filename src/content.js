// Site-adapter content script. The shared core drives a site's profile-picture
// dialog: scoped upload, untainted preview verification, gated Save.
// Adapters for sites whose DOM has not been probed on a logged-in session
// stay disabled by design. Does not handle credentials.
(() => {
  'use strict';

  const WAIT_MS = 12000;
  const DIALOG_WAIT_MS = 25000;     // the dialog opens empty; Facebook fills it in afterwards
  const UPLOAD_SETTLE_MS = 2500;    // a ready dialog may show its file input without any click
  const PREVIEW_SETTLE_MS = 600;
  const SAVE_SETTLE_MS = 1500;
  const SAVE_WAIT_MS = 30000;
  const PREVIEW_FETCH_RETRIES = 2;  // a transient CDN fetch failure must not stick for the whole wait
  const PREVIEW_FETCH_RETRY_MS = 400;
  const BUTTONS = 'button, [role="button"], [role="menuitem"], [role="link"]';
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
    const matches = [...root.querySelectorAll(BUTTONS)].filter(el => usableButton(el) && pattern.test(label(el)));
    return matches.length === 1 ? matches[0] : null;
  }

  function press(element) {
    // SVG elements have no click(); send the event instead.
    if (typeof element.click === 'function') element.click();
    else element.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
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

  function accessibleName(element) {
    return String(element.getAttribute('aria-label') || element.getAttribute('alt') || element.getAttribute('title') || '').trim();
  }

  function ownAvatar() {
    // The profile header and a small sticky avatar can share a name. Use the large exact match,
    // including SVG avatars, and stop when there are two comparable large matches.
    const named = [...document.querySelectorAll('img, [role="img"]')].filter(visible);
    const exact = named.filter(el => /^(?:your )?profile picture$/i.test(accessibleName(el)))
      .map(el => ({el, box: el.getBoundingClientRect()}))
      .filter(({box}) => box.width >= 80 && box.height >= 80)
      .sort((a, b) => b.box.width * b.box.height - a.box.width * a.box.height);
    if (exact.length) {
      const [first, second] = exact;
      if (second && second.box.width * second.box.height >= 0.9 * first.box.width * first.box.height) return null;
      return first.el;
    }
    // Some profile headers name the control "Profile picture actions". Keep that observed
    // prefix form only when one large target remains, excluding navigation and named people.
    const fallback = named.filter(el => /^profile picture\b/i.test(accessibleName(el)) &&
      !/^profile picture\s+(?:of|for)\b/i.test(accessibleName(el)) && !el.closest('[role="banner"]'))
      .filter(el => {const box = el.getBoundingClientRect(); return box.width >= 80 && box.height >= 80;});
    return fallback.length === 1 ? fallback[0] : null;
  }

  function profileDialogs() {
    const dialogs = [...document.querySelectorAll('[role="dialog"], dialog')].filter(visible);
    // Match on the accessible name first. A dialog named something else, such
    // as "Create post", can mention profile pictures in its body text without
    // being the profile-picture dialog, so named non-matches are excluded.
    const named = dialogs.filter(el => /profile picture/i.test(accessibleName(el)));
    const matches = named.length ? named
      : dialogs.filter(el => !accessibleName(el) && /profile picture/i.test(el.textContent || ''));
    // One dialog can sit inside another; the outermost one holds everything.
    return matches.filter(el => !matches.some(other => other !== el && other.contains(el)));
  }

  // Always look the dialog up again: Facebook shows it empty and can replace it while it loads, so an element
  // found early may be detached by the time its contents are ready.
  function profileDialog() {
    const matches = profileDialogs();
    return matches.length === 1 ? matches[0] : null;
  }

  const IMAGE_TYPE = /^(?:image\/[a-z0-9.+*-]+|\.(?:jpe?g|png|webp|heic|heif|gif|bmp))$/;

  function acceptedTypes(input) {
    return (input.getAttribute('accept') || '').toLowerCase().split(',').map(item => item.trim()).filter(Boolean);
  }

  function takesOnlyImages(input) {
    // Every used input must declare image types. The current Facebook dialog
    // holds no file input of its own; the Upload-photo path targets an
    // external input whose accept list is image-only. An input without an
    // accept attribute is not provably an image input, so it is never used.
    const types = acceptedTypes(input);
    return !input.disabled && types.length > 0 && types.every(type => IMAGE_TYPE.test(type));
  }

  function dialogInput() {
    const dialog = profileDialog();
    const inputs = dialog ? [...dialog.querySelectorAll('input[type="file"]')].filter(takesOnlyImages) : [];
    return inputs.length === 1 ? inputs[0] : null;
  }

  function uploadButton(dialog) {
    const matches = [...dialog.querySelectorAll(BUTTONS)].filter(el => usableButton(el) && /^(?:upload|add|choose) photo$/i.test(label(el)));
    // One control can be wrapped in several nested buttons with the same name; press the innermost.
    const innermost = matches.filter(el => !matches.some(other => other !== el && el.contains(other)));
    return innermost.length === 1 ? innermost[0] : null;
  }

  // "Upload photo" makes Facebook click a file input, which may sit outside the dialog. Watch for that click (and
  // keep the browser's own file picker from opening) so the input the dialog itself targets is the one used.
  async function inputFromUploadButton(button, progress) {
    const onClick = event => {
      if (!event.isTrusted && event.target instanceof HTMLInputElement && event.target.type === 'file') {
        event.preventDefault();
        if (progress.requested && progress.requested !== event.target) progress.ambiguous = true;
        else progress.requested = event.target;
      }
    };
    window.addEventListener('click', onClick, true);
    try {
      // Attribute an external input only to the synchronous Upload-photo handler. Unrelated
      // user clicks and later page activity must never become the extension's upload target.
      press(button);
    } finally {
      window.removeEventListener('click', onClick, true);
    }
    if (progress.ambiguous) throw new Error('Upload photo requested multiple file inputs; stopped safely');
    return waitUntil(() => {
      if (!profileDialog()) return null;
      return progress.requested && progress.requested.isConnected && takesOnlyImages(progress.requested)
        ? progress.requested : dialogInput();
    }, WAIT_MS);
  }

  async function findFileInput(progress) {
    const deadline = Date.now() + DIALOG_WAIT_MS;
    let readySince = 0;
    while (Date.now() < deadline) {
      const input = dialogInput();
      if (input) return input;
      const dialog = profileDialog();
      const button = dialog && !progress.pressed ? uploadButton(dialog) : null;
      if (!button) readySince = 0;
      else if (!readySince) readySince = Date.now();
      else if (Date.now() - readySince >= UPLOAD_SETTLE_MS) {
        progress.pressed = true;
        return inputFromUploadButton(button, progress);
      }
      await sleep(200);
    }
    return null;
  }

  function dialogReport(progress) {
    // Counts only: nothing from the page is copied into the message.
    const dialogs = profileDialogs();
    const root = dialogs.length === 1 ? dialogs[0] : null;
    const count = selector => (root ? root.querySelectorAll(selector).length : 0);
    return `dialogs ${dialogs.length}, elements ${count('*')}, buttons ${count(BUTTONS)}, file inputs ${count('input[type="file"]')}` +
      `, on page ${document.querySelectorAll('input[type="file"]').length}, upload pressed ${progress.pressed ? 'yes' : 'no'}` +
      `, picker requested ${progress.requested ? 'yes' : 'no'}`;
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

  // Site adapters. Each adapter owns the site-specific labels and guards; the
  // upload, preview verification and gated Save flow below is shared core.
  // An adapter must never be enabled from guesses: probe the logged-in DOM on
  // the real site first, then set enabled to true deliberately.
  const SITES = {
    facebook: {
      id: 'facebook',
      hosts: ['www.facebook.com'],
      enabled: true,
      chooseAction: /^(?:choose|update) profile picture$/i,
      saveAction: /^save(?: changes)?$/i,
      nextAction: /^(?:select photo|next)$/i,
      errorHint: 'Check the English Facebook UI.',
    },
    linkedin: {
      id: 'linkedin',
      hosts: ['www.linkedin.com'],
      enabled: false,
      note: 'Contract only. LinkedIn restricts automation; ship disabled until the logged-in DOM is probed.',
    },
    x: {
      id: 'x',
      hosts: ['x.com', 'www.x.com', 'mobile.x.com', 'twitter.com'],
      enabled: false,
      note: 'Contract only. X restricts automation; ship disabled until the logged-in DOM is probed.',
    },
  };

  function siteFor(hostname) {
    return Object.values(SITES).find(site => site.hosts.includes(hostname)) || null;
  }

  let activeSite = null;

  function validatePage() {
    if (location.protocol !== 'https:') {
      throw new Error('This extension runs only on https sites');
    }
    const site = siteFor(location.hostname);
    if (!site) throw new Error(`This extension does not support ${location.hostname}`);
    if (!site.enabled) throw new Error(`Support for ${site.id} is not enabled in this build`);
    activeSite = site;
    if (site.id === 'facebook') {
      if (/^\/(login|checkpoint)(?:\/|$|\.php)/i.test(location.pathname)) {
        throw new Error('Log in to Facebook in this browser, then retry');
      }
      if (/^\/(?:home(?:\.php)?)?$/i.test(location.pathname)) {
        throw new Error('Facebook did not open your profile. No photo selected.');
      }
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

  function previewSource(image) {
    return image.currentSrc || image.getAttribute('src') || '';
  }

  function pictureSamples(picture, crop = null) {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 32;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      if (crop) ctx.drawImage(picture, crop.x, crop.y, crop.size, crop.size, 0, 0, 32, 32);
      else ctx.drawImage(picture, 0, 0, 32, 32);
      // Every pixel of the comparison participates. Nine sample positions were
      // audit-proven bypassable: two images crafted to agree only at those
      // positions passed verification while most pixels differed materially.
      return [...ctx.getImageData(0, 0, 32, 32).data];
    } catch { return null; }
  }

  // Per-pixel tolerance against the 32x32 reference. A small fixed budget of
  // outlier pixels absorbs CDN recompression spikes on single pixels; a
  // materially different image always exhausts it and fails closed.
  const TOLERANCE = 24;
  const MAX_OUTLIER_PIXELS = 10;  // ~1% of the 32x32 comparison

  function matchesPicture(samples, expectedVariants) {
    if (samples === null) return false;
    return expectedVariants.some(expected => {
      if (samples.length !== expected.length) return false;
      let outliers = 0;
      for (let pixel = 0; pixel < samples.length; pixel += 4) {
        for (let channel = 0; channel < 3; channel++) {
          if (Math.abs(samples[pixel + channel] - expected[pixel + channel]) > TOLERANCE) {
            outliers++;
            break;
          }
        }
        if (outliers > MAX_OUTLIER_PIXELS) return false;
      }
      return true;
    });
  }

  async function expectedPicture(bytes) {
    let bitmap;
    try {
      bitmap = await createImageBitmap(new Blob([bytes], {type: 'image/jpeg'}));
      if (bitmap.width > 1600 || bitmap.height > 1600) throw new Error('Unsupported normalized image dimensions');
      const samples = pictureSamples(bitmap);
      if (!samples) throw new Error('Could not read the selected image');
      const size = Math.min(bitmap.width, bitmap.height);
      const centered = pictureSamples(bitmap, {x: (bitmap.width - size) / 2, y: (bitmap.height - size) / 2, size});
      return centered ? [samples, centered] : [samples];
    } catch {
      throw new Error('The selected JPEG could not be decoded; no image was uploaded');
    } finally { bitmap?.close(); }
  }

  function previewSnapshot(dialog, expected) {
    return {
      sources: new Set([...dialog.querySelectorAll('img')].map(previewSource)),
      canvases: new Map([...dialog.querySelectorAll('canvas')].map(canvas => [canvas, canvasPicture(canvas)])),
      verified: new Set(),
      checked: new Map(),
      expected
    };
  }

  function candidateImages(dialog, before) {
    const pictureSized = element => {
      const box = element.getBoundingClientRect();
      return visible(element) && box.width >= 80 && box.height >= 80;
    };
    return [...dialog.querySelectorAll('img')].filter(image => pictureSized(image) &&
      image.complete && image.naturalWidth > 0 && image.naturalHeight > 0 &&
      previewSource(image) && !before.sources.has(previewSource(image)));
  }

  // Facebook serves staged previews from a CDN that taints canvases, which
  // makes direct getImageData sampling fail. The CDN allows cross-origin
  // reads from www.facebook.com, so re-fetch the bytes untainted and compare
  // those. Same-origin, blob and data images are sampled directly. Fetched
  // previews are size-capped: a hostile or broken page must not be able to
  // push an unbounded image into createImageBitmap.
  const MAX_PREVIEW_BYTES = 32 * 1024 * 1024;
  async function untaintedDrawable(image) {
    const src = previewSource(image);
    if (!src) return null;
    if (src.startsWith('blob:') || src.startsWith('data:')) return image;
    if (new URL(src, location.href).origin === location.origin) return image;
    for (let attempt = 0; ; attempt++) {
      try {
        const response = await fetch(src, {credentials: 'omit', mode: 'cors'});
        if (!response.ok) return null;
        const declared = Number(response.headers.get('content-length'));
        if (Number.isFinite(declared) && declared > MAX_PREVIEW_BYTES) return null;
        const blob = await response.blob();
        if (blob.size > MAX_PREVIEW_BYTES) return null;
        return await createImageBitmap(blob);
      } catch (error) {
        if (attempt >= PREVIEW_FETCH_RETRIES) return null;
        await sleep(PREVIEW_FETCH_RETRY_MS);
      }
    }
  }

  async function verifyCandidate(image, before) {
    const src = previewSource(image);
    const drawable = await untaintedDrawable(image);
    if (drawable && matchesPicture(pictureSamples(drawable), before.expected)) {
      before.verified.add(src);
      return image;
    }
    return null;
  }

  function readyPreview(dialog, before) {
    // A verified source can belong to an image that was later hidden or
    // superseded; only a currently visible image may gate Save.
    const images = [...dialog.querySelectorAll('img')].filter(image =>
      before.verified.has(previewSource(image)) && visible(image));
    if (images[0]) return images[0];
    const canvases = [...dialog.querySelectorAll('canvas')].filter(canvas => {
      const box = canvas.getBoundingClientRect();
      if (!visible(canvas) || box.width < 80 || box.height < 80) return false;
      const samples = pictureSamples(canvas);
      const picture = canvasPicture(canvas, samples);
      return picture !== null && picture !== before.canvases.get(canvas) && matchesPicture(samples, before.expected);
    });
    return canvases[0] || null;
  }

  async function verifyPreview(dialog, before) {
    for (const image of candidateImages(dialog, before)) {
      const src = previewSource(image);
      if (!before.checked.has(src)) before.checked.set(src, verifyCandidate(image, before));
      if (await before.checked.get(src)) return image;
    }
    return null;
  }

  function canvasPicture(canvas, samples = pictureSamples(canvas)) {
    const opaque = samples?.some((value, index) => index % 4 === 3 && value > 0);
    return opaque ? `${canvas.width}x${canvas.height}:${samples.join(',')}` : null;
  }

  function dialogBusy(dialog) {
    return [...dialog.querySelectorAll('[aria-busy="true"], [role="progressbar"]')].some(visible);
  }

  function dialogError(dialog) {
    return [...dialog.querySelectorAll('[role="alert"]')].some(visible);
  }

  async function waitForPreview(before) {
    const deadline = Date.now() + DIALOG_WAIT_MS;
    let readySince = 0;
    let lastPreview = null;
    while (Date.now() < deadline) {
      const dialog = profileDialog();
      if (dialog && dialogError(dialog)) throw new Error('Facebook reported an upload problem; no automatic Save attempted');
      const preview = dialog && !dialogBusy(dialog) ? (readyPreview(dialog, before) || await verifyPreview(dialog, before)) : null;
      if (!preview || preview !== lastPreview) readySince = 0;
      if (preview && !readySince) readySince = Date.now();
      lastPreview = preview;
      if (readySince && Date.now() - readySince >= PREVIEW_SETTLE_MS) return;
      await sleep(200);
    }
    throw new Error('Could not verify the selected picture in the preview; no automatic Save attempted. Check the preview and Save manually if correct.');
  }

  async function uploadIntoDialog(bytes, expected) {
    const site = activeSite || SITES.facebook;
    const avatar = await waitUntil(ownAvatar);
    if (!avatar) throw new Error(`Could not uniquely identify your own profile picture. ${site.errorHint}`);
    press(avatar.closest('button, [role="button"]') || avatar);

    const chooser = await waitUntil(() => uniqueClick(document, site.chooseAction));
    if (!chooser) throw new Error('Choose profile picture action was not uniquely identified');
    press(chooser);

    if (!await waitUntil(profileDialog)) throw new Error('Profile-picture dialog did not open; no image was uploaded');
    const progress = {pressed: false, requested: null};
    const input = await findFileInput(progress);
    if (!input) throw new Error(`No file input inside the profile-picture dialog; stopped safely (${dialogReport(progress)})`);
    const dialog = profileDialog();
    if (!dialog || !input.isConnected) throw new Error('The profile-picture dialog changed before upload; try again');
    const before = previewSnapshot(dialog, expected);
    const file = new File([bytes], 'profile-photo.jpg', {type: 'image/jpeg'});
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
    // Do not re-check input.files here: Facebook reads the file during the
    // change dispatch and clears the input immediately, which made a fully
    // successful upload report "did not receive the selected image file" on
    // the live site. Acceptance is proven by waitForPreview below, which
    // refuses any Save until the dialog renders the selected photo.
    await waitForPreview(before);
    return before;
  }

  async function saveIfRequested(before) {
    const site = activeSite || SITES.facebook;
    // Intermediate steps vary by UI version. All clicks stay dialog scoped.
    const inDialog = (pattern) => () => {
      const dialog = profileDialog();
      return dialog && !dialogBusy(dialog) && !dialogError(dialog) && readyPreview(dialog, before)
        ? uniqueClick(dialog, pattern) : null;
    };
    const findSave = inDialog(site.saveAction);
    const findNext = inDialog(site.nextAction);
    let save = findSave();
    for (let attempt = 0; !save && attempt < 2; attempt++) {
      const next = findNext();
      if (!next) break;
      press(next);
      save = await waitUntil(findSave);
    }
    if (!save) save = await waitUntil(findSave);
    if (!save) throw new Error('Save button did not become available; no automatic Save attempted');
    let cancelled = false;
    const onCancel = event => {
      if (event.type === 'keydown' && event.key === 'Escape' &&
        [...document.querySelectorAll('[role="dialog"], dialog')].some(visible)) cancelled = true;
      const control = event.target instanceof Element ? event.target.closest(BUTTONS) : null;
      const dialog = control?.closest('[role="dialog"], dialog');
      if (event.type === 'click' && control && visible(dialog) && /^(?:cancel|close|discard(?: changes)?)$/i.test(label(control))) cancelled = true;
    };
    window.addEventListener('click', onCancel, true);
    window.addEventListener('keydown', onCancel, true);
    try {
      // Re-check after installing listeners; never click a detached or superseded Save control.
      if (findSave() !== save) throw new Error('The picture preview changed before Save; try again');
      press(save);
      const deadline = Date.now() + SAVE_WAIT_MS;
      let closedSince = 0;
      while (Date.now() < deadline) {
        if (cancelled) {
          // Save was clicked and something then cancelled or replaced the dialog. Facebook may
          // or may not have kept the change; report it as unconfirmed so the caller treats the
          // rotation as consumed instead of retrying the same photo immediately.
          return {ok: true, saved: true, confirmed: false, stage: 'save-click-unconfirmed'};
        }
        const dialog = profileDialog();
        if (dialog && dialogError(dialog)) {
          return {ok: true, saved: true, confirmed: false, stage: 'save-click-unconfirmed'};
        }
        // An unlabeled replacement shell is still a dialog. A brief removal during rendering is not acknowledgement.
        const anyDialog = [...document.querySelectorAll('[role="dialog"], dialog')].some(visible);
        if (anyDialog) closedSince = 0;
        else if (!closedSince) closedSince = Date.now();
        else if (Date.now() - closedSince >= SAVE_SETTLE_MS) {
          return {ok: true, saved: true, confirmed: true, stage: 'save-click-acknowledged'};
        }
        await sleep(200);
      }
      // Save was clicked but the dialog never settled; the outcome is unknown. Same treatment as
      // a mid-close cancel: the rotation counts as consumed, because retrying would risk an
      // immediate second publication of the same photo.
      return {ok: true, saved: true, confirmed: false, stage: 'save-click-unconfirmed'};
    } finally {
      window.removeEventListener('click', onCancel, true);
      window.removeEventListener('keydown', onCancel, true);
    }
  }

  async function run(message) {
    validatePage();
    if (message.mime !== 'image/jpeg' || message.fileName !== 'profile-photo.jpg') {
      throw new Error('Invalid image metadata');
    }
    const bytes = decodeBytes(message.data);
    const expected = await expectedPicture(bytes);
    const before = await uploadIntoDialog(bytes, expected);
    if (message.publish !== true) {
      showNotice('fb-pfp: Picture prepared. Check the preview, then click Save yourself.');
      return {ok: true, saved: false, stage: 'review'};
    }
    const result = await saveIfRequested(before);
    // Only a settled, closed dialog counts as acknowledgement. A cancel, an
    // error or a dialog that never settled is reported as unconfirmed.
    if (result.confirmed === true) {
      showNotice('fb-pfp: Save acknowledged by the Facebook dialog. Verify your profile picture.');
    } else {
      showNotice('fb-pfp: Save was clicked, but Facebook did not confirm it. Check your profile picture.', true);
    }
    return result;
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message?.type !== 'PREPARE_PHOTO') return false;
    // Only this extension's own pages and worker may drive the dialog.
    if (sender?.id !== chrome.runtime.id) {
      sendResponse({ok: false, error: 'Ignored message from an unknown sender'});
      return false;
    }
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
