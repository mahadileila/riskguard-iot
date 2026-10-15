"""
Seeds a set of representative devices for a university campus (UNITEN Putrajaya),
spread across the BMS subsystems. Each device is created directly with its
building, floor and position inside the floor.

Buildings are NOT retyped here: they are looked up in the database (created by
seed_buildings.py) from a short keyword, so a typo in a full building name can
never silently skip a device. If a keyword matches zero or several buildings,
the script stops before creating anything and lists the buildings it found.

Devices are get-or-create by name (among active devices), so re-running
this script is safe and won't create duplicates.

Run order:
    1. seed_reference_data.py
    2. seed_buildings.py
    3. seed_devices.py (this script)
    4. seed_simulated_data.py
    5. seed_score_history.py

Usage:
    docker compose exec backend python seed_devices.py
"""
from app import create_app, db
from app.models import Building, Device, DeviceType

# Keywords matched (case-insensitive, substring) against building names in the database.
# Each keyword must match exactly one active building.
ADMIN = "Admin"
LIBRARY = "Library"
RND = "R&D"
IT = "IT and Multimedia"
CIVIL = "Civil"

# (device_name, device_type_name, building_keyword, floor, zone)
# - device_name must be unique among active devices
# - device_type_name must match a name created by seed_reference_data.py
# - building_keyword must match exactly one building created by seed_buildings.py
# - floor must be between 1 and the building's floor_count (1 = ground floor)
# - zone is the free-text position inside the floor
DEVICES = [
    # ---------- Admin Building: offices, reception, records, main vehicle gate ----------
    ("Admin Lobby CCTV",                  "CCTV camera",                   ADMIN, 1, "Main lobby"),
    ("Admin Entrance Card Reader",        "RFID badge reader",             ADMIN, 1, "Main entrance"),
    ("Registrar Records Room Smart Lock", "Smart lock",                    ADMIN, 2, "Student records room"),
    ("Admin Corridor Smoke Detector",     "Connected smoke/heat detector", ADMIN, 2, "Corridor A"),
    ("Admin Office Thermostat",           "Central thermostat",            ADMIN, 3, "Open-plan office"),
    ("Admin Corridor Light Sensor",       "Occupancy-linked light sensor", ADMIN, 4, "Corridor B"),
    ("Boardroom Climate Sensor",          "Temperature/humidity sensor",   ADMIN, 6, "Boardroom"),
    ("Admin Visitor Car Park Sensor",     "Parking occupancy sensor",      ADMIN, 1, "Visitor car park"),
    ("Main Gate LPR Camera",              "LPR camera",                    ADMIN, 1, "Vehicle entrance gate"),

    # ---------- Library: study areas, rare books archive ----------
    ("Library Entrance Turnstile Reader", "RFID badge reader",             LIBRARY, 1, "Entrance turnstile"),
    ("Library Entrance CCTV",             "CCTV camera",                   LIBRARY, 1, "Entrance hall"),
    ("Library Smart Meter",               "Smart energy meter",            LIBRARY, 1, "Electrical room"),
    ("Library Car Park Sensor",           "Parking occupancy sensor",      LIBRARY, 1, "Library car park"),
    ("Library Thermostat",                "Central thermostat",            LIBRARY, 2, "Main reading area"),
    ("Library Reading Hall PIR Sensor",   "PIR sensor",                    LIBRARY, 3, "Reading hall"),
    ("Library Stacks Smoke Detector",     "Connected smoke/heat detector", LIBRARY, 3, "Book stacks"),
    ("Library Study Room Light Sensor",   "Occupancy-linked light sensor", LIBRARY, 4, "Group study rooms"),
    ("Library Archive Climate Sensor",    "Temperature/humidity sensor",   LIBRARY, 5, "Rare books archive"),
    ("Library Archive Leak Detector",     "Smart water leak detector",     LIBRARY, 5, "Rare books archive"),

    # ---------- R&D: restricted labs ----------
    ("R&D Entrance Card Reader",          "RFID badge reader",             RND, 1, "Main entrance"),
    ("R&D Smart Meter",                   "Smart energy meter",            RND, 1, "Electrical room"),
    ("R&D Prototype Lab Smart Lock",      "Smart lock",                    RND, 2, "Prototype lab"),
    ("R&D Corridor CCTV",                 "CCTV camera",                   RND, 2, "Corridor"),
    ("R&D Electronics Lab Climate Sensor", "Temperature/humidity sensor",  RND, 2, "Electronics lab"),
    ("R&D Equipment Room Smoke Detector", "Connected smoke/heat detector", RND, 3, "Equipment room"),

    # ---------- IT and Multimedia Services: server room, computer labs ----------
    ("IT Staff Entrance Card Reader",     "RFID badge reader",             IT, 1, "Staff entrance"),
    ("IT Server Room Smart Lock",         "Smart lock",                    IT, 1, "Server room"),
    ("IT Server Room Climate Sensor",     "Temperature/humidity sensor",   IT, 1, "Server room"),
    ("IT Server Room Smoke Detector",     "Connected smoke/heat detector", IT, 1, "Server room"),
    ("IT Corridor CCTV",                  "CCTV camera",                   IT, 2, "Corridor"),
    ("IT Computer Lab Light Sensor",      "Occupancy-linked light sensor", IT, 3, "Computer lab 2"),
    ("IT Multimedia Studio Thermostat",   "Central thermostat",            IT, 4, "Multimedia studio"),

    # ---------- BD Lab (Civil Engineering): teaching labs, heavy equipment ----------
    ("Civil Lab Entrance Card Reader",    "RFID badge reader",             CIVIL, 1, "Main entrance"),
    ("Civil Hydraulics Lab Leak Detector", "Smart water leak detector",    CIVIL, 1, "Hydraulics lab"),
    ("Civil Lab Smart Meter",             "Smart energy meter",            CIVIL, 1, "Heavy equipment bay"),
    ("Civil Materials Store Smart Lock",  "Smart lock",                    CIVIL, 2, "Materials testing store"),
    ("Civil Concrete Lab Smoke Detector", "Connected smoke/heat detector", CIVIL, 2, "Concrete lab"),
    ("Civil Lecture Studio Thermostat",   "Central thermostat",            CIVIL, 3, "Lecture studio"),
    ("Civil Corridor PIR Sensor",         "PIR sensor",                    CIVIL, 3, "Corridor"),
]


