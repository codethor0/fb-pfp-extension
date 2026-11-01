import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tool = join(root, 'tools', 'edge_acceptance.py');

const source = execFileSync('python3', ['-c',
  `print(open(${JSON.stringify(tool)}).read())`], {encoding: 'utf8'});

test('edge acceptance verifies library integrity with SHA-256, not sizes', () => {
  assert.match(source, /SHA-256/);
  assert.doesNotMatch(source, /storedBytes/);
  assert.doesNotMatch(source, /sourceBytes/);
});

test('edge acceptance exercises the real popup Download button', () => {
  assert.match(source, /#export-download'\)\.click\(\)/);
  assert.match(source, /Browser\.setDownloadBehavior/);
  assert.match(source, /\.crdownload/);
});

test('edge acceptance scopes downloads and processes to the test run', () => {
  assert.match(source, /downloadPath/);
  assert.doesNotMatch(source, /~\//);
  assert.doesNotMatch(source, /pkill/);
  assert.doesNotMatch(source, /\/Users\/(?!you\/)[\w.-]+\//);
});

test('edge acceptance ships no identity markers or smart punctuation', () => {
  assert.doesNotMatch(source, /\u2013|\u2014/);
  assert.doesNotMatch(source, /codethor@gmail\.com/);
});
