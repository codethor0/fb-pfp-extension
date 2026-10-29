import {listPhotos, savePhoto, deletePhoto} from './library.mjs';
import {normalizePhoto, MAX_LIBRARY_COUNT, safePhotoName} from './images.mjs';
import {resolveSiteRoute} from './logic.mjs';

const siteLabel = settings => resolveSiteRoute(settings?.siteId)?.label || 'Facebook';

const $ = id => document.getElementById(id);
const status = (message, error = false) => {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
};
let photos = [];
let objectUrls = [];
let busy = false;

function updateActions() {
  $('prepare').disabled = busy || photos.length === 0;
  $('publish').disabled = busy || photos.length === 0 || !$('confirm-publish').checked;
}

async function renderPhotos() {
  for (const url of objectUrls) URL.revokeObjectURL(url);
  objectUrls = [];
  photos = await listPhotos();
  $('count').textContent = `${photos.length} / ${MAX_LIBRARY_COUNT}`;
  const list = $('photos');
  list.replaceChildren();
  for (const photo of photos) {
    const row = document.createElement('li');
    row.className = 'photo';
    const thumb = document.createElement('img');
    const url = URL.createObjectURL(photo.blob);
    objectUrls.push(url);
    thumb.src = url;
    thumb.alt = '';
    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = safePhotoName(photo.originalName);
    name.title = name.textContent;
    const button = document.createElement('button');
    button.textContent = 'Remove';
    button.type = 'button';
    button.setAttribute('aria-label', `Remove ${name.textContent}`);
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {await deletePhoto(photo.id); await renderPhotos(); status('Removed picture from this browser.');}
      catch (error) {status(error.message, true); button.disabled = false;}
    });
    row.append(thumb, name, button);
    list.appendChild(row);
  }
  updateActions();
}

async function importFiles(files) {
  let added = 0;
  const errors = [];
  for (const file of files) {
    if (photos.length + added >= MAX_LIBRARY_COUNT) {errors.push('Library limited to 20 images.'); break;}
    try {
      const normalized = await normalizePhoto(file);
      const id = crypto.randomUUID();
      await savePhoto({id, originalName: normalized.originalName, blob: normalized.blob,
        width: normalized.width, height: normalized.height, addedAt: Date.now() + added});
      added++;
    } catch (error) {errors.push(`${safePhotoName(file.name)}: ${error.message}`);}
  }
  await renderPhotos();
  status(`${added} picture(s) imported.${errors.length ? ' ' + errors.join(' ') : ''}`, errors.length > 0);
}

async function request(message) {
  const reply = await chrome.runtime.sendMessage(message);
  if (!reply?.ok) throw new Error(reply?.error || 'Extension service worker unavailable');
  return reply;
}

async function start() {
  try {
    const [reply] = await Promise.all([request({type: 'GET_SETTINGS'}), renderPhotos()]);
    $('mode').value = reply.settings.mode;
    $('schedule').checked = reply.settings.scheduleEnabled;
    $('time').value = reply.settings.scheduleTime;
    status(reply.settings.lastResult);
  } catch (error) {status(error.message, true);}
}

async function run(type) {
  if (busy) return;
  if (type === 'PUBLISH_NEXT' && !$('confirm-publish').checked) return;
  busy = true;
  updateActions();
  try {
    // Honor the current mode without silently modifying the schedule controls.
    const current = await request({type: 'GET_SETTINGS'});
    const label = siteLabel(current.settings);
    status(type === 'PUBLISH_NEXT' ? `Opening ${label} and changing your profile picture...` :
      `Opening ${label} and preparing the picture dialog...`);
    if (current.settings.mode !== $('mode').value) {
      await request({type: 'SAVE_SETTINGS', settings: {...current.settings, mode: $('mode').value}});
    }
    const reply = await request({type});
    if (reply.saved) {
      const unconfirmed = reply.confirmed === false;
      status(reply.warning || (unconfirmed
        ? `${reply.name}: Save clicked, but ${label} did not confirm it. Verify your profile picture.`
        : `${reply.name}: Save acknowledged. Verify the result on ${label}.`), !!reply.warning || unconfirmed);
    }
    else status(`${reply.name}: Ready for review in the ${label} tab. Save manually if correct.`);
  } catch (error) {status(error.message, true);}
  finally {
    busy = false;
    $('confirm-publish').checked = false;
    updateActions();
  }
}

$('picker').addEventListener('change', async event => {
  try {
    const files = [...event.target.files];
    if (files.length) {status('Processing pictures locally...'); await importFiles(files);}
  } catch (error) {status(error.message, true);}
  finally {$('picker').value = '';}
});
$('confirm-publish').addEventListener('change', updateActions);
$('prepare').addEventListener('click', () => {void run('PREPARE_NEXT');});
$('publish').addEventListener('click', () => {void run('PUBLISH_NEXT');});
$('save').addEventListener('click', async () => {
  $('save').disabled = true;
  try {
    const reply = await request({type: 'SAVE_SETTINGS', settings: {
      mode: $('mode').value,
      scheduleEnabled: $('schedule').checked,
      scheduleTime: $('time').value
    }});
    // Reflect the stored values: an empty or invalid time field is corrected
    // to the default server-side, and the field must not disagree with it.
    $('mode').value = reply.settings.mode;
    $('schedule').checked = reply.settings.scheduleEnabled;
    $('time').value = reply.settings.scheduleTime;
    status($('schedule').checked ? 'Daily review saved. Browser must be open at that time.' :
      'Preferences saved. Daily review is off.');
  } catch (error) {status(error.message, true);}
  finally {$('save').disabled = false;}
});
window.addEventListener('unload', () => {for (const url of objectUrls) URL.revokeObjectURL(url);});
void start();
