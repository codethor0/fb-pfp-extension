import test from 'node:test';
import assert from 'node:assert/strict';

import {
  imageFormat, declaredPngDimensions, dimensionsSupported,
  safePhotoName, MAX_PIXELS,
  EXPORT_TARGETS, exportTarget, squareCropSource, exportFileName
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

test('exportTarget resolves only declared targets, frozen', () => {
  const linkedin = exportTarget('linkedin');
  assert.equal(linkedin.size, 400);
  assert.equal(linkedin.maxBytes, 8 * 1024 * 1024);
  assert.equal(linkedin.label, 'LinkedIn');
  assert.equal(exportTarget('facebook'), null);
  assert.equal(exportTarget('__proto__'), null);
  assert.equal(exportTarget('constructor'), null);
  assert.equal(exportTarget('hasOwnProperty'), null);
  assert.ok(Object.isFrozen(linkedin));
  assert.ok(Object.isFrozen(EXPORT_TARGETS));
});

test('squareCropSource center-crops the short side for landscape and portrait', () => {
  assert.deepEqual(squareCropSource(600, 400), {sx: 100, sy: 0, side: 400});
  assert.deepEqual(squareCropSource(300, 500), {sx: 0, sy: 100, side: 300});
  assert.deepEqual(squareCropSource(400, 400), {sx: 0, sy: 0, side: 400});
  // Odd sizes: floor() never returns a half-pixel rectangle.
  assert.deepEqual(squareCropSource(301, 499), {sx: 0, sy: 99, side: 301});
  assert.deepEqual(squareCropSource(499, 301), {sx: 99, sy: 0, side: 301});
});

test('squareCropSource rejects dimensions the pixel budget rejects', () => {
  assert.equal(squareCropSource(0, 10), null);
  assert.equal(squareCropSource(10.5, 10), null);
  assert.equal(squareCropSource(-5, 10), null);
  assert.equal(squareCropSource(9000, 9000), null);
});

test('exportFileName builds the linkedin name and sanitizes the base', () => {
  const target = EXPORT_TARGETS.linkedin;
  assert.equal(exportFileName('Vacation 2026.JPG', target), 'Vacation_2026-linkedin-400x400.jpg');
  assert.equal(exportFileName('', target), 'portrait-linkedin-400x400.jpg');
  assert.equal(exportFileName(null, target), 'portrait-linkedin-400x400.jpg');
  const traversal = exportFileName('../../../etc/passwd.jpg', target);
  assert.equal(/[\\/]/.test(traversal), false);
  assert.ok(traversal.endsWith('-linkedin-400x400.jpg'));
  const markup = exportFileName('<img src=x onerror=alert(1)>.jpg', target);
  assert.equal(/[<>]/.test(markup), false);
  // Total length stays capped even for a very long base name.
  assert.ok(exportFileName('x'.repeat(500) + '.jpg', target).length <= 100);
  // No period injection before the suffix that could fake an extension.
  assert.ok(exportFileName('..', target).endsWith('-linkedin-400x400.jpg'));
});
