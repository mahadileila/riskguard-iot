"""
Soft-resets the demo data so it can be re-seeded from scratch.

Following the project rule "never delete, always flag", NO row is removed
from the database: every device and building is simply marked
is_deleted = True. Their collection instances, data samples and score
history stay in the database but disappear from the app (every query and
the dashboard filter on Device.is_deleted = False).

Reference data (BMS subsystems, device types, risk factors) is left untouched.

Run order after a reset:
    1. reset_demo_data.py       (this script)
    2. seed_buildings.py
    3. seed_devices.py
    4. seed_simulated_data.py
    5. seed_score_history.py

Usage:
    docker compose exec backend python reset_demo_data.py
"""
from app import create_app, db
from app.models import Building, Device


def reset():
    app = create_app()
    with app.app_context():
        devices = Device.query.filter_by(is_deleted=False).update(
            {"is_deleted": True}, synchronize_session=False
        )
        buildings = Building.query.filter_by(is_deleted=False).update(
            {"is_deleted": True}, synchronize_session=False
        )
        db.session.commit()

        print(f"{devices} device(s) and {buildings} building(s) flagged as deleted.")


if __name__ == "__main__":
    reset()