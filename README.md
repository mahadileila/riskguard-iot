# 🛡️ RiskGuard IoT

A dashboard that scores the privacy risk of IoT devices in smart buildings (CCTV, badge readers, thermostats, smart meters, occupancy sensors...).

It was developed during a 16-week research internship at **UNITEN**, as the prototype supporting a conference paper on privacy risk assessment for IoT-enabled building management systems (BMS).

> ⚠️ Academic prototype, not a production security tool. Device attributes and score history are **simulated** by the seed scripts.

## 📊 How the scoring works

Each device has one or more **collection instances**, each one being a distinct data stream (for example, a camera's video feed). Every instance is rated from 0 to 4 on 7 factors:

- **Impact**: data type, sensitivity, identifiability, location tracking
- **Likelihood**: frequency, access control, data sharing

The ratings are derived deterministically from 6 raw attributes: data nature, identifiability, location scope, collection frequency, access scope and sharing scope. Sensitivity is deduced from the data type and the identifiability.

```
Score(instance) = mean(Impact) × mean(Likelihood) / 16 × 100
Score(device)   = MAX(Score(instance))
```

A score is a **percentage of the maximum theoretical risk**, not a probability.

| Score | Band |
|---|---|
| 0 – 33.99 | 🟢 Low |
| 34 – 66.99 | 🟠 Medium |
| 67 – 100 | 🔴 High |

## 🧰 Stack

| Layer | Technology |
|---|---|
| Frontend | Angular (standalone, zoneless), Tailwind CSS, Chart.js |
| Backend | Flask, Flask-SQLAlchemy, Flask-Migrate |
| Database | SQLite |
| Auth | JWT (PyJWT) |
| Infra | Docker Compose, Nginx |

## ✨ Features

- CRUD on buildings, BMS subsystems, device types and devices (search, soft delete)
- Device detail page: collection instances, raw attributes, the 7 factor ratings and sample data
- Dashboard with summary cards, a risk-by-subsystem chart and a risk trend chart (last 30 days or last 12 months)
- Building and floor filters using searchable dropdowns
- CSV export of the device inventory
- JWT login with a single admin account defined in `.env`

## 🗂️ Repository layout

```
backend/
  app/
    routes.py              API endpoints (all under /api)
    models.py              SQLAlchemy models
    services/
      auth.py              JWT creation and verification, admin credentials check
      factor_mapping.py    raw attributes -> 0-4 factor ratings
      risk_scoring.py      score formulas and risk bands
  config.py                configuration, reads backend/.env
  migrations/              Alembic migrations (Flask-Migrate)
  seed_*.py                demo data generators
  reset_demo_data.py       demo data reset script
  run.py
frontend/Angular/
  src/app/
    core/                  guards, interceptors, models, API services
    features/              one folder per page
    shared/                layout, notifications, filter combo box
  Dockerfile               production build, served by Nginx
  Dockerfile.dev           dev server with hot-reload
  nginx.conf               SPA routing and /api/ proxy to Flask
  proxy.conf.json          dev server proxy (development mode only)
docker-compose.yml         production-like mode
docker-compose.dev.yml     development mode
```

## 🚀 Running it

Requires Docker Desktop.

1. Create your env file:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Generate the admin password hash and paste it into `ADMIN_PASSWORD_HASH` in `backend/.env`:
   ```bash
   python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
   ```
3. Generate a random key and paste it into `SECRET_KEY` in `backend/.env` (it signs the JWT tokens):
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Start everything:
   ```bash
   docker compose up --build
   ```
5. In another terminal, run the migrations and the seeds. **The order matters**:
   ```bash
   docker compose exec backend flask db upgrade
   docker compose exec backend python seed_reference_data.py
   docker compose exec backend python seed_buildings.py
   docker compose exec backend python seed_devices.py
   docker compose exec backend python seed_simulated_data.py
   docker compose exec backend python seed_score_history.py
   ```
6. Open [http://localhost:4200](http://localhost:4200) and log in with the admin credentials from your `.env`.

The seeds create 5 UNITEN campus buildings with realistic devices, simulated collection instances and one year of simulated score history for the trend chart. They are safe to re-run.

The browser only talks to Nginx (port 4200), which forwards `/api/` to the Flask backend. Port 5000 is also exposed, which is useful for debugging with curl or Postman.

The database is stored in a Docker volume, so it survives `docker compose down` and restarts. To start from scratch, remove the volume and redo step 5:

```bash
docker compose down -v
```

## 🔧 Development mode

```bash
docker compose -f docker-compose.dev.yml up --build
```

- Frontend: [http://localhost:4200](http://localhost:4200), Angular dev server with hot-reload
- Backend: [http://localhost:5000](http://localhost:5000), source code mounted into the container

Development mode has to run through Docker: the dev proxy (`proxy.conf.json`) targets the `backend` service name, which only resolves inside the Compose network.

It uses its own database volume, so run the migrations and seeds once here too, adding `-f docker-compose.dev.yml` to each `docker compose exec` command. To reset it:

```bash
docker compose -f docker-compose.dev.yml down -v
```

## ⚙️ Configuration

Settings are read from `backend/.env` (template: `backend/.env.example`).

| Variable | Description |
|---|---|
| `SECRET_KEY` | Key used to sign the JWT tokens |
| `ADMIN_PASSWORD_HASH` | Hash of the admin password |
| `DATABASE_URL` | Optional. Defaults to `sqlite:////app/instance/app.db`, the path stored in the Docker volume |

## 🛠️ Common tasks

```bash
# Rebuild only the frontend after a change (production mode)
docker compose up --build -d frontend

# Create and apply a migration after changing models.py
docker compose exec backend flask db migrate -m "describe the change"
docker compose exec backend flask db upgrade

# Logs
docker compose logs -f backend
docker compose logs -f frontend
```

## 🚧 Limitations

- Only one admin account exists, defined in `.env`.
- All device data, collection instances and score history are simulated.
- The scoring rules are fixed in `factor_mapping.py` and `risk_scoring.py`.