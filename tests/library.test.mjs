import test from 'node:test';
import assert from 'node:assert/strict';
import {validPhotoRecord} from '../src/library.mjs';

const jpeg = new Blob([new Uint8Array([0xff, 0xd8, 0xff, 0xe0])], {type: 'image/jpeg'});

test('a well-formed record is accepted', () => {
  assert.equal(validPhotoRecord({id: '3f2a1b9c-1111-4222-8333-944455556666',
    blob: jpeg, addedAt: 1728000000000}), true);
});

test('malformed records from hostile or corrupt storage are rejected', () => {
  assert.equal(validPhotoRecord(null), false);
  assert.equal(validPhotoRecord('nope'), false);
  assert.equal(validPhotoRecord({}), false);
  // Wrong id shape, prototype tricks, and script ids all fail closed.
  assert.equal(validPhotoRecord({id: '../../etc', blob: jpeg, addedAt: 1}), false);
  assert.equal(validPhotoRecord({id: '<script>', blob: jpeg, addedAt: 1}), false);
  assert.equal(validPhotoRecord(JSON.parse('{"__proto__": {"x": 1}, "id": "3f2a1b9c-1111-4222-8333-944455556666"}')), false);
  // Non-JPEG or non-Blob payloads are never usable as photos.
  assert.equal(validPhotoRecord({id: '3f2a1b9c-1111-4222-8333-944455556666',
    blob: new Blob(['x'], {type: 'text/html'}), addedAt: 1}), false);
  assert.equal(validPhotoRecord({id: '3f2a1b9c-1111-4222-8333-944455556666',
    blob: 'not-a-blob', addedAt: 1}), false);
  // Timestamps must be finite numbers.
  assert.equal(validPhotoRecord({id: '3f2a1b9c-1111-4222-8333-944455556666',
    blob: jpeg, addedAt: 'tomorrow'}), false);
  assert.equal(validPhotoRecord({id: '3f2a1b9c-1111-4222-8333-944455556666',
    blob: jpeg, addedAt: NaN}), false);
});

test('pollution attempts do not touch Object.prototype', () => {
  JSON.parse('{"__proto__": {"polluted": true}}');
  assert.equal(Object.prototype.polluted, undefined);
});
