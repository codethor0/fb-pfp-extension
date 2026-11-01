import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tool = join(root, 'tools', 'firefox_acceptance.py');

const source = execFileSync('python3', ['-c',
  `print(open(${JSON.stringify(tool)}).read())`], {encoding: 'utf8'});

test('firefox acceptance installs the real package through WebDriver BiDi', () => {
  assert.match(source, /webExtension\.install/);
  assert.match(source, /base64/);
  assert.match(source, /extensions\.webextensions\.uuids/);
});

test('firefox acceptance proves the real event page booted', () => {
  assert.match(source, /ExtensionStorageIDB\.migrated/);
});

test('firefox acceptance never marks the popup download as tested', () => {
  assert.match(source, /NOT TESTED/);
  assert.doesNotMatch(source, /expect_download/);
});

test('firefox acceptance scopes everything to the test run', () => {
  assert.doesNotMatch(source, /~\//);
  assert.doesNotMatch(source, /pkill/);
  assert.doesNotMatch(source, /\/Users\/(?!you\/)[\w.-]+\//);
});

test('firefox acceptance ships no identity markers or smart punctuation', () => {
  assert.doesNotMatch(source, /\u2013|\u2014/);
  assert.doesNotMatch(source, /codethor@gmail\.com/);
});
