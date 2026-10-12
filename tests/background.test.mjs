import test from 'node:test';
import assert from 'node:assert/strict';

const storage = {};
const alarms = new Map();
const callbacks = {};
const fakeId = 'abcdefghijklmnopqrstuvwxyzabcdef';

globalThis.chrome = {
  runtime: {
    id: fakeId,
    getURL: path => `chrome-extension://${fakeId}/${path}`,
    onMessage: {addListener(fn) {callbacks.message=fn;}},
    onInstalled: {addListener(fn) {callbacks.installed=fn;}},
    onStartup: {addListener(fn) {callbacks.startup=fn;}}
  },
  storage: {
    local: {
      async get(key) {return {[key]: storage[key]};},
      async set(object) {Object.assign(storage, object);},
      async setAccessLevel() {}
    }
  },
  alarms: {
    async clear(key) {return alarms.delete(key);},
    async create(key, config) {alarms.set(key, config);},
    async get(key) {return alarms.get(key);},
    onAlarm: {addListener(fn) {callbacks.alarm=fn;}}
  }
};

await import('../src/background.mjs');
const popupSender = {id: fakeId, url: chrome.runtime.getURL('src/popup.html')};

function send(message, sender=popupSender) {
  return new Promise(resolve => {
    assert.equal(callbacks.message(message, sender, resolve), true);
  });
}

test('background registers handlers immediately',()=>{
  assert.equal(typeof callbacks.message,'function');
  assert.equal(typeof callbacks.alarm,'function');
  assert.equal(typeof callbacks.installed,'function');
  assert.equal(typeof callbacks.startup,'function');
});
test('rejects messages from third-party origins or spoofed extension ID',async()=>{
  for(const sender of [
    {id:fakeId,url:'https://www.facebook.com/me'},
    {id:'other',url:popupSender.url},
    {id:fakeId,url:chrome.runtime.getURL('src/other.html')}
  ]) {
    assert.deepEqual(await send({type:'GET_SETTINGS'},sender),{ok:false,error:'Untrusted message origin'});
  }
});
test('default settings disable the scheduled alarm', async()=>{
  const result=await send({type:'GET_SETTINGS'});
  assert.equal(result.ok,true);
  assert.equal(result.settings.scheduleEnabled,false);
});
test('save-settings only accepts allowlisted keys and schedules correctly', async()=>{
  const requested={mode:'random',scheduleEnabled:true,scheduleTime:'10:20',
    usedIds:['tamper'],lastResult:'faked success'};
  const result=await send({type:'SAVE_SETTINGS',settings:requested});
  assert.equal(result.ok,true);
  assert.equal(result.settings.mode,'random');
  assert.equal(result.settings.scheduleEnabled,true);
  assert.equal(result.settings.scheduleTime,'10:20');
  assert.deepEqual(result.settings.usedIds,[]);
  assert.equal(result.settings.lastResult,'No runs yet.');
  assert.ok(alarms.get('fb-pfp-daily-review').when > Date.now());
});
test('invalid schedule is corrected before it reaches alarms', async()=>{
  const result=await send({type:'SAVE_SETTINGS',settings:{mode:'evil',scheduleEnabled:true,scheduleTime:'99:99'}});
  assert.equal(result.settings.mode,'cycle');
  assert.equal(result.settings.scheduleTime,'09:15');
});
test('disabling scheduling cancels the existing alarm',async()=>{
  const result=await send({type:'SAVE_SETTINGS',settings:{mode:'cycle',scheduleEnabled:false,scheduleTime:'09:15'}});
  assert.equal(result.ok,true);
  assert.equal(alarms.size,0);
});
test('unknown message has a closed default',async()=>{
  assert.deepEqual(await send({type:'DELETE_ALL'}),{ok:false,error:'Unknown request'});
});

test('a publish request is recognized but fails closed with no library', async()=>{
  const result=await send({type:'PUBLISH_NEXT'});
  assert.equal(result.ok,false);
  assert.match(result.error,/indexedDB|library|photo|unexpected/i);
});
test('review and publish are distinct explicit actions', async()=>{
  const review=await send({type:'PREPARE_NEXT'});
  assert.equal(review.ok,false);
  assert.notEqual(review.saved,true);
});
