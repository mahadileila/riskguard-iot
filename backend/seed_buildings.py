"""
Seeds buildings, each with its number of floors (floors are numbered 1..N).

Get-or-create on active (is_deleted = False) rows, so re-running is safe.

Run order:
    1. seed_reference_data.py 
    2. seed_buildings.py (this script)    
    3. seed_devices.py
    4. seed_simulated_data.py
    5. seed_score_history.py

Usage:
    docker compose exec backend python seed_buildings.py
"""
from app import create_app, db
from app.models import Building

# building name -> number of floors
BUILDINGS = {
    "UNITEN Putrajaya - Admin Building": 6,
    "UNITEN Putrajaya - Library": 6,
    "UNITEN Putrajaya - R&D SDN.BHD.": 3,
    "UNITEN Putrajaya - IT and Multimedia Services": 5,
    "UNITEN Putrajaya - BD Lab (Civil Engineering)": 4,
}


def seed():
    app = create_app()
    with app.app_context():
        created_count = 0

        for name, floor_count in BUILDINGS.items():
            existing = Building.query.filter_by(name=name, is_deleted=False).first()
            if existing is not None:
                continue

            db.session.add(Building(name=name, floor_count=floor_count, is_deleted=False))
            created_count += 1

        db.session.commit()
        print(f"{created_count} building(s) created.")


if __name__ == "__main__":
    seed()