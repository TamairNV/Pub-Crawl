# Handoff: Pub-Crawl player mode (global rules + current location)

Written 2026-11-14 by a cloud Claude session that could edit code on the Mac but could **not** reach the server. Pick up from "What's left".

## Goal

In player mode (`/event-play/:id`), players should see:
1. The **general (base) rules** for the event.
2. The **current location** (pub) and **its rule(s)**, kept in sync with the ref as they press Next/Prev.

## Where things are

| | |
|---|---|
| Live site | https://crawl.tamairnv.co.uk (Angular SPA + Flask API at `/api/*`) |
| Server copy (deployed) | `tnv@192.168.1.199:~/Desktop/Pub-Crawl`, docker compose project: `frontend` (port 8082, nginx), `backend` (port 8001, gunicorn/Flask), `tunnel` (cloudflared, leave alone) |
| Mac copy (where edits were made) | `~/claude/pub-crawl` (git remotes: `origin` = github TamairNV/Pub-Crawl, `server` = the server folder) |
| DB | MariaDB, creds in the server's `.env` (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`). Tables used: `Event`, `Pub`, `Rule`, `Participant`, `User`, `Team`, `Point`. |

**Important: the server and Mac copies have diverged.** Server HEAD is `2ab8a29` ("Add AGENT.md…") with many uncommitted edits (routes.py, SQL_manager.py, ref.html, dashboard.*, event-details.*, auth.ts, map.html, playerDashboard.*). Mac HEAD is `67668ce`. Never rsync whole files from the Mac over the server's `routes.py` / `SQL_manager.py`.

## Design (why it's built this way)

- The ref's current pub used to live only in the ref's browser (`currentPubIndex` in `ref.ts`), so players had no way to know it. It is now stored server-side in a new column **`Event.current_pub_id`** (a `Pub.id`, not an index, so adding or removing pubs mid-crawl doesn't shift it).
- `get-locations-rules` returns one row per *rule* (Rule JOIN Pub), so a pub with two rules appears twice. The player page groups rows by pub id and shows all of that pub's rules.
- If `current_pub_id` is NULL or points at a deleted pub, players see the first pub, which matches where the ref page starts.
- Players poll `get-current-pub` every 20 s (no websockets in this app).

## Code changes (done on the Mac, uncommitted, tested: `ng build` compiles, Python compiles)

**Backend, appended to the end of each file (pure additions):**
- `flask-backend/app/SQL_manager.py`: `get_current_pub_sql(event_id)` returns `{"pub_id": ...}` or `False`. `set_current_pub_sql(event_id, pub_id)` only updates if the pub belongs to that event.
- `flask-backend/app/routes.py`:
  - `POST /api/get-current-pub` `{event_id}`: `@login_required` + `can_view_event`.
  - `POST /api/set-current-pub` `{event_id, pub_id}`: `@admin_required`.
  - Responses follow the app's `{"status", "received"}` convention.

**Frontend, whole-file changes (the server's copies of these four are unmodified since `67668ce`):**
- `src/app/admin/ref.ts`: `movePub()` now calls `saveCurrentPub()`, which POSTs to set-current-pub. After location rules load, `syncCurrentPub()` restores the index from the server.
- `src/app/player/eventPlay.ts`: adds `baseRules`, `locationsRules`, `currentPubId`, `currentStop`, `getBaseRules()`, `getLocationRules()`, `getCurrentPub()`, 20 s polling with cleanup in `ngOnDestroy`, and `updateCurrentStop()`.
- `src/app/player/eventPlay.html`: a "Current Location" card above the leaderboard and a "General Rules" card below it.
- `src/app/player/eventPlay.css`: styles copied from `ref.css` (`.pub-title`, `.badge`, `.rule-box`, `.list-container`, `.list-item`, `.description-text`).

**DB migration (not yet run):**
```sql
ALTER TABLE Event ADD COLUMN current_pub_id VARCHAR(64) NULL DEFAULT NULL;
```

## Deploy bundle (prepared, not yet run successfully)

`~/claude/pub-crawl/.tmp-build/` contains:
- `base/…`: the four frontend files as they were at `67668ce`, used for a safety check.
- `new/…`: the four edited frontend files.
- `append/…`: the exact text to append to the server's `SQL_manager.py` and `routes.py`.
- `deploy.sh`: runs **on the server**. It checks that the four frontend files on the server still match `base/` (stops otherwise) and that the backend files don't already contain `current_pub`. It backs up to `~/backups/pub-crawl_<ts>.tgz` (skips the unreadable `*.key`), copies and appends the files, and runs `py_compile`. It refuses to rebuild if any *other* uncommitted server file is newer than the running backend container (so untested edits don't ship by accident). Otherwise it adds the DB column (skipped if it already exists, via the backend container's `get_db()`), runs `docker compose up -d --build frontend backend`, and curls the new endpoint.
- `pc.tgz`: a stray source tarball from a test build. Junk, delete it.

`~/claude/pub-crawl/deploy-crawl.command` runs it from the Mac: it scps `.tmp-build` to `/tmp/crawl-deploy-2` and runs `deploy.sh` over ssh.

## What happened

- First deploy attempt: aborted at the backup step (`tar: … tnv-server.taila2c3c8.ts.net.key: Cannot open: Permission denied`). Because of `set -e`, **nothing was changed on the server.** Confirmed afterwards: `grep -c current_pub` on the server shows 0 in both files, and the containers were last built 2026-11-11 22:55.
- `deploy.sh` has since been fixed (tar `--ignore-failed-read`, excludes `*.key`, no interactive prompt) but has **not been run since the fix**.

## What's left

1. Run `~/claude/pub-crawl/deploy-crawl.command`, or do the same steps by hand on the server.
2. If it stops with "edited after the live build", look at the listed server files with Tamair before rebuilding. Those are his uncommitted changes and would go live with the rebuild.
3. Verify:
   - `curl -s -o /dev/null -w '%{http_code}' -X POST https://crawl.tamairnv.co.uk/api/get-current-pub` should return **401**. 404 means the old backend is still running.
   - Test it end to end: ref page → Next Pub → player page shows the new pub within about 20 s. General Rules are listed under the leaderboard.
   - Hard-refresh the browser if the UI looks unchanged (cached `index.html`).
4. Clean up: delete `~/claude/pub-crawl/.tmp-build/` and `deploy-crawl.command`, and `/tmp/crawl-deploy*` on the server.
5. Commit: on the server, commit the change, or commit on the Mac and reconcile with the server's `2ab8a29` plus its uncommitted work. Don't `git add .` on the server: untracked `tnv-server…ts.net.key`, `.crt`, `flask-backend/.evn`, `venv/` and macOS `._*` files are lying around there.
6. Per Tamair's server conventions: add a line to the server's `~/.claude/CLAUDE.md` (back it up first) recording that Pub-Crawl lives at `~/Desktop/Pub-Crawl` (frontend 8082, backend 8001), is served at crawl.tamairnv.co.uk via nginx-proxy-manager, and has the new `Event.current_pub_id` column and endpoints.

## Known quirks worth knowing

- Most existing API routes have no auth decorators. Only the new ones and the photo routes check login.
- `is_admin()` compares `role.lower() == 'admin'`. The frontend checks `role == 'ADMIN'`.
- The ref page is reached from the admin event-details page, so refs are admins and `set-current-pub` is admin-only.
- The `Event` table is read with `SELECT *` in a couple of places. The new column just adds a field, so nothing breaks.
