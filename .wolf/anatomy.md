# anatomy.md

> Auto-maintained by OpenWolf. Last scanned: 2026-11-23T20:28:48.435Z
> Files: 93 tracked | Anatomy hits: 0 | Misses: 0

> Project structure index. Auto-maintained by OpenWolf hooks and daemon.
> Run `openwolf scan` to generate, or wait for the first Claude Code session.
> Status: Pending initial scan

## ./

- `.dockerignore` — Docker ignore rules (~24 tok)
- `.editorconfig` — Editor configuration (~84 tok)
- `.gitignore` — Git ignore rules (~193 tok)
- `.prettierrc` — Prettier configuration (~43 tok)
- `AGENT.md` — Pub Crawl: AGENT.md (~3160 tok)
- `AGENTS.md` — Read AGENT.md first (~157 tok)
- `angular.json` (~570 tok)
- `CLAUDE.md` — OpenWolf (~105 tok)
- `docker-compose.yml` — Docker Compose services (~234 tok)
- `Dockerfile` — Docker container definition (~104 tok)
- `GEMINI.md` — Read AGENT.md first (~157 tok)
- `HANDOFF-pub-crawl.md` — Handoff: Pub-Crawl player mode (global rules + current location) (~1801 tok)
- `nginx.conf` — Nginx configuration (~82 tok)
- `package.json` — Node.js package manifest (~232 tok)
- `proxy.conf.json` (~46 tok)
- `Pub-Crawl.iml` (~207 tok)
- `README.md` — Project documentation (~366 tok)
- `tsconfig.app.json` — /*.ts" (~123 tok)
- `tsconfig.json` — TypeScript configuration (~274 tok)
- `tsconfig.spec.json` — /*.d.ts", (~126 tok)

## flask-backend/

- `Dockerfile` — Docker container definition (~155 tok)
- `requirements.txt` — Python dependencies (~21 tok)
- `run.py` — API router (~72 tok)

## flask-backend/app/

- `__init__.py` — API router (~852 tok)
- `clean_up.py` — URL configuration (~135 tok)
- `config.py` — Declares Config (~112 tok)
- `mini_events_manager.py` — db_conn, ensure_mini_events_schema, get_wheels_for_event_sql, create_wheel_sql + 5 more (~12060 tok)
- `routes.py` — Flask routes: 19 endpoints (~12557 tok)
- `SQL_manager.py` — get_db, run_query, get_all_users_sql, select_users_sql + 17 more (~6374 tok)

## flask-backend/app/templates/

- `base.html` — Title (~32 tok)

## flask-backend/app/templates/errors/

- `400.html` (~111 tok)
- `403.html` (~110 tok)
- `404.html` (~109 tok)
- `500.html` (~115 tok)

## migrations/

- `20261114_mini_events.sql` — SQL: tables: MiniWheel, MiniWheelItem, PlayerTask, TeamPoint, 2 alter(s) (~1124 tok)
- `20261114_soft_delete.sql` — SQL: 2 alter(s) (~51 tok)

## src/

- `index.html` — PubCrawl (~108 tok)
- `main.ts` (~69 tok)
- `styles.css` — Styles: 13 rules, 6 vars, 1 media queries (~815 tok)

## src/app/

- `app.config.ts` — Exports appConfig (~144 tok)
- `app.css` (~0 tok)
- `app.html` (~432 tok)
- `app.routes.ts` — Exports routes (~381 tok)
- `app.spec.ts` (~0 tok)
- `app.ts` — Exports AppComponent (~84 tok)
- `auth.interceptor.ts` — If the server says we're not logged in (e.g. an old saved login from before (~211 tok)
- `auth.spec.ts` (~95 tok)
- `auth.ts` — Exports UserProfile, AuthService (~245 tok)
- `create_account.css` — Styles: 1 rules (~444 tok)

## src/app/account/

- `create_account.html` (~232 tok)
- `create_account.ts` — API routes: POST (1 endpoints) (~479 tok)
- `login.css` — Styles: 13 rules, 1 media queries (~754 tok)
- `login.html` (~162 tok)
- `login.ts` — API routes: POST (1 endpoints) (~576 tok)

## src/app/admin/

- `admin-shared.css` (~0 tok)
- `dashboard.css` — Styles: 65 rules, 1 media queries (~2567 tok)
- `dashboard.html` (~1620 tok)
- `dashboard.ts` — API routes: GET, POST (9 endpoints) (~2076 tok)
- `event-details.css` — Styles: 84 rules, 1 media queries (~2906 tok)
- `event-details.html` (~3660 tok)
- `event-details.ts` — Colours offered for new teams, in order (~4682 tok)
- `mini-events-setup.css` — Styles: 42 rules (~1284 tok)
- `mini-events-setup.html` (~1806 tok)
- `mini-events-setup.ts` — API routes: POST (9 endpoints) (~2483 tok)
- `ref-mini-events.css` — Styles: 69 rules (~1952 tok)
- `ref-mini-events.html` (~4879 tok)
- `ref-mini-events.ts` — API routes: POST (5 endpoints) (~5328 tok)
- `ref.css` — Styles: 42 rules (~1412 tok)
- `ref.html` (~982 tok)
- `ref.ts` — API routes: GET, POST (9 endpoints) (~2387 tok)
- `restore.css` — Styles: 27 rules (~949 tok)
- `restore.html` (~835 tok)
- `restore.ts` — API routes: GET, POST (4 endpoints) (~1177 tok)

## src/app/photos/

- `map.css` — Styles: 30 rules (~1378 tok)
- `map.html` (~559 tok)
- `map.ts` — ngAfterViewInit(): void { (~1471 tok)
- `upload.css` — Styles: 14 rules (~914 tok)
- `upload.html` (~285 tok)
- `upload.ts` — Send one chunk, retrying with exponential backoff on transient errors. (~1819 tok)

## src/app/player/

- `eventPlay.css` — Styles: 21 rules (~916 tok)
- `eventPlay.html` (~689 tok)
- `eventPlay.ts` — API routes: GET, POST (6 endpoints) (~2270 tok)
- `player-mini-events.css` — Styles: 41 rules (~1330 tok)
- `player-mini-events.html` (~2147 tok)
- `player-mini-events.ts` — API routes: POST (4 endpoints) (~2636 tok)
- `playerDashboard.css` — Styles: 18 rules (~782 tok)
- `playerDashboard.html` (~250 tok)
- `playerDashboard.ts` — API routes: GET, POST (2 endpoints) (~490 tok)

## src/app/shared/

- `mini-events.types.ts` — Exports WheelItem, MiniWheel, PlayerTask, EventAward, formatRewardBadge (~588 tok)
- `password-reveal.ts` — API routes: POST (1 endpoints) (~657 tok)

## src/app/shared/spin-wheel/

- `spin-wheel.css` — Styles: 15 rules (~596 tok)
- `spin-wheel.html` (~254 tok)
- `spin-wheel.ts` — Exports SpinCommand, SpinWheelComponent (~2197 tok)
