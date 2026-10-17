# 🛡️ RiskGuard IoT

A full-stack dashboard that models, scores and visualizes the **privacy risk** of IoT devices in smart buildings (CCTV, badge readers, thermostats, smart meters, occupancy sensors...).

Built during a 16-week research internship at **UNITEN**, to support a conference paper on privacy risk assessment for IoT-enabled building management systems (BMS).

> ⚠️ Academic prototype, not a production security tool. Device attributes and score history are **simulated** by seed scripts.

## 📊 How the scoring works

Each device has one or more **collection instances** (a distinct data stream, e.g. a camera's video feed). Each instance is rated 0–4 on 7 factors:

- **Impact**: Data type, Sensitivity, Identifiability, Location tracking
- **Likelihood**: Frequency, Access control, Data sharing

The ratings are derived deterministically from 6 raw attributes (data nature, identifiability, location scope, collection frequency, access scope, sharing scope). Sensitivity is deduced from data type and identifiability.

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

- Full CRUD on buildings, BMS subsystems, device types and devices (search, soft delete)
- Device detail: collection instances, raw attributes, the 7 factor ratings and sample data
- Dashboard with summary cards, risk-by-subsystem chart and a risk trend chart (last 30 days / last 12 months)
- Filter by building and floor through searchable dropdowns, which scale to hundreds of entries
- Scores displayed as percentages, with Low / Medium / High bands
- CSV export of the device inventory
- JWT login (single admin account defined in `.env`)

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
3. Start everything:
   ```bash
   docker compose up --build
   ```
4. In another terminal, migrate and seed. **The order matters**:
   ```bash
   docker compose exec backend flask db upgrade
   docker compose exec backend python seed_reference_data.py
   docker compose exec backend python seed_buildings.py
   docker compose exec backend python seed_devices.py
   docker compose exec backend python seed_simulated_data.py
   docker compose exec backend python seed_score_history.py
   ```
5. Open [http://localhost:4200](http://localhost:4200) and log in with the admin credentials from your `.env`.

The seeds create 5 UNITEN campus buildings with realistic devices, simulated collection instances, and one year of simulated score history for the trend chart. They are safe to re-run, but to start from scratch delete the database (`instance/app.db`) and redo step 4.

---
