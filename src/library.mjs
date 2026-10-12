// Images remain in this extension's IndexedDB. They are never saved to a repository.
const NAME = 'fb-pfp-library';
const STORE = 'photos';
const VERSION = 1;

function requestValue(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Photo storage failed'));
  });
}

export function openLibrary() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(NAME, VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'id' });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Unable to open local photo library'));
  });
}

async function transact(mode, operation) {
  const db = await openLibrary();
  try {
    const tx = db.transaction(STORE, mode);
    // Register completion handlers before any request can finish.
    const completed = new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error || new Error('Photo storage transaction failed'));
      tx.onabort = () => reject(tx.error || new Error('Photo storage transaction aborted'));
    });
    const result = await requestValue(operation(tx.objectStore(STORE)));
    await completed;
    return result;
  } finally { db.close(); }
}

export async function listPhotos() {
  const photos = await transact('readonly', store => store.getAll());
  return photos.sort((a, b) => a.addedAt - b.addedAt || a.id.localeCompare(b.id));
}

export function savePhoto(photo) {
  if (!photo || !/^[a-f0-9-]{36}$/.test(photo.id) || !(photo.blob instanceof Blob) || photo.blob.type !== 'image/jpeg') {
    throw new TypeError('Invalid photo record');
  }
  return transact('readwrite', store => store.put(photo));
}

export function deletePhoto(id) {
  if (typeof id !== 'string') throw new TypeError('Invalid photo ID');
  return transact('readwrite', store => store.delete(id));
}

export async function getPhoto(id) {
  return transact('readonly', store => store.get(id));
}
