import { Injectable, NgZone, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { ACTIONS, MEDIA, idbAll, idbDelete, idbPut } from './idb';

export interface QueuedAction {
  id: string;            // client UUID, sent as client_id so the server ignores repeats
  url: string;
  body: any;
  created: number;
  coalesceKey?: string;  // e.g. "pub:<event>": only the newest one matters
}

export interface QueuedMedia {
  id: string;
  eventId: string;
  file: Blob;
  name: string;
  type: string;
  size: number;
  isVideo: boolean;
  created: number;
}

// Keeps the crawl going with no signal: ref actions wait in IndexedDB and are sent (once) when the
// phone is back online; read endpoints fall back to their last good answer (see offline.interceptor).
@Injectable({ providedIn: 'root' })
export class OfflineService {
  private http = inject(HttpClient);
  private zone = inject(NgZone);

  online = signal<boolean>(typeof navigator === 'undefined' ? true : navigator.onLine);
  pending = signal(0);
  queued = signal<QueuedAction[]>([]);
  mediaWaiting = signal(0);
  lastLive = signal<number | null>(null);   // when we last heard from the server
  syncing = signal(false);

  private flushing = false;
  private again = false;

  constructor() {
    window.addEventListener('online', () => this.zone.run(() => { this.online.set(true); this.flush(); }));
    window.addEventListener('offline', () => this.zone.run(() => this.online.set(false)));
    setInterval(() => this.zone.run(() => this.flush()), 15000);
    this.refreshCounts().then(() => this.flush());
  }

  markLive() { this.lastLive.set(Date.now()); if (!this.online()) this.online.set(true); }
  markOffline() { this.online.set(false); }

  /** Queue a write and try to send it straight away. Resolves once it's safely stored. */
  async send(url: string, body: any, coalesceKey?: string) {
    const action: QueuedAction = { id: crypto.randomUUID(), url, body: { ...body }, created: Date.now(), coalesceKey };
    action.body.client_id = action.id;
    if (coalesceKey) {
      for (const a of await idbAll<QueuedAction>(ACTIONS)) {
        if (a.coalesceKey === coalesceKey) await idbDelete(ACTIONS, a.id);
      }
    }
    await idbPut(ACTIONS, action);
    await this.refreshCounts();
    await this.flush();
  }

  async flush(): Promise<void> {
    if (this.flushing) { this.again = true; return; }
    this.flushing = true;
    let stalled = false;
    try {
      const actions = (await idbAll<QueuedAction>(ACTIONS)).sort((a, b) => a.created - b.created);
      if (!actions.length) return;
      this.syncing.set(true);
      for (const a of actions) {
        try {
          await firstValueFrom(this.http.post(a.url, a.body));
          await idbDelete(ACTIONS, a.id);
          this.markLive();
        } catch (err: any) {
          const status = err?.status ?? 0;
          if (status === 0 || status >= 500 || status === 429) { if (status === 0) this.markOffline(); stalled = true; break; } // try later
          await idbDelete(ACTIONS, a.id); // 4xx: the server said no; don't retry forever
        }
        await this.refreshCounts();
      }
    } catch (e) {
      console.warn('offline flush failed', e);
    } finally {
      this.flushing = false;
      this.syncing.set(false);
      await this.refreshCounts();
    }
    if (this.again && !stalled) { this.again = false; return this.flush(); }
    this.again = false;
  }

  /** Points taps still waiting to be sent, per player, so screens can add them on top of server totals. */
  pendingPoints(eventId: string | null | undefined): Record<string, number> {
    const out: Record<string, number> = {};
    for (const a of this.queued()) {
      if (a.url === '/api/give-user-points' && a.body?.event_id === eventId) {
        out[a.body.user_id] = (out[a.body.user_id] || 0) + (Number(a.body.points) || 0);
      }
    }
    return out;
  }

  // ---- media ----

  /** Videos only go up on wifi (or when we can't tell); photos go whenever there's signal. */
  canUploadNow(isVideo: boolean): boolean {
    if (!navigator.onLine) return false;
    if (!isVideo) return true;
    const c: any = (navigator as any).connection;
    if (!c) return true;
    if (c.saveData) return false;
    if (c.type) return c.type === 'wifi' || c.type === 'ethernet';
    return true;
  }

  async queueMedia(eventId: string, file: File) {
    const m: QueuedMedia = {
      id: crypto.randomUUID(), eventId, file, name: file.name, type: file.type, size: file.size,
      isVideo: file.type.startsWith('video/'), created: Date.now(),
    };
    await idbPut(MEDIA, m);
    await this.refreshCounts();
  }

  async mediaFor(eventId: string) {
    return (await idbAll<QueuedMedia>(MEDIA)).filter(m => m.eventId === eventId);
  }

  async removeMedia(id: string) {
    await idbDelete(MEDIA, id);
    await this.refreshCounts();
  }

  private async refreshCounts() {
    try {
      const acts = await idbAll<QueuedAction>(ACTIONS);
      this.queued.set(acts);
      this.pending.set(acts.length);
      this.mediaWaiting.set((await idbAll(MEDIA)).length);
    } catch { /* private mode without IndexedDB */ }
  }
}
