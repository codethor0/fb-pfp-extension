import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_SETTINGS, sanitizeSettings, isValidTime,
  selectPhoto, recordSaved, nextScheduledTime, isAllowedFacebookPage, safeDisplayError
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
  assert.deepEqual(s.usedIds,[]);
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
