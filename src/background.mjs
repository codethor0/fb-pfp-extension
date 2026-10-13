import { listPhotos, getPhoto } from './library.mjs';
import {
  DEFAULT_SETTINGS, sanitizeSettings, selectPhoto, recordSaved,
  nextScheduledTime, isAllowedFacebookPage, safeDisplayError
} from './logic.mjs';
import { encodePhoto } from './transfer.mjs';

const STORAGE_KEY = 'settings';
const ALARM_NAME = 'fb-pfp-daily-review';
const FACEBOOK_PROFILE = 'https://www.facebook.com/me';
let runInFlight = null;

async function readSettings() {
  const data = await chrome.storage.local.get(STORAGE_KEY);
  return sanitizeSettings(data[STORAGE_KEY] || DEFAULT_SETTINGS);
}

async function writeSettings(settings) {
  await chrome.storage.local.set({[STORAGE_KEY]: sanitizeSettings(settings)});
}

// Serialize settings read-modify-write so a concurrent schedule change can
// never be clobbered by a run that read the settings first (audit finding F6).
let settingsQueue = Promise.resolve();
function updateSettings(mutator) {
  const next = settingsQueue.then(async () => mutator(await readSettings()));
  settingsQueue = next.then(() => {}, () => {});
  return next;
}

async function writeResult(message) {
  await updateSettings(async settings => {
    await writeSettings({...settings, lastResult: `${new Date().toLocaleString()}: ${message}`});
  });
}

async function syncAlarm() {
  const settings = await readSettings();
  await chrome.alarms.clear(ALARM_NAME);
  if (settings.scheduleEnabled) {
    await chrome.alarms.create(ALARM_NAME, {when: nextScheduledTime(new Date(), settings.scheduleTime)});
  }
}

async function ensureAlarm() {
  const settings = await readSettings();
  const alarm = await chrome.alarms.get(ALARM_NAME);
  if ((settings.scheduleEnabled && !alarm) || (!settings.scheduleEnabled && alarm)) await syncAlarm();
}

async function restrictStorage() {
  // The Facebook content script does not need library or settings access.
  await chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'});
}

