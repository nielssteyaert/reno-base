# Renovation Budget for Home Assistant

A Home Assistant app (add-on) for tracking the budget of a home renovation. It has a sidebar panel
for expenses, payments, categories, rooms, suppliers, milestones, reports, Excel import/export and
backups. See [reno_budget/DOCS.md](reno_budget/DOCS.md) for how it works.

## Install

1. In Home Assistant, go to **Settings → Apps → Install app**.
2. Open the menu (⋮) at the top right, choose **Repositories**, add
   `https://github.com/nielssteyaert/reno-base` and click **Add**.
3. Find **Renovation Budget** in the store, install it, and start it. Home Assistant builds the image
   on your device, so the first install takes a few minutes.
4. Turn on **Show in sidebar** and open **Renovation**.

Supported architectures: `amd64` and `aarch64`.

## Repository layout

```
repository.yaml          app repository metadata
reno_budget/             the app (Docker build context)
  config.yaml            app configuration (ingress, options, backup behaviour)
  Dockerfile             builds the Vue frontend, then the Python runtime
  run.sh                 starts uvicorn on port 8099
  backend/               FastAPI + SQLAlchemy + SQLite (app/, alembic/, tests/, scripts/)
  frontend/              Vue 3 + Vite + PrimeVue
```

## Development

Backend (Python 3.12+; the image uses 3.14):

```bash
cd reno_budget/backend
uv venv .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/python -m pytest
```

Frontend:

```bash
cd reno_budget/frontend
npm ci
npm run typecheck && npm run build
```

Run locally with demo data. `RENO_DEV=1` turns off the ingress-only access check:

```bash
cd reno_budget/backend
RENO_DATA_DIR=.devdata .venv/bin/python -m scripts.seed_demo
RENO_DEV=1 RENO_DATA_DIR=.devdata RENO_STATIC_DIR=../frontend/dist .venv/bin/uvicorn app.main:app --port 8099
```

For frontend hot reload, run `npm run dev` in `frontend/`. It proxies `/api` to port 8099.

Build the container the way Home Assistant does:

```bash
docker build --build-arg BUILD_VERSION=0.1.0 --build-arg BUILD_ARCH=amd64 -t reno-budget reno_budget
```

Then run it with `RENO_DEV=1` so it accepts connections outside ingress:

```bash
docker run --rm -e RENO_DEV=1 -v "$PWD/.devdata:/data" -p 8099:8099 reno-budget
```

### Database changes

Change `backend/app/models.py`, then generate a migration and review it:

```bash
cd reno_budget/backend
.venv/bin/alembic revision --autogenerate -m "describe the change"
```

Migrations run automatically when the app starts and after a restore.

### Releasing

Bump `version` in `reno_budget/config.yaml` and add an entry to `reno_budget/CHANGELOG.md`. Home
Assistant offers the update once the commit is on GitHub.
