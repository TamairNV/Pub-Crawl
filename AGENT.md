# Pub Crawl: AGENT.md

> Read this first. It's the human-curated fact sheet for this project on TNV-server. Keep it true: fix any fact you find wrong.
> Learned memory lives in OpenWolf's `.wolf/` (`.wolf/cerebrum.md` = decisions and preferences, `.wolf/STATUS.md` = session handoff, `.wolf/buglog.json` = bugs; AGENT.md holds the facts, .wolf holds what agents learned). Server-wide: `~/AGENT.md` (index of every project), `~/.claude/CLAUDE.md`, and infra notes (`read_note("apps/pub-crawl")` with the tnv-server MCP tools, or `~/infra/notes/apps/pub-crawl.md`).
> **Before you finish a session, update "Current state / where we left off" at the bottom** (date, what changed, what's next).

## Purpose

Uni project: PubCrawl web app (Angular frontend, Flask backend), public at crawl.tamairnv.co.uk.

## Where it lives

| | |
|---|---|
| URL | https://crawl.tamairnv.co.uk |
| Login | Public, with its own accounts |
| Folder | `~/Desktop/Pub-Crawl` |
| Repo | TamairNV/Pub-Crawl |
| Branch state | `main`, ahead of origin with uncommitted changes (2026-11-11 admin roles + setup page not committed) |

## Run, deploy, roll back

- `cd ~/Desktop/Pub-Crawl && docker compose up -d --build`.
- Route: tunnel `pub-crawl-tunnel` (container cloudflare-tunnel) -> nginx-proxy-manager (CSC2033 project) -> pub-crawl containers over Docker networks.
- Back up first: `tar czf ~/backups/pub-crawl_$(date +%Y%m%d-%H%M%S).tgz -C /home/tnv/Desktop Pub-Crawl` (plus a copy of `.env`). For a Docker app also tag the running image: `docker tag <image> <image>:rollback-<date>`, then roll back by re-tagging it and `docker compose up -d --no-build`, or by restoring the tarball.

## Ports and binds

- 127.0.0.1:8082 -> 80 (frontend), 127.0.0.1:8001 -> 8001 (backend).

## Containers and processes

- Compose project `pub-crawl`: `pub-crawl-frontend-1`, `pub-crawl-backend-1` (also on csc2033_team32_25-26_default), `cloudflare-tunnel`. Networks pub-crawl_default and csc2033_team32_25-26_default are external.

## Data

- `uploads/` mounted into the backend at /app/static/uploads.

## Secrets (names only, never values)

- `.env`: CLOUDFLARE_TUNNEL_TOKEN, SECRET_KEY. `flask-backend/.env` (copied into the backend image at build): DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT (MariaDB 10.11). `flask-backend/.evn` is a stray copy of it.

## Depends on

- nginx-proxy-manager in ~/Desktop/CSC2033_Team32_25-26 (it proxies crawl).
- Tunnel pub-crawl-tunnel.

## Accounts and roles

- `User.role`: `player` (default), `ADMIN` (create and run crawls), `OWNER` (an admin who can also make people admin or take it away, on the admin dashboard's Admins card).
- The `admin` account is the OWNER (Tamair knows the password). Passwords are stored in plain text in `User.password` (uni code, not changed).
- The backend reads the role from the DB on every request (`current_role()` in routes.py), so role changes take effect straight away. Crawl-management endpoints use `@admin_required`, `/api/manage-users` and `/api/set-user-role` use `@owner_required`, and nobody can change an OWNER's role.

## Health check

- `curl -s localhost:8082/` (page title PubCrawl; /healthz isn't real).
- Smoke-test site: `crawl`.
- After any change run `smoke-test` (and `smoke-test --tests` if you touched access-panel or house-finder). Don't finish with a new FAIL.

## Gotchas

- NPM's crawl host uses literal proxy_pass to container names: if pub-crawl-backend-1 doesn't exist, NPM reload fails and takes other sites down. Reload NPM after recreating the backend: `docker exec csc2033_team32_25-26-nginx-proxy-manager-1 nginx -s reload`.
- The folder holds a Tailscale TLS certificate and private key (tnv-server.taila2c3c8.ts.net.crt/.key) that .gitignore doesn't cover: never commit them.
- Stale `pub-crawl-backend-run-*` one-off containers can be removed.
- `.dockerignore` (frontend build context) must exclude `uploads/` (6.7 GB+) and the Tailscale key; fixed 2026-11-11 (it said `flask_backend`).
- MariaDB (`pub_crawl` DB) runs on the host at `:3306` (not `groupDB`/`groupDBPro`). The app's DB user (`flask-backend/.env`) lacks `CREATE`/`ALTER` DDL privileges, so SQL files in `migrations/` (`20261114_mini_events.sql`, `20261114_soft_delete.sql`) must be run by MariaDB root; `CREATE command denied` notes at worker boot from `ensure_mini_events_schema()` are benign once migrated.

## Current state / where we left off

Agents: add a dated line here at the end of every session, newest last, and trim old lines once they stop mattering.

- 2026-11-08: AGENT.md created from the code, compose files and infra notes (server map work).
- 2026-11-11: added the OWNER role and the `admin` account (can promote and demote admins), locked crawl-management APIs to admins, and redesigned the crawl page as a 4-step setup (teams with quick start, players with search and spread evenly, pubs in order with ↑↓, rules). Pubs no longer need a rule (LEFT JOIN). Backup ~/backups/pub-crawl_20261111-142420*, images :rollback-20261111. Not committed yet.
- 2026-11-11: fixed Crawl Setup page bugs: made `.crawl-name` bright white on dark background, changed the 4 step nav links (`#teams`, `#players`, `#pubs`, `#rules`) to buttons with smooth scrolling so they don't redirect to `/login` due to `<base href="/">`, and added `/api/set-pub-rule` + UI to add/edit/remove rules on existing locations both inline in Step 3 (Pubs) and via a location selector in Step 4 (Rules). Backup `~/backups/pub-crawl_20261111-224600.tgz`.
- 2026-11-14: added Mini Events inside each crawl (`MiniWheel`, `MiniWheelItem`, `PlayerTask`, `TeamPoint`, `EventAward`, `EventAwardVote` + `Event.awards_voting_open`/`awards_results_visible`): multiple spin-the-wheel mini events per crawl in Crawl Setup Step 5 (tasks/outcomes with points, deductions, or stealing points from another team), live Ref Mode controls (`ref-mini-events`) to click any player's name and send random/custom tasks or spin the wheel directly, confirm tasks (letting either Ref or Player spin/pick sabotage target atomically), and Crawl Awards setup (Step 6) + Ref proxy voting on behalf of non-logged-in players + Player live pop-ups & awards voting (`player-mini-events`, `eventPlay` polling `/api/player-live-state`). Backup `~/backups/pub-crawl_20261114-154600.tgz`, images `:rollback-20261114`.
- 2026-11-14: ordered crawls newest-first (`ORDER BY created_at DESC` in `get_all_events_sql` and `events_user_is_in_sql`, showing dates on Admin & Player dashboards), fixed spin-wheel label text bleeding under the center `SPIN` hub (`spin-wheel.ts` radial bounds/dynamic sizing/2-line wrap + `spin-wheel.css` opaque `.center-hub:disabled`), converted event deletion to `OWNER`-only soft delete (`Event.deleted_at` via `migrations/20261114_soft_delete.sql`), added the `OWNER`-only `/admin-restore` page (`/api/get-deleted-events`, `/api/restore-event`, `/api/purge-event`), and added an `OWNER`-only **Reset Scores** action (`POST /api/reset-event`, on `/admin-dashboard` rows and `/event-details/:id` header) that clears `Point`, `TeamPoint`, `PlayerTask`, `EventAwardVote`, optional `Photo` + uploaded media, and resets `current_pub_id` / award toggles while keeping teams, players, pubs, rules, wheels, and awards.
- 2026-11-14 (hardening): fixed `SQL_manager.py` leaking open MariaDB connections under mobile polling (`_run` / `_close_conn` + `try/finally: _close_conn`), set Flask `DEBUG = False` and `TESTING = False` in `config.py`, and added `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)` in `flask-backend/app/__init__.py` for Cloudflare/NPM proxy headers.
- 2026-11-14 (mobile UX + password reveal): disabled iOS double-tap & input auto-zoom globally (`viewport maximum-scale=1, user-scalable=no` in `src/index.html`, `touch-action: manipulation` + `user-select: none` on buttons + `max(16px, 1rem)` coarse-pointer input sizing in `src/styles.css`), added an admin-visibility passkey notice on `/create-account` (`src/app/account/create_account.html`), and added admin/owner-only `POST /api/reveal-password` (protecting `OWNER` accounts from `ADMIN`s, `Cache-Control: no-store`) with shared [`<app-password-reveal>`](src/app/shared/password-reveal.ts) inside Referee Mode's player modal and Crawl Setup Step 2 players.
- 2026-11-15: crawl photos (Beach, Crawl of John, Alan Car 1, Donegal) copied into share.tamairnv.co.uk galleries (pubcrawl-* in /mnt/fpv2tb/event-photos/events). The /map-view page now shows an Open-the-gallery button for those four events (SHARE_GALLERIES in src/app/photos/map.ts). Originals still in uploads/ (backup ~/backups/pub-crawl_media-move_20261115-183903.tgz); frontend rollback image pub-crawl-frontend:rollback-20261115. Upload still writes to uploads/. Phoebe 21st has no photos yet and is not mapped.
