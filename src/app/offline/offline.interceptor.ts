import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, of, tap, throwError } from 'rxjs';
import { OfflineService } from './offline.service';

// Read-only endpoints whose last good answer we keep, so the leaderboard, rules and current pub
// still show (with "last updated") when the pub has no signal.
const CACHED = [
  '/api/get-event-details', '/api/get-user-points', '/api/get-base-rules', '/api/get-locations-rules',
  '/api/player-live-state', '/api/ref-live-state', '/api/get-current-pub', '/api/get-mini-events',
  '/api/get-user-events', '/api/get-events', '/api/me',
];
const PREFIX = 'crawlr-cache:';

export const offlineInterceptor: HttpInterceptorFn = (req, next) => {
  const offline = inject(OfflineService);
  const path = req.url.split('?')[0];
  const cacheable = CACHED.includes(path);
  const key = PREFIX + path + ':' + JSON.stringify(req.body ?? '');

  return next(req).pipe(
    tap(ev => {
      if (ev instanceof HttpResponse) {
        offline.markLive();
        if (cacheable && ev.status === 200) {
          try { localStorage.setItem(key, JSON.stringify({ at: Date.now(), body: ev.body })); } catch { /* full */ }
        }
      }
    }),
    catchError(err => {
      if (err?.status === 0) {
        offline.markOffline();
        if (cacheable) {
          try {
            const hit = JSON.parse(localStorage.getItem(key) || 'null');
            if (hit) return of(new HttpResponse({ status: 200, body: hit.body, headers: req.headers }));
          } catch { /* ignore */ }
        }
      }
      return throwError(() => err);
    }),
  );
};
