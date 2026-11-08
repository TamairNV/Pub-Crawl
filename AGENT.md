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
| Branch state | `main`, 1 commit ahead of origin and uncommitted changes on 2026-11-08 |

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

- `.env`: CLOUDFLARE_TUNNEL_TOKEN, SECRET_KEY. The backend reads DB_HOST/DB_USER/DB_NAME/DB_PORT (app/SQL_manager.py) but this .env doesn't set them, so which database it uses isn't recorded here: check before relying on it.

## Depends on

- nginx-proxy-manager in ~/Desktop/CSC2033_Team32_25-26 (it proxies crawl).
- Tunnel pub-crawl-tunnel.

## Health check

- `curl -s localhost:8082/` (page title PubCrawl; /healthz isn't real).
- Smoke-test site: `crawl`.
- After any change run `smoke-test` (and `smoke-test --tests` if you touched access-panel or house-finder). Don't finish with a new FAIL.

## Gotchas

- NPM's crawl host uses literal proxy_pass to container names: if pub-crawl-backend-1 doesn't exist, NPM reload fails and takes other sites down. Reload NPM after recreating the backend: `docker exec csc2033_team32_25-26-nginx-proxy-manager-1 nginx -s reload`.
- The folder holds a Tailscale TLS certificate and private key (tnv-server.taila2c3c8.ts.net.crt/.key) that .gitignore doesn't cover: never commit them.
- Stale `pub-crawl-backend-run-*` one-off containers can be removed.

## Current state / where we left off

Agents: add a dated line here at the end of every session, newest last, and trim old lines once they stop mattering.

- 2026-11-08: AGENT.md created from the code, compose files and infra notes (server map work).
