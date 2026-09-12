# Solapur Municipal Complaint Platform

Hackathon MVP for Solapur. Lifecycle first (v2 spec). Intelligence layers come later.

## Apps

- `backend/` — FastAPI + PostgreSQL/PostGIS
- `apps/web/` — Next.js municipal console
- `apps/mobile/` — Expo citizen + field worker app
- `database/geo/` — official ward GeoJSON goes here (not invented)

## L0 (this slice)

Auth, RBAC, 8 zones, 26 election wards, 7 departments, demo users, PostGIS lookup, DEMO_GEO box for Ward 1 only.

## Run

Your user is not in the `docker` group yet, so Compose needs `sudo` (or log out after `sudo usermod -aG docker $USER`).

```bash
cp .env.example .env
sudo docker compose up -d
# if the compose plugin is missing: sudo docker-compose up -d
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m seeds.seed
uvicorn app.main:app --reload --port 8000
```

To run the configurable SLA evaluator continuously in a second terminal:

```bash
cd backend
source .venv/bin/activate
export DEFAULT_SLA_ENABLED=true
python -m app.sla.worker
```

The evaluator is also available on demand to an officer, department head, or
admin at `POST /api/v1/operations/sla/run`. It records one reminder and one
escalation per complaint/status cycle, so repeated runs do not duplicate alerts.

### Operations assistant

The operations console includes a deterministic, SQL-backed assistant at
`POST /api/v1/assistant/query`. It supports only the five operational questions
listed in the specification: Ward 1 unresolved problems, highest department
workload, complaint-heavy wards, a complaint priority explanation (include the
complaint UUID), and today's operational summary. Unsupported questions return
`422`; no external model or fabricated statistic is used.

### Municipal analytics

The operations console loads department-scoped or city-wide metrics from
`GET /api/v1/analytics/summary`. Officers and department heads see only their
department; admins may optionally pass `?department_id=<id>`. The response
includes complaint KPIs, status breakdown, SLA overdue counts, workload,
ward distribution, and emerging issue categories.

### Field worker flow

Sign in on the same mobile app with the synthetic worker account
`ramesh@demo.solapur` / `Demo@1234`. Assigned complaints are available through
the worker mobile view. Workers can start work, add notes, request support,
upload an `after` photo, and submit the resolution for later verification.

API docs: http://localhost:8000/docs

### Synthetic demo logins (password `Demo@1234`)

| Role | Email |
|---|---|
| Citizen | amit@demo.solapur |
| Field worker | ramesh@demo.solapur |
| Officer (Solid Waste) | officer.swm@demo.solapur |
| Department head | head.swm@demo.solapur |
| Admin | admin@demo.solapur |

These accounts are synthetic. They are not real SMC records.

Ward 1 name and population come from the problem statement. Other ward **titles** are official SMC election-ward names; populations are null until sourced. Polygons are not fabricated: `DEMO_GEO=true` attaches a demo box around Tuljapur Naka `(17.6599, 75.9064)` to Ward 1 only. Place official GeoJSON at `database/geo/wards.geojson` and run `python backend/scripts/import_wards_geojson.py`.
