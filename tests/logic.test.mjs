import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_SETTINGS, sanitizeSettings, isValidTime,
  selectPhoto, recordSaved, nextScheduledTime, isAllowedFacebookPage, safeDisplayError,
  shouldCloseScheduledTab,
  SITE_ROUTES, resolveSiteRoute, isAllowedSitePage
} from '../src/logic.mjs';
import { imageFormat, safePhotoName } from '../src/images.mjs';

const photos = ['a','b','c'].map(id => ({id}));

test('default mode is cycle, schedule disabled', () => {
  assert.equal(DEFAULT_SETTINGS.scheduleEnabled, false);
  assert.equal(sanitizeSettings({mode:'evil'}).mode, 'cycle');
});
test('invalid settings fail safe', () => {
  const r = sanitizeSettings({scheduleEnabled:'true', scheduleTime:'25:00', usedIds:['a',42,{},'a']});
  assert.equal(r.scheduleEnabled,false);
  assert.equal(r.scheduleTime,'09:15');
  assert.deepEqual(r.usedIds,['a']);
});
test('time parsing accepts 00:00 and 23:59 only', () => {
  assert.equal(isValidTime('00:00'),true);
  assert.equal(isValidTime('23:59'),true);
  for (const x of ['7:00','24:00','13:60','09:00;eval','']) assert.equal(isValidTime(x),false);
});
test('cycle no repeats, resets after all saved', () => {
  let s = sanitizeSettings();
  const picked = [];
  for (let i=0;i<3;i++) {
    const p = selectPhoto(photos,s,()=>0);
    picked.push(p.id);
    s = recordSaved(photos,s,p.id);
  }
  assert.deepEqual(picked,['a','b','c']);
  // The new round starts with the last saved photo excluded.
  assert.deepEqual(s.usedIds,['c']);
});
test('a new round never opens by repeating the photo just saved', () => {
  let s = {...sanitizeSettings(), usedIds:['a','b']};
  s = recordSaved(photos,s,'c');
  for (const r of [0, 0.34, 0.5, 0.67, 0.999]) {
    assert.notEqual(selectPhoto(photos,s,()=>r).id,'c');
  }
});
test('a single photo can only repeat itself and still resets', () => {
  const one=[photos[0]];
  const s = recordSaved(one,sanitizeSettings(),'a');
  assert.deepEqual(s.usedIds,[]);
  assert.equal(selectPhoto(one,s,()=>0).id,'a');
});
test('random mode can repeat and honors RNG', () => {
  assert.equal(selectPhoto(photos,{mode:'random',usedIds:['a']},()=>0).id,'a');
  assert.equal(selectPhoto(photos,{mode:'random',usedIds:[]},()=>0.999).id,'c');
});
test('removed photos do not poison rotation', () => {
  const p=[photos[0],photos[2]];
  assert.equal(selectPhoto(p,{mode:'cycle',usedIds:['a','b']},()=>0).id,'c');
});
test('invalid RNG rejected', () => {
  assert.throws(()=>selectPhoto(photos,{mode:'cycle'},()=>1),RangeError);
});
test('empty library is harmless',()=>assert.equal(selectPhoto([],DEFAULT_SETTINGS),null));
test('local alarm picks next day if current time passed', () => {
  const now=new Date(2026,9,11,10,0);
  const when=new Date(nextScheduledTime(now,'09:15'));
  assert.equal(when.getDate(),12);
  assert.equal(when.getHours(),9);
  assert.equal(when.getMinutes(),15);
});
test('schedule is same day before time', () => {
  const when=new Date(nextScheduledTime(new Date(2026,9,11,8,0),'09:15'));
  assert.equal(when.getDate(),11);
});
test('Facebook origin is exact HTTPS only',()=>{
  assert.equal(isAllowedFacebookPage('https://www.facebook.com/me'),true);
  for(const x of ['http://www.facebook.com/me','https://www.facebook.com.evil.org/',
    'https://m.facebook.com/me','https://evil.org/?to=www.facebook.com','not a url']) {
    assert.equal(isAllowedFacebookPage(x),false);
  }
});
test('errors redact embedded URLs',()=>{
  assert.equal(safeDisplayError(new Error('see https://x.example/token=secret')), 'see [URL]');
});
test('magic bytes validation rejects fake JPEG names',()=>{
  assert.equal(imageFormat(new Uint8Array([0xff,0xd8,0xff,0x01])),'jpeg');
  assert.equal(imageFormat(new Uint8Array([137,80,78,71,13,10,26,10])),'png');
  assert.equal(imageFormat(new TextEncoder().encode('RIFF0000WEBP')),'webp');
  assert.equal(imageFormat(new TextEncoder().encode('not an image')),null);
});
test('file names stripped of unsafe characters',()=>{
  assert.equal(safePhotoName('../../my photo.jpg'),'_.._my_photo.jpg');
  assert.equal(safePhotoName('😀'), '_');
});

test('a review-only selection does not consume a photo',()=>{
  const original=sanitizeSettings();
  assert.equal(selectPhoto(photos,original,()=>0).id,'a');
  assert.equal(selectPhoto(photos,original,()=>0).id,'a');
  assert.deepEqual(original.usedIds,[]);
});

