export const MAX_SOURCE_BYTES = 8 * 1024 * 1024;
export const MAX_STORED_BYTES = 3 * 1024 * 1024;
export const MAX_DIMENSION = 1600;
export const MAX_LIBRARY_COUNT = 20;

// Check signature, not just the filename or MIME type.
export function imageFormat(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (b.length >= 3 && b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'jpeg';
  if (b.length >= 8 && [137,80,78,71,13,10,26,10].every((x, i) => b[i] === x)) return 'png';
  if (b.length >= 12 && String.fromCharCode(...b.slice(0, 4)) === 'RIFF' &&
      String.fromCharCode(...b.slice(8, 12)) === 'WEBP') return 'webp';
  return null;
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
  const bitmap = await createImageBitmap(file);
  try {
    if (bitmap.width < 1 || bitmap.height < 1 || bitmap.width > 10000 || bitmap.height > 10000) {
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
