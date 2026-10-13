import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tool = join(root, 'tools', 'store_resubmit.py');

test('store resubmit tool reports missing arguments', () => {
  const run = spawnSync('python3', [tool], {encoding: 'utf8'});
  assert.notEqual(run.status, 0);
  assert.match(run.stderr, /--publisher/);
});

test('store resubmit tool rejects a missing zip', () => {
  const run = spawnSync('python3', [tool, '--publisher', 'p', '--item', 'i', '--zip', '/nonexistent.zip'],
    {encoding: 'utf8'});
  assert.equal(run.status, 2);
  assert.match(run.stderr, /not found/);
});

test('store resubmit tool verifies the zip digest', () => {
  const zip = join(root, 'manifest.json'); // any small file works as a stand-in
  const run = spawnSync('python3', [tool, '--publisher', 'p', '--item', 'i', '--zip', zip,
    '--sha256', '0'.repeat(64)], {encoding: 'utf8'});
  assert.equal(run.status, 2);
  assert.match(run.stderr, /sha256 mismatch/);
});

test('store resubmit tool ships no machine-specific paths or identity markers', () => {
  const source = execFileSync('python3', ['-c',
    `print(open(${JSON.stringify(tool)}).read())`], {encoding: 'utf8'});
  assert.doesNotMatch(source, /\/Users\/(?!you\/)[\w.-]+\//);
  assert.doesNotMatch(source, /\u2013|\u2014/);
  assert.doesNotMatch(source, /codethor@gmail\.com/);
});