def resolve_buildings():
    """
    Maps every building keyword used in DEVICES to the matching building in the
    database. Returns (mapping, ok). Prints a clear message when a keyword does
    not match exactly one building.
    """
    buildings = Building.query.filter_by(is_deleted=False).all()
    mapping = {}
    ok = True

    for keyword in sorted({device[2] for device in DEVICES}):
        matches = [b for b in buildings if keyword.lower() in b.name.lower()]

        if len(matches) == 1:
            mapping[keyword] = matches[0]
            continue

        ok = False
        problem = "matches no building" if not matches else "matches several buildings"
        print(f"Keyword '{keyword}' {problem}.")

    if not ok:
        print("Buildings currently in the database:")
        for b in buildings:
            print(f"  - {b.name} ({b.floor_count} floors)")
        print("Run seed_buildings.py first, or adjust the keywords at the top of this script.")

    return mapping, ok


def seed():
    app = create_app()
    with app.app_context():
        building_by_keyword, ok = resolve_buildings()
        if not ok:
            return  # nothing is created if a building cannot be resolved

        created_count = 0

        for device_name, type_name, building_keyword, floor, zone in DEVICES:
            existing = Device.query.filter_by(name=device_name, is_deleted=False).first()
            if existing is not None:
                continue

            device_type = DeviceType.query.filter_by(name=type_name, is_deleted=False).first()
            if device_type is None:
                print(f"Skipping '{device_name}': device type '{type_name}' not found. "
                      f"Run seed_reference_data.py first.")
                continue

            building = building_by_keyword[building_keyword]

            if floor < 1 or floor > building.floor_count:
                print(f"Skipping '{device_name}': floor {floor} is outside "
                      f"'{building.name}' (1 to {building.floor_count}).")
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