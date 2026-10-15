"""
Generates one year of simulated daily risk score snapshots per device, for the
dashboard trend chart. Starting from today's live score, each earlier day is a
small random step that is gently pulled back toward that score, so the history
ends exactly on what the app shows now and never drifts to 0 or 100. These are
demo data, not a reconstruction of real past states.

Devices that already have history are skipped, so re-running is safe.

Run order:
    1. seed_reference_data.py 
    2. seed_buildings.py        
    3. seed_devices.py
    4. seed_simulated_data.py
    5. seed_score_history.py (this script)

Run after seed_simulated_data.py:
    docker compose exec backend python seed_score_history.py
"""
import random
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import Device, RiskScoreHistory
from app.services.risk_scoring import compute_device_score, classify_score

DAYS_OF_HISTORY = 365
DAILY_NOISE = 3
PULL_TOWARD_CURRENT = 0.03


def seed():
    app = create_app()
    with app.app_context():
        now = datetime.now(timezone.utc)

        for device in Device.query.filter_by(is_deleted=False).all():
            if RiskScoreHistory.query.filter_by(id_device=device.id_device).count() > 0:
                continue

            current_score, current_classification = compute_device_score(device.id_device)
            if current_classification["label"] == "No Risk":
                continue

            walking_score = current_score

            for days_ago in range(DAYS_OF_HISTORY + 1):
                if days_ago == 0:
                    score = current_score
                    label = current_classification["label"]
                else:
                    noise = random.uniform(-DAILY_NOISE, DAILY_NOISE)
                    walking_score += PULL_TOWARD_CURRENT * (current_score - walking_score) + noise
                    walking_score = max(0.0, min(100.0, walking_score))
                    score = round(walking_score, 2)
                    label = classify_score(score)["label"]

                db.session.add(RiskScoreHistory(
                    score=score,
                    classification=label,
                    computed_at=now - timedelta(days=days_ago),
                    id_device=device.id_device,
                ))

        db.session.commit()
        print(f"Score history seeded ({DAYS_OF_HISTORY} days per device).")


if __name__ == "__main__":
    seed()