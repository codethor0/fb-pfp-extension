export const MAX_SOURCE_BYTES = 8 * 1024 * 1024;
export const MAX_STORED_BYTES = 3 * 1024 * 1024;
export const MAX_DIMENSION = 1600;
export const MAX_LIBRARY_COUNT = 20;
export const MAX_PIXELS = 64_000_000;

// Local export targets: platforms the user uploads to by hand. Sizes and
// byte limits come from each platform's own published requirements.
// LinkedIn Help (checked 2026-10-29): profile photo minimum 400 x 400 px,
// maximum file size 8 MB.
export const EXPORT_TARGETS = Object.freeze({
  linkedin: Object.freeze({id: 'linkedin', label: 'LinkedIn', size: 400, maxBytes: 8 * 1024 * 1024})
});

export function exportTarget(id) {
  return Object.prototype.hasOwnProperty.call(EXPORT_TARGETS, id) ? EXPORT_TARGETS[id] : null;
}

// Center square crop rectangle for a source of the given dimensions.
// Pure geometry: no canvas, no decoding, safe to unit test. Returns null
// for dimensions the pixel budget rejects.
export function squareCropSource(width, height) {
  if (!dimensionsSupported(width, height)) return null;
  const side = Math.min(width, height);
  return {sx: Math.floor((width - side) / 2), sy: Math.floor((height - side) / 2), side};
}

// Download filename: sanitized stored name (or 'portrait') plus the target
// id and pixel size. The suffix is fixed and short; the base is capped so
// the whole name stays under 100 characters.
export function exportFileName(originalName, target) {
  const raw = String(originalName || '').replace(/\.[^.]*$/, '');
  const base = raw ? (safePhotoName(raw) || 'portrait') : 'portrait';
  const suffix = `-${target.id}-${target.size}x${target.size}.jpg`;
  const cap = Math.max(1, 100 - suffix.length);
  return base.slice(0, cap) + suffix;
}

// Check signature, not just the filename or MIME type.
export function imageFormat(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (b.length >= 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'jpeg';
  if (b.length >= 8 && [137,80,78,71,13,10,26,10].every((x, i) => b[i] === x)) return 'png';
  if (b.length >= 12 && String.fromCharCode(...b.slice(0, 4)) === 'RIFF' &&
      String.fromCharCode(...b.slice(8, 12)) === 'WEBP') return 'webp';
  return null;
}

// PNG width and height are big-endian uint32 values in the IHDR chunk at byte
// offsets 16 and 20. Reading them before decode rejects decompression bombs
// that a small compressed file could otherwise expand into.
export function declaredPngDimensions(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (b.length < 24 || b[12] !== 0x49 || b[13] !== 0x48 || b[14] !== 0x44 || b[15] !== 0x52) return null;
  const view = new DataView(b.buffer, b.byteOffset, b.byteLength);
  return {width: view.getUint32(16), height: view.getUint32(20)};
}

export function dimensionsSupported(width, height) {
  return Number.isInteger(width) && Number.isInteger(height) &&
    width >= 1 && height >= 1 &&
    width <= 10000 && height <= 10000 &&
    width * height <= MAX_PIXELS;
}

export function safePhotoName(name) {
  const cleaned = String(name || 'photo').replace(/[^a-zA-Z0-9_.-]/g, '_').replace(/_+/g, '_').replace(/^\.+/, '').slice(0, 80);
  return cleaned || 'photo';
}

// Called from the popup, which has a DOM and can draw into a canvas.
// Canvas re-encoding strips camera EXIF and GPS metadata before storage/upload.
export async function normalizePhoto(file) {
  if (!(file instanceof Blob) || file.size === 0 || file.size > MAX_SOURCE_BYTES) {
    throw new Error('Each image must be between 1 byte and 8 MB');
  }
  const signature = imageFormat(new Uint8Array(await file.slice(0, 16).arrayBuffer()));
  if (!signature) throw new Error('Use a valid JPEG, PNG or WebP image');
  if (signature === 'png') {
    const declared = declaredPngDimensions(new Uint8Array(await file.slice(0, 33).arrayBuffer()));
    if (!declared || !dimensionsSupported(declared.width, declared.height)) {
      throw new Error('Image dimensions are unsupported');
    }
  }
  const bitmap = await createImageBitmap(file);
  try {
    if (!dimensionsSupported(bitmap.width, bitmap.height)) {
      throw new Error('Image dimensions are unsupported');
    }
    const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Image converter unavailable');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve, reject) => canvas.toBlob(
      result => result ? resolve(result) : reject(new Error('Could not normalize image')),
      'image/jpeg', 0.88));
    if (blob.size > MAX_STORED_BYTES) throw new Error('Processed photo exceeds 3 MB');
    return {blob, width:canvas.width, height:canvas.height, originalName:safePhotoName(file.name)};
  } finally { bitmap.close(); }
}

// Shared source validation for the export path. Mirrors the guards in
// normalizePhoto but leaves that function and the Facebook pipeline untouched.
async function validateExportSource(source) {
  if (!(source instanceof Blob) || source.size === 0 || source.size > MAX_SOURCE_BYTES) {
    throw new Error('Each image must be between 1 byte and 8 MB');
  }
  const signature = imageFormat(new Uint8Array(await source.slice(0, 16).arrayBuffer()));
  if (!signature) throw new Error('Use a valid JPEG, PNG or WebP image');
  if (signature === 'png') {
    const declared = declaredPngDimensions(new Uint8Array(await source.slice(0, 33).arrayBuffer()));
    if (!declared || !dimensionsSupported(declared.width, declared.height)) {
      throw new Error('Image dimensions are unsupported');
    }
  }
  return signature;
}

// Local export transform: center square crop, resize to the target's square
// size, re-encode as metadata-free JPEG. Pure over its inputs: the stored
// blob is read-only, nothing is written back to the library, and no state is
// shared with the Facebook rotation. `upscaled` flags sources whose shorter
// side is below the target size so the UI can warn.
export async function cropSquareForExport(source, targetId, originalName = '') {
  const target = exportTarget(targetId);
  if (!target) throw new Error('Unknown export target');
  await validateExportSource(source);
  const bitmap = await createImageBitmap(source);
  try {
    if (!dimensionsSupported(bitmap.width, bitmap.height)) {
      throw new Error('Image dimensions are unsupported');
    }
    const crop = squareCropSource(bitmap.width, bitmap.height);
    const canvas = document.createElement('canvas');
    canvas.width = target.size;
    canvas.height = target.size;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Image converter unavailable');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, crop.sx, crop.sy, crop.side, crop.side, 0, 0, target.size, target.size);
    const blob = await new Promise((resolve, reject) => canvas.toBlob(
      result => result ? resolve(result) : reject(new Error('Could not export image')),
      'image/jpeg', 0.88));
    if (blob.size > MAX_STORED_BYTES) throw new Error('Exported photo exceeds 3 MB');
    return {
      blob,
      width: target.size,
      height: target.size,
      fileName: exportFileName(originalName, target),
      upscaled: crop.side < target.size
    };
  } finally { bitmap.close(); }
}
