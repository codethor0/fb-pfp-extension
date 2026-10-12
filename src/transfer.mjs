// Chrome extension runtime messages serialize via JSON. Bound payloads to 3 MB.
export async function encodePhoto(blob) {
  if (!(blob instanceof Blob) || blob.type !== 'image/jpeg' || blob.size > 3 * 1024 * 1024) {
    throw new Error('Cannot transfer this image');
  }
  const array = new Uint8Array(await blob.arrayBuffer());
  const partSize = 0x8000;
  const parts = [];
  for (let i = 0; i < array.length; i += partSize) {
    parts.push(String.fromCharCode(...array.subarray(i, i + partSize)));
  }
  return btoa(parts.join(''));
}