test('userinfo and lookalike hosts are not Facebook', () => {
  assert.equal(isAllowedFacebookPage('https://www.facebook.com@evil.example/'), false);
  assert.equal(isAllowedFacebookPage('https://www.facebook.com.:8443/'), false);
  assert.equal(isAllowedFacebookPage('https://www.facebook.com.evil.example/'), false);
  assert.equal(isAllowedFacebookPage('https://user:pass@www.facebook.com@evil.example/'), false);
  assert.equal(isAllowedFacebookPage('javascript:alert(1)'), false);
  assert.equal(isAllowedFacebookPage(''), false);
  assert.equal(isAllowedFacebookPage(null), false);
});

test('settings sanitize survives hostile JSON shapes', () => {
  const hostile = JSON.parse('{"__proto__": {"polluted": 1}, "mode": "random", "usedIds": {"$where": 1}}');
  const r = sanitizeSettings(hostile);
  assert.equal(r.mode, 'random');
  assert.deepEqual(r.usedIds, []);
  assert.equal(Object.prototype.polluted, undefined);
  // Bulk garbage stays bounded.
  const bulk = sanitizeSettings({usedIds: Array.from({length: 10000}, (_, i) => `id-${i}`)});
  assert.equal(bulk.usedIds.length, 500);
  assert.equal(bulk.usedIds.at(-1), 'id-9999');
  // Non-string results and oversized logs are neutralized.
  assert.equal(sanitizeSettings({lastResult: {toString: 'no'}}).lastResult, 'No runs yet.');
  assert.equal(sanitizeSettings({lastResult: 'x'.repeat(10000)}).lastResult.length, 300);
});

test('selection rejects NaN RNG and duplicate ids safely', () => {
  assert.throws(() => selectPhoto(photos, {mode: 'cycle'}, () => NaN), RangeError);
  const dupes = [{id: 'a'}, {id: 'a'}, {id: 'b'}];
  const pick = selectPhoto(dupes, {mode: 'cycle', usedIds: []}, () => 0.9);
  assert.ok(['a', 'b'].includes(pick.id));
});

test('recordSaved refuses unknown ids', () => {
  assert.throws(() => recordSaved(photos, sanitizeSettings(), 'zzz'), /removed/);
});

test('error display redacts every URL and caps length', () => {
  const messy = safeDisplayError(new Error('a https://x.example/1 and http://y.example/2 ' + 'z'.repeat(500)));
  assert.equal(messy.includes('https://'), false);
  assert.equal(messy.includes('http://'), false);
  assert.equal(messy.length, 200);
  assert.equal(safeDisplayError('plain string failure'), 'plain string failure');
});

test('scheduled tab closes only when unstaged and unfocused', () => {
  assert.equal(shouldCloseScheduledTab({active: false, staged: false}), true);
  assert.equal(shouldCloseScheduledTab({active: true, staged: false}), false);
  assert.equal(shouldCloseScheduledTab({active: false, staged: true}), false);
  assert.equal(shouldCloseScheduledTab({active: true, staged: true}), false);
  assert.equal(shouldCloseScheduledTab({}), true);
});

test('review tab id sanitizes to integer or null', () => {
  assert.equal(sanitizeSettings({reviewTabId: 42}).reviewTabId, 42);
  assert.equal(sanitizeSettings({reviewTabId: 0}).reviewTabId, 0);
  assert.equal(sanitizeSettings().reviewTabId, null);
  for (const bad of [-1, 1.5, '7', '7;eval', {}, [7]]) {
    assert.equal(sanitizeSettings({reviewTabId: bad}).reviewTabId, null);
  }
});

test('worker site routes resolve enabled sites only', () => {
  assert.equal(resolveSiteRoute('facebook'), SITE_ROUTES.facebook);
  assert.equal(resolveSiteRoute('facebook').profileUrl, 'https://www.facebook.com/me');
  // Disabled adapters and unknown ids never resolve, whatever the storage says.
  for (const bad of ['linkedin', 'x', '', 'FACEBOOK', 'facebook;eval', {}, null, undefined]) {
    assert.equal(resolveSiteRoute(bad), null);
  }
});

test('stored siteId fails closed to the default site', () => {
  assert.equal(sanitizeSettings().siteId, 'facebook');
  assert.equal(sanitizeSettings({siteId: 'facebook'}).siteId, 'facebook');
  for (const bad of ['linkedin', 'x', 'evil', {toString: () => 'facebook'}, 42]) {
    assert.equal(sanitizeSettings({siteId: bad}).siteId, 'facebook');
  }
});

test('site page allowance is exact HTTPS on a route host', () => {
  const route = SITE_ROUTES.facebook;
  assert.equal(isAllowedSitePage(route, 'https://www.facebook.com/me'), true);
  assert.equal(isAllowedSitePage(route, 'https://www.facebook.com/anything'), true);
  for (const bad of ['http://www.facebook.com/me', 'https://facebook.com/me',
                     'https://www.facebook.com.evil.com/me', 'https://evil.com',
                     'not a url', '', null]) {
    assert.equal(isAllowedSitePage(route, bad), false);
    assert.equal(isAllowedFacebookPage(bad), false);
  }
  assert.equal(isAllowedSitePage(null, 'https://www.facebook.com/me'), false);
  assert.equal(isAllowedFacebookPage('https://www.facebook.com/me'), true);
});
