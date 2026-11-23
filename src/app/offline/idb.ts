// Tiny IndexedDB wrapper (no dependencies). Two stores: queued API actions and queued media files.
const DB_NAME = 'crawlr-offline';
const DB_VERSION = 1;
export const ACTIONS = 'actions';
export const MEDIA = 'media';

let dbPromise: Promise<IDBDatabase> | null = null;

function open(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(ACTIONS)) db.createObjectStore(ACTIONS, { keyPath: 'id' });
      if (!db.objectStoreNames.contains(MEDIA)) db.createObjectStore(MEDIA, { keyPath: 'id' });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => { dbPromise = null; reject(req.error); };
  });
  return dbPromise;
}

function tx<T>(store: string, mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return open().then(db => new Promise<T>((resolve, reject) => {
    const t = db.transaction(store, mode);
    const r = fn(t.objectStore(store));
    t.oncomplete = () => resolve(r.result);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  }));
}

export const idbPut = (store: string, value: any) => tx(store, 'readwrite', s => s.put(value));
export const idbDelete = (store: string, key: string) => tx(store, 'readwrite', s => s.delete(key));
export const idbAll = <T = any>(store: string) => tx<T[]>(store, 'readonly', s => s.getAll() as IDBRequest<T[]>);
