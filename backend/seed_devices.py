"""
Seeds a set of representative devices across the BMS subsystems, each one
created directly with its building, floor and position inside the floor.

Devices are get-or-create by name (among active devices), so re-running
this script is safe and won't create duplicates.

Run order:
    1. seed_reference_data.py   (subsystems, device types, risk factors)
    2. seed_buildings.py        (buildings and their floor count)
    3. seed_devices.py          (this script)
    4. seed_simulated_data.py   (instances, factor scores, data samples)
    5. seed_score_history.py    (score history for the dashboard trend)

Usage:
    docker compose exec backend python seed_devices.py
"""
from app import create_app, db
from app.models import Building, Device, DeviceType

# (device_name, device_type_name, building_name, floor, zone)
# - device_type_name must match a name created by seed_reference_data.py
# - building_name must match a building created by seed_buildings.py
# - floor must be between 1 and the building's floor_count
# - zone is the free-text position inside the floor
DEVICES = [
    ("Central Thermostat",     "Central thermostat",            "Main Tower",         2,  "Open space"),
    ("Temp/Humidity Sensor",   "Temperature/humidity sensor",   "Main Tower",         2,  "Meeting room 4"),
    ("Occupancy Light Sensor", "Occupancy-linked light sensor", "Main Tower",         12, "Office area"),
    ("Lobby Camera",           "CCTV camera",                   "Main Tower",         1,  "Lobby West"),
    ("Access Card Reader",     "RFID badge reader",             "Main Tower",         1,  "Main entrance"),
    ("Server Room Smart Lock", "Smart lock",                    "Main Tower",         1,  "Server room"),
    ("Smoke Detector",         "Connected smoke/heat detector", "Main Tower",         3,  "Corridor 2"),
    ("PIR Sensor",             "PIR sensor",                    "Main Tower",         5,  "Corridor 1"),
    ("Smart Meter",            "Smart energy meter",            "Technical Building", 1,  "Electrical room"),
    ("Water Leak Detector",    "Smart water leak detector",     "Technical Building", 2,  "Plant room"),
    ("Parking Sensor",         "Parking occupancy sensor",      "Parking",            2,  "Zone B"),
    ("LPR Camera",             "LPR camera",                    "Parking",            1,  "Entrance gate"),
]


def seed():
    app = create_app()
    with app.app_context():
        created_count = 0

        for device_name, type_name, building_name, floor, zone in DEVICES:
            existing = Device.query.filter_by(name=device_name, is_deleted=False).first()
            if existing is not None:
                continue

            device_type = DeviceType.query.filter_by(name=type_name, is_deleted=False).first()
            if device_type is None:
                print(f"Skipping '{device_name}': device type '{type_name}' not found. "
                      f"Run seed_reference_data.py first.")
                continue

            building = Building.query.filter_by(name=building_name, is_deleted=False).first()
            if building is None:
                print(f"Skipping '{device_name}': building '{building_name}' not found. "
                      f"Run seed_buildings.py first.")
                continue

            if floor < 1 or floor > building.floor_count:
                print(f"Skipping '{device_name}': floor {floor} is outside "
                      f"'{building_name}' (1 to {building.floor_count}).")
                continue

            db.session.add(Device(
                name=device_name,
                id_device_type=device_type.id_device_type,
                id_building=building.id_building,
                floor=floor,
                zone=zone,
                is_deleted=False,
            ))
            created_count += 1

        db.session.commit()
        print(f"{created_count} device(s) created.")


if __name__ == "__main__":
    seed()