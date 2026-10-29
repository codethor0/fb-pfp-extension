// Pure functions, shared by the extension worker and offline tests.
export const DEFAULT_SETTINGS = Object.freeze({
  mode: 'cycle',
  scheduleEnabled: false,
  scheduleTime: '09:15',
  usedIds: [],
  lastResult: 'No runs yet.',
  reviewTabId: null,
  siteId: 'facebook',
});

export function isValidTime(time) {
  return typeof time === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(time);
}

export function sanitizeSettings(input = {}) {
  const mode = input.mode === 'random' ? 'random' : 'cycle';
  const scheduleTime = isValidTime(input.scheduleTime) ? input.scheduleTime : DEFAULT_SETTINGS.scheduleTime;
  const usedIds = Array.isArray(input.usedIds)
    ? [...new Set(input.usedIds.filter(id => typeof id === 'string' && /^[a-zA-Z0-9-]{1,80}$/.test(id)))].slice(-500)
    : [];
  const reviewTabId = Number.isInteger(input.reviewTabId) && input.reviewTabId >= 0 ? input.reviewTabId : null;
  // Fail closed to the default site: a stored or injected siteId that does
  // not resolve to an enabled route can never reroute a run.
  const siteId = typeof input.siteId === 'string' && resolveSiteRoute(input.siteId)
    ? input.siteId : DEFAULT_SETTINGS.siteId;
  return {
    mode,
    scheduleEnabled: input.scheduleEnabled === true,
    scheduleTime,
    usedIds,
    reviewTabId,
    siteId,
    lastResult: typeof input.lastResult === 'string' ? input.lastResult.slice(0, 300) : DEFAULT_SETTINGS.lastResult
  };
}

export function selectPhoto(photos, settings, random = Math.random) {
  if (!Array.isArray(photos) || photos.length === 0) return null;
  const ids = new Set(photos.map(photo => photo.id));
  const previouslySaved = (settings.usedIds || []).filter(id => ids.has(id));
  const fresh = photos.filter(photo => !previouslySaved.includes(photo.id));
  const candidates = settings.mode === 'cycle' && fresh.length ? fresh : photos;
  const r = random();
  if (!Number.isFinite(r) || r < 0 || r >= 1) throw new RangeError('Random source must return a number in [0, 1)');
  return candidates[Math.floor(r * candidates.length)];
}

export function recordSaved(photos, settings, id) {
  const ids = photos.map(photo => photo.id);
  if (!ids.includes(id)) throw new Error('Photo was removed before the save completed');
  const previous = (settings.usedIds || []).filter(x => ids.includes(x));
  const used = [...new Set([...previous, id])];
  // A finished round starts a new one. Keep the photo just saved marked as
  // used so the new round cannot open by repeating it. With a single photo
  // there is nothing else to choose, so the round simply resets.
  if (used.length >= ids.length) return { ...settings, usedIds: ids.length > 1 ? [id] : [] };
  return { ...settings, usedIds: used };
}

export function nextScheduledTime(now, time) {
  if (!(now instanceof Date) || Number.isNaN(now.getTime()) || !isValidTime(time)) {
    throw new TypeError('Invalid local date or HH:MM schedule');
  }
  const [hour, minute] = time.split(':').map(Number);
  const next = new Date(now.getFullYear(), now.getMonth(), now.getDate(), hour, minute, 0, 0);
  if (next.getTime() <= now.getTime()) next.setDate(next.getDate() + 1);
  return next.getTime();
}

// Worker-layer site routes: where each enabled site opens, which hostnames
// qualify as its pages, and how it is named in user-facing strings. Only
// sites the shipped build actually enables appear here; disabled adapters
// stay content-side research entries until they have a verified, permitted
// flow. Never add a route without host permissions granted for it.
export const SITE_ROUTES = Object.freeze({
  facebook: Object.freeze({
    id: 'facebook',
    label: 'Facebook',
    profileUrl: 'https://www.facebook.com/me',
    hosts: Object.freeze(['www.facebook.com']),
    enabled: true,
  }),
});

export function resolveSiteRoute(siteId) {
  if (typeof siteId !== 'string') return null;
  const route = SITE_ROUTES[siteId];
  return route && route.enabled === true ? route : null;
}

export function isAllowedSitePage(route, url) {
  if (!route) return false;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && route.hosts.includes(parsed.hostname);
  } catch { return false; }
}

export function isAllowedFacebookPage(url) {
  return isAllowedSitePage(SITE_ROUTES.facebook, url);
}

// A scheduled run closes its tab only when nothing was staged into Facebook's
// dialog and the user has not focused the tab since. Anything else keeps the
// tab so the user can inspect or retry it.
export function shouldCloseScheduledTab({active, staged}) {
  return active !== true && staged !== true;
}

export function safeDisplayError(error) {
  const message = error instanceof Error ? error.message : String(error);
  return message.replace(/https?:\/\/\S+/g, '[URL]').slice(0, 200);
}
