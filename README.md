# Nyaykosh Backend (FastAPI)

Python/FastAPI backend for the **Nyaykosh** Next.js frontend (`../dpdp`). It
serves the laws catalog, the public laws API, the compliance simulator, and a
protected admin area — all logic ported 1:1 from the frontend's `src/lib`.

## Quick start

Requires **PostgreSQL** running locally (or a reachable instance).

```bash
cd dpdp_backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit SECRET_KEY / DATABASE_URL / admin creds

createdb nyaykosh             # one-time: create the database
python -m app.seed            # create tables + seed from app/data/*.json
./run.sh                       # or: uvicorn app.main:app --reload --port 8000
```

The server also creates tables + seeds on startup if empty, so `app.seed` is
optional — but handy. Use `python -m app.seed --reset` to drop and rebuild.

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

Default admin login (override in `.env`): `admin@nyaykosh.in` / `changeme123`.

## API surface

All endpoints are under `/v1`.

### Public — laws (matches the frontend `ApiPanel` samples)
| Method | Path | Description |
|---|---|---|
| GET | `/v1/laws` | List laws. Filters: `?category=`, `?status=`, `?q=` |
| GET | `/v1/laws/{slug}` | Full law by `apiSlug` or `id` |
| GET | `/v1/laws/{slug}/penalties` | Penalty schedule |
| GET | `/v1/laws/{slug}/provisions` | All provisions |
| GET | `/v1/laws/{slug}/provisions/{provisionSlug}` | One provision |

### Public — simulator
| Method | Path | Description |
|---|---|---|
| GET | `/v1/simulator/personas` | All personas → triggers → rules |
| GET | `/v1/simulator/personas/{id}` | One persona |
| POST | `/v1/simulator/evaluate` | Score a checklist (see below) |

`POST /v1/simulator/evaluate` body:
```json
{
  "personaId": "significant-data-fiduciary",
  "triggerId": "sdf_designation_received",
  "checkedKeys": ["DPDP-SDF-ECP-1::action::0", "DPDP-SDF-ECP-1::artifact::0"]
}
```
`checkedKeys` use the same `"<ruleId>::action|artifact::<index>"` format as the
frontend's `itemKey()`. The response matches `SimulatorResult` in `simulator.ts`.

### Public — content
| GET | `/v1/site` · `/v1/navigation` · `/v1/categories` |

### Auth
| POST | `/v1/auth/login` → `{ access_token, token_type, email }` |
| GET | `/v1/auth/me` (bearer) |

### Admin (all require `Authorization: Bearer <token>`)
| Method | Path | Description |
|---|---|---|
| GET | `/v1/admin/stats` | Dashboard stats (ports `adminStats.ts`) |
| POST | `/v1/admin/laws` | Create law (id derived from title+year) |
| PUT | `/v1/admin/laws/{id}` | Update law |
| DELETE | `/v1/admin/laws/{id}` | Delete law |
| GET | `/v1/admin/personas` | Read simulator rules |
| PUT | `/v1/admin/personas` | Replace simulator rules |
| GET | `/v1/admin/rules/template` | Download `.xlsx` import template |
| POST | `/v1/admin/rules/preview` | Dry-run parse+merge an uploaded `.xlsx` |
| POST | `/v1/admin/rules/import` | Parse, merge, and persist |

## Persistence

**PostgreSQL** via SQLAlchemy 2.0 (+ psycopg 3). Schema in
`app/models/db_models.py`:

- `laws` — scalar columns (id, api_slug, title, year, category, status) for
  filtering, plus a `JSONB data` column holding the full nested law record.
- `personas` — id/label/position + `JSONB data` (triggers → rules nested).
- `site_content` — key/value JSONB for `site` and `navigation`.
- `admin_users` — email + bcrypt password hash.

Storing the nested shapes as JSONB keeps the rich law/persona structure intact
(no join-heavy normalisation) while still allowing SQL filters on the common
fields. The seed data in `app/data/*.json` (copied from the frontend) is loaded
by `app/seed.py`. All DB access is isolated in `app/services/store.py`; routers
depend only on its functions.

Configure the connection via `DATABASE_URL` in `.env`, e.g.
`postgresql+psycopg://user:pass@localhost:5432/nyaykosh`.

## Wiring the frontend to this API

The frontend currently imports bundled JSON. To use this backend, point fetches
at `http://localhost:8000/v1/...`, set `API_BASE` in `src/constants/index.ts`,
and replace `src/lib/adminAuth.ts` with calls to `/v1/auth/login` (store the
returned JWT instead of the demo localStorage session).

## Tests

```bash
pip install pytest httpx
pytest
```