async function sendToNewTab(tabId, payload) {
  for (let attempt = 0; attempt < 80; attempt++) {
    const tab = await chrome.tabs.get(tabId);
    if (!isAllowedFacebookPage(tab.url || '')) {
      if (tab.status === 'complete' && tab.url && tab.url !== 'about:blank') {
        throw new Error('Facebook redirected to an unsupported domain');
      }
    } else if (tab.status === 'complete') {
      try {
        return await chrome.tabs.sendMessage(tabId, payload, {frameId: 0});
      } catch (error) {
        // A content script may install a moment after navigation finishes.
        if (!/Receiving end does not exist|Could not establish connection/i.test(String(error))) throw error;
      }
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('Timed out waiting for Facebook or the content script');
}

async function runPhoto({source, publish}) {
  if (runInFlight) return {ok: false, error: 'A profile photo operation is already running'};
  // The service worker owns the operation; closing the popup does not stop it.
  const operation = (async () => {
    const settings = await readSettings();
    if (source === 'alarm' && (!settings.scheduleEnabled || publish)) {
      throw new Error('Scheduled publishing is disabled');
    }
    const photos = await listPhotos();
    if (!photos.length) throw new Error('Add photos in the extension before running it');
    const selected = selectPhoto(photos, settings);
    if (!selected) throw new Error('No usable photos available');
    const photo = await getPhoto(selected.id);
    if (!photo?.blob) throw new Error('The selected photo was removed. Try again.');
    const base64 = await encodePhoto(photo.blob);
    // Alarm-initiated runs open the tab in the background so a scheduled review
    // never steals focus; user-initiated runs open in the foreground.
    const tab = await chrome.tabs.create({url: FACEBOOK_PROFILE, active: source !== 'alarm'});
    if (!Number.isInteger(tab.id)) throw new Error('Could not open your Facebook profile');
    const result = await sendToNewTab(tab.id, {
      type: 'PREPARE_PHOTO',
      publish,
      mime: 'image/jpeg',
      fileName: 'profile-photo.jpg',
      data: base64
    });
    if (!result?.ok) throw new Error(result?.error || 'Facebook did not accept the image');
    // A completed review does not use up a picture. A Save click does, even when
    // Facebook never confirmed the result: retrying the same photo immediately
    // would risk a second publication (audit finding F2).
    if (publish) {
      if (result.saved !== true) throw new Error('Save was not clicked. Rotation state was not changed.');
      const confirmed = result.confirmed !== false;
      const remaining = await listPhotos();
      const outcome = await updateSettings(async current => {
        const updated = remaining.some(item => item.id === selected.id)
          ? recordSaved(remaining, current, selected.id) : current;
        const message = confirmed
          ? `${new Date().toLocaleString()}: Save acknowledged for ${selected.originalName}. Verify your Facebook profile picture.`
          : `${new Date().toLocaleString()}: Save clicked for ${selected.originalName}, but Facebook did not confirm the result. The photo was counted as used so it will not repeat immediately. Verify your Facebook profile picture.`;
        await writeSettings({...updated, lastResult: message});
        return updated;
      }).then(() => true, () => false);
      if (!outcome) {
        // Never report Save as failed solely because rotation state failed to persist.
        return {ok: true, saved: true, confirmed, name: selected.originalName, tabId: tab.id,
          warning: confirmed
            ? 'Save was acknowledged, but the rotation state could not be updated. Verify Facebook.'
            : 'Save was clicked but not confirmed, and the rotation state could not be updated. Verify Facebook.'};
      }
      return {ok: true, saved: true, confirmed, name: selected.originalName, tabId: tab.id};
    }
    await writeResult(`${selected.originalName} prepared for review. Click Save on Facebook if it is correct.`).catch(() => {});
    return {ok: true, saved: false, name: selected.originalName, tabId: tab.id};
  })();
  runInFlight = operation;
  try { return await operation; }
  catch (error) {
    const message = safeDisplayError(error);
    await writeResult(`Operation failed: ${message}`).catch(() => {});
    return {ok: false, error: message};
  } finally { runInFlight = null; }
}

async function handleMessage(message, sender) {
  if (sender?.id !== chrome.runtime.id ||
      sender?.url !== chrome.runtime.getURL('src/popup.html')) {
    return {ok: false, error: 'Untrusted message origin'};
  }
  if (message?.type === 'GET_SETTINGS') return {ok: true, settings: await readSettings()};
  if (message?.type === 'SAVE_SETTINGS') {
    const requested = message.settings || {};
    const updated = await updateSettings(async previous => {
      const next = sanitizeSettings({
        ...previous,
        mode: requested.mode,
        scheduleEnabled: requested.scheduleEnabled,
        scheduleTime: requested.scheduleTime
      });
      await writeSettings(next);
      return next;
    });
    await syncAlarm();
    return {ok: true, settings: updated};
  }
  if (message?.type === 'PREPARE_NEXT') return runPhoto({source: 'user', publish: false});
  if (message?.type === 'PUBLISH_NEXT') return runPhoto({source: 'user', publish: true});
  return {ok: false, error: 'Unknown request'};
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender)
    .then(sendResponse)
    .catch(error => sendResponse({ok: false, error: safeDisplayError(error)}));
  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  void (async () => {await restrictStorage(); await ensureAlarm();})()
    .catch(error => console.error('Initialization:', safeDisplayError(error)));
});
chrome.runtime.onStartup.addListener(() => {
  void (async () => {await restrictStorage(); await ensureAlarm();})()
    .catch(error => console.error('Startup:', safeDisplayError(error)));
});
chrome.alarms.onAlarm.addListener(alarm => {
  if (alarm.name !== ALARM_NAME) return;
  void (async () => {
    await syncAlarm();
    await runPhoto({source: 'alarm', publish: false});
  })().catch(error => console.error('Scheduled review:', safeDisplayError(error)));
});
