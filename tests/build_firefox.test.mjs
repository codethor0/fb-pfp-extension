import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, readFileSync, existsSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {firefoxManifest, buildFirefox, GECKO_ID} from '../tools/build_firefox.mjs';

const chrome = JSON.parse(readFileSync(new URL('../manifest.json', import.meta.url), 'utf8'));

test('firefox manifest swaps the service worker for an event page', () => {
  const ff = firefoxManifest(chrome);
  assert.deepEqual(ff.background, {scripts: [chrome.background.service_worker], type: 'module'});
  assert.equal('service_worker' in ff.background, false);
  assert.equal('minimum_chrome_version' in ff, false);
});
test('firefox manifest declares an id and that no data is collected', () => {
  const gecko = firefoxManifest(chrome).browser_specific_settings.gecko;
  assert.equal(gecko.id, GECKO_ID);
  assert.match(gecko.id, /^[a-z0-9._-]+@[a-z0-9.-]+$/);
  assert.deepEqual(gecko.data_collection_permissions, {required: ['none']});
  assert.match(gecko.strict_min_version, /^\d+\.\d+$/);
  assert.match(firefoxManifest(chrome).browser_specific_settings.gecko_android.strict_min_version, /^\d+\.\d+$/);
});
test('firefox manifest never widens permissions or the Chrome manifest', () => {
  const before = JSON.stringify(chrome);
  const ff = firefoxManifest(chrome);
  assert.equal(JSON.stringify(chrome), before, 'input manifest was mutated');
  for (const key of ['permissions', 'host_permissions', 'content_scripts', 'content_security_policy', 'action']) {
    assert.deepEqual(ff[key], chrome[key], key);
  }
});
test('build writes only the manifest, src and icons', () => {
  const out = mkdtempSync(join(tmpdir(), 'fb-pfp-ff-'));
  try {
    buildFirefox(out);
    for (const file of ['manifest.json', 'src/background.mjs', 'src/content.js', 'src/popup.html', 'icons/icon128.png']) {
      assert.ok(existsSync(join(out, file)), file);
    }
    for (const file of ['tools', 'tests', 'README.md', 'verify.sh']) {
      assert.equal(existsSync(join(out, file)), false, file + ' must not ship');
    }
    assert.equal(JSON.parse(readFileSync(join(out, 'manifest.json'), 'utf8')).background.scripts[0], 'src/background.mjs');
  } finally { rmSync(out, {recursive: true, force: true}); }
});
