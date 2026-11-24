# Pub Crawl: AGENT.md

> Read this first. It's the human-curated fact sheet for this project on TNV-server. Keep it true: fix any fact you find wrong.
> Learned memory lives in OpenWolf's `.wolf/` (`.wolf/cerebrum.md` = decisions and preferences, `.wolf/STATUS.md` = session handoff, `.wolf/buglog.json` = bugs; AGENT.md holds the facts, .wolf holds what agents learned). Server-wide: `~/AGENT.md` (index of every project), `~/.claude/CLAUDE.md`, and infra notes (`read_note("apps/pub-crawl")` with the tnv-server MCP tools, or `~/infra/notes/apps/pub-crawl.md`).
> **Before you finish a session, update "Current state / where we left off" at the bottom** (date, what changed, what's next).

## Purpose

Started as a uni project: PubCrawl web app (Angular frontend, Flask backend), public at crawl.tamairnv.co.uk. Now Tamair's **active side-income project** (paid per-event product for uni societies and stag/hen groups). Read `../AGENT.md` first. **Roadmap: `../docs/02-upgrade-plan.md`** (work from it); why: `../docs/01-feasibility-report.md`.

Tamair wants a **mobile UX overhaul** of player + ref screens (one thumb, big targets, sticky current pub, no tiny tables) that **KEEPS the current look**: big, high-contrast, "drunk-proof". Don't restyle it into something generic.

## Stack

- Frontend: Angular 21 SPA (TypeScript 5.9), built in `node:20-alpine`, served by nginx (`nginx.conf`, image `pub-crawl-frontend`).
- Backend: Flask + gunicorn on python:3.11-slim (`flask-backend/`, image `pub-crawl-backend`), pymysql, Pillow/pillow-heif, ffmpeg for chunked video uploads. API under `/api/*`; `routes.py` (routes), `SQL_manager.py` (queries), `mini_events_manager.py` (mini events).
- DB: host MariaDB 10.11 on :3306, database `pub_crawl`. Tables: `Event`, `Pub`, `Rule`, `Team`, `Participant`, `User`, `Point`, `Photo`, `MiniWheel`, `MiniWheelItem`, `PlayerTask`, `TeamPoint`, `EventAward`, `EventAwardVote`. `Event` has `current_pub_id`, `awards_voting_open`, `awards_results_visible`, `deleted_at`.

## Where it lives

| | |
|---|---|
| URL | https://crawl.tamairnv.co.uk |
| Login | Public, with its own accounts |
| Folder | `~/businesses/pub-crawl` (moved 2026-11-23; `~/Desktop/Pub-Crawl` is a symlink to it so old paths, compose labels and NPM keep working) |
| Repo | TamairNV/Pub-Crawl |
| Branch state | `main` = `origin/main` (76645b6 on 2026-11-23), clean. One source of truth: this repo. The old Mac copy (~/claude/pub-crawl) is stale |

## Run, deploy, roll back

- **Check before deploying** (no downtime, nothing live touched): `rm -rf /tmp/pc-build && mkdir /tmp/pc-build && git archive HEAD | tar -x -C /tmp/pc-build && python3 -m py_compile /tmp/pc-build/flask-backend/app/*.py && docker run --rm -v /tmp/pc-build:/app -w /app node:20-alpine sh -c 'npm ci && npx ng build --configuration=production'` (budget warnings are normal), then `docker run --rm -v /tmp:/t alpine rm -rf /t/pc-build`.
- Deploy (only when Tamair wants it live): commit first, back up (below), tag rollback images, then `cd ~/businesses/pub-crawl && docker compose up -d --build frontend backend` (never the `tunnel` service), reload NPM (see Gotchas), run `smoke-test`.
- Migrations: SQL files in `migrations/`, run by MariaDB root (ask Tamair); the app's DB user has no DDL rights.
- Route: tunnel `pub-crawl-tunnel` (container cloudflare-tunnel) -> nginx-proxy-manager (CSC2033 project) -> pub-crawl containers over Docker networks.
- Back up first: `tar czf ~/backups/pub-crawl_$(date +%Y%m%d-%H%M%S).tgz --exclude=node_modules --exclude='*.key' --exclude=uploads -C ~/businesses pub-crawl` (plus copies of `.env` and `flask-backend/.env`, chmod 600; `uploads/` is 6.7 GB, last full copy ~/backups/pub-crawl_media-move_20261115-183903.tgz). For a Docker app also tag the running image: `docker tag <image> <image>:rollback-<date>`, then roll back by re-tagging it and `docker compose up -d --no-build`, or by restoring the tarball.

## Ports and binds

- 127.0.0.1:8082 -> 80 (frontend), 127.0.0.1:8001 -> 8001 (backend). Both 127.0.0.1 only (checked 2026-11-23); NPM reaches them by container name over Docker networks. Keep it that way.

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
- The `admin` account is the OWNER (Tamair knows the password). On **live (main)** passwords are still plain text; on branch **production** they are scrypt hashes, upgraded on the next login (`app/security.py`), so a code rollback after go-live locks out anyone who logged in on the new version (see ../docs/04-go-live-plan.md).
- The backend reads the role from the DB on every request (`current_role()` in routes.py), so role changes take effect straight away. Crawl-management endpoints use `@admin_required`, `/api/manage-users` and `/api/set-user-role` use `@owner_required`, and nobody can change an OWNER's role.

## Health check

- `curl -s localhost:8082/` (page title PubCrawl; /healthz isn't real).
- Smoke-test site: `crawl`.
- After any change run `smoke-test` (and `smoke-test --tests` if you touched access-panel or house-finder). Don't finish with a new FAIL.

## Gotchas

- NPM's crawl host uses literal proxy_pass to container names: if pub-crawl-backend-1 doesn't exist, NPM reload fails and takes other sites down. Reload NPM after recreating the backend: `docker exec csc2033_team32_25-26-nginx-proxy-manager-1 nginx -s reload`.
- The folder holds a Tailscale TLS certificate and private key (tnv-server.taila2c3c8.ts.net.crt/.key), `flask-backend/.evn`, venvs and `uploads/`: .gitignore covers them since 2026-11-23, but still never `git add .` without checking `git status`.
- `HANDOFF-pub-crawl.md` (2026-11-14, from the Mac) is history: the current-location feature it describes is live (00859e3) and its `ALTER TABLE Event ADD COLUMN current_pub_id` is already done (column exists, checked 2026-11-23). Don't run its deploy steps.
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
- 2026-11-23: moved to `~/businesses/pub-crawl` (symlink at `~/Desktop/Pub-Crawl`, containers untouched, no redeploy). Committed the Nov 11-15 live server edits as `dd0bc3c` (branch `server-wip-20261123`), merged the Mac copy (branch `current-location`, same code as 00859e3; all conflicts resolved to the server side, only HANDOFF-pub-crawl.md new) in `0ca0672`, `.gitignore` for keys/venvs/uploads in `76645b6`. Pushed main + both branches to GitHub (from the Mac). py_compile and `ng build` pass. Migration check: `Event.current_pub_id`, `deleted_at` and the mini-events tables all exist, so nothing pending. main matches what is live exactly: backend .py files are byte-identical to the running container, and `ng build` of main gives the same bundle hashes the live site serves (main-BEPHA5AI.js, styles-CGKK227E.css). OpenWolf initialised (`.wolf/`). Next: upgrade plan Step 1 (password hashing, QR join, mobile UX overhaul keeping the drunk-proof look), then Stripe per-event payments.
- 2026-11-23 (Stripe): per-event payments built on branch `stripe-payments` (7a21532), NOT merged or deployed. Hosted Checkout (Group £9.99 / Society £15, GBP, test keys only), signed idempotent webhook `POST /api/stripe/webhook`, `POST /api/payments/status|checkout`, "Unlock this crawl" card on Crawl Setup, free 3-team limit only with `PAYMENTS_ENFORCE=1`. Migration `migrations/20261123_event_payments.sql` NOT run. Tests: `scripts/test-payments.sh` (11 pass, throwaway MariaDB). Plan + go-live steps: `../docs/03-stripe-plan.md`. Vault has empty STRIPE_SECRET_KEY / STRIPE_PUBLISHABLE_KEY / STRIPE_WEBHOOK_SECRET (service pub-crawl). Waiting on Tamair: Stripe CLI install + `stripe login`, test keys.
- 2026-11-23/24 (production + staging): branch `production` = main + Stripe + feature branches feat/security (scrypt hashes, upgraded on login; DB login throttle; Origin/Sec-Fetch-Site CSRF check; passkey reset instead of reveal), feat/organisers (Event.owner_user_id, EventRef co-refs, per-crawl permission checks), feat/qr-join (join tokens, guest players, player cap, /join/:token), feat/mobile-ux (sticky pub bar, one-row scoring, you-card, leaderboard now most-points-first), feat/offline (sw.js, IndexedDB queue, Point.client_id, cached reads, OFFLINE badge, media queue). Staging: compose project pub-crawl-staging (deploy/staging, `scripts/staging.sh up|seed`), 127.0.0.1:8109, own MariaDB, https://staging.pub-crawler.uk (house tunnel, Access "Pub Crawl staging"), logins from the keys vault into ~/businesses/pub-crawl-staging/.env. Migrations are numbered `migrations/NNNN_*.sql` run by `scripts/migrate.sh`; 0000-0007 applied on STAGING only. Live untouched. Next: 2f setup wizard + rule packs, 2g Stripe + free-access codes, 2h recap, 2i landing/terms, 2j hardening, then a go-live plan with rollback for Tamair.
- 2026-11-24 (2f–2j + field feedback): Tamair's crawl feedback is in ../docs/02-upgrade-plan.md ("Field feedback"). Production branch now also has: setup wizard `/new-crawl` + rule packs + per-crawl feature switches (`Event.features`), random teams, team reveal `/reveal/:id` with share image, no-phone players (`/api/add-guest-player`), 3s shared read cache for players + indexes + gunicorn WEB_CONCURRENCY=8 (load test: 200 phones, 0 errors, polling p95 79 ms); free-access codes (`/admin-codes`, `AccessCode`, `Event.unlocked_by_code`); recap `/recap/:id` + winners poster; landing `/`, `/terms`, `/privacy`; hardening: `/api/healthz` + Docker healthchecks, media retention `python -m app.maintenance media [--apply]` (90 days, `Event.keep_media`), `scripts/backup-db.sh`. Migrations 0000–0010 on STAGING only; staging crontab runs the DB dump (04:15) and retention (04:30). Stripe test keys are in the staging .env; real test Checkout works; webhook waits on Tamair (test-mode endpoint + Access bypass for /api/stripe/webhook). Go-live plan + rollback: ../docs/04-go-live-plan.md (not started, needs Tamair's OK). Live untouched.
