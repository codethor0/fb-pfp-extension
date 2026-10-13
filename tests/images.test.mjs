import test from 'node:test';
import assert from 'node:assert/strict';

import {
  imageFormat, declaredPngDimensions, dimensionsSupported,
  safePhotoName, MAX_PIXELS
} from '../src/images.mjs';

test('imageFormat detects real magic bytes only', () => {
  assert.equal(imageFormat(new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 0])), 'jpeg');
  assert.equal(imageFormat(new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10, 0, 0])), 'png');
  const webp = new Uint8Array([82, 73, 70, 70, 0, 0, 0, 0, 87, 69, 66, 80, 0, 0]);
  assert.equal(imageFormat(webp), 'webp');
  assert.equal(imageFormat(new Uint8Array([0x47, 0x49, 0x46, 0x38])), null);
  assert.equal(imageFormat(new Uint8Array([0xff, 0xd8])), null);
  assert.equal(imageFormat('not bytes'), null);
});

test('declaredPngDimensions reads IHDR without decoding', () => {
  const png = new Uint8Array(33);
  png.set([137, 80, 78, 71, 13, 10, 26, 10], 0);
  png.set([0, 0, 0, 13], 8);      // IHDR length
  png.set([73, 72, 68, 82], 12);  // 'IHDR'
  const view = new DataView(png.buffer);
  view.setUint32(16, 4000);
  view.setUint32(20, 3000);
  assert.deepEqual(declaredPngDimensions(png), {width: 4000, height: 3000});
  // Garbage without an IHDR chunk header yields null, never throws.
  assert.equal(declaredPngDimensions(new Uint8Array(10)), null);
  assert.equal(declaredPngDimensions(new Uint8Array(40)), null);
});

test('dimensionsSupported enforces the pixel budget', () => {
  assert.equal(dimensionsSupported(4000, 3000), true);
  assert.equal(dimensionsSupported(10000, 10000), false);
  assert.equal(dimensionsSupported(MAX_PIXELS, 1), false);
  assert.equal(dimensionsSupported(0, 10), false);
  assert.equal(dimensionsSupported(10.5, 10), false);
  assert.equal(dimensionsSupported(-5, 10), false);
  assert.equal(dimensionsSupported(8000, 8000), true);   // exactly at the cap
  assert.equal(dimensionsSupported(9000, 9000), false);  // 81 MP over the cap
});

test('safePhotoName strips path and markup characters', () => {
  const traversal = safePhotoName('../../../etc/passwd');
  assert.equal(/[\\/]/.test(traversal), false);
  assert.equal(/^\./.test(traversal), false);
  assert.equal(safePhotoName('<img src=x onerror=alert(1)>'), '_img_src_x_onerror_alert_1_');
  assert.equal(safePhotoName('..'), 'photo');
  assert.equal(safePhotoName(''), 'photo');
  assert.equal(safePhotoName('Vacation 2026.JPG').length <= 80, true);
  assert.equal(safePhotoName('x'.repeat(200)).length, 80);
});
