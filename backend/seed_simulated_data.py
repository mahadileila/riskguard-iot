"""
Generates simulated collection instances and data samples for every device
that has none yet.

Raw attributes (nature of data, identifiability, location scope, collection
frequency, access scope, sharing scope) come from a profile per kind of data,
optionally adjusted per device in DEVICE_OVERRIDES. Factor ratings are then
computed by compute_factor_ratings(), the same function a real ingestion
route would use.

Run order:
    1. seed_reference_data.py 
    2. seed_buildings.py    
    3. seed_devices.py
    4. seed_simulated_data.py (this script) 
    5. seed_score_history.py

Run after seed_devices.py:
    docker compose exec backend python seed_simulated_data.py
"""
import random
from datetime import datetime, timedelta, timezone
from app import create_app, db
from app.models import Device, CollectionInstance, InstanceFactorScore, RiskFactor, DeviceDataSample
from app.services.factor_mapping import compute_factor_ratings, InvalidAttributeError

ATTRIBUTE_NAMES = (
    "data_nature", "identifiability_level", "location_scope",
    "collection_frequency", "access_scope", "sharing_scope",
)

# Keyword found in the data point name -> values in ATTRIBUTE_NAMES order
_PROFILES = {
    "temperature":             ("environmental", "cannot_link", "room_zone", "frequent", "small_team", "not_shared"),
    "humidity":                ("environmental", "cannot_link", "room_zone", "frequent", "small_team", "not_shared"),
    "inferred presence":       ("behavioural", "cannot_link", "room_zone", "frequent", "small_team", "not_shared"),
    "presence":                ("behavioural", "cannot_link", "room_zone", "frequent", "small_team", "not_shared"),
    "zone occupancy":          ("behavioural", "cannot_link", "room_zone", "frequent", "small_team", "not_shared"),
    "vehicle presence":        ("behavioural", "cannot_link", "room_zone", "periodic", "small_team", "not_shared"),
    "identity":                ("behavioural_contextual", "direct", "room_zone", "periodic", "defined_group", "internal_services"),
    "access timestamps":       ("behavioural", "additional_information", "room_zone", "periodic", "defined_group", "same_subsystem"),
    "video/image":             ("identity_biometric", "direct", "room_zone_over_time", "continuous", "defined_group", "external_partner_contract"),
    "plate identifier":        ("identity_biometric", "direct", "room_zone", "periodic", "defined_group", "external_partner_contract"),
    "environmental data":      ("environmental", "cannot_link", "room_zone", "occasional", "key_personnel", "same_subsystem"),
    "event location":          ("environmental", "cannot_link", "room_zone", "occasional", "key_personnel", "same_subsystem"),
    "electricity consumption": ("non_personal_usage", "significant_effort", "building_level", "continuous", "small_team", "external_partner_contract"),
    "water consumption":       ("non_personal_usage", "cannot_link", "building_level", "weekly_several", "small_team", "not_shared"),
    "indoor localisation":     ("behavioural", "cannot_link", "room_zone_over_time", "frequent", "small_team", "not_shared"),
}

RAW_ATTRIBUTE_PROFILES = {
    keyword: dict(zip(ATTRIBUTE_NAMES, values)) for keyword, values in _PROFILES.items()
}

DEFAULT_ATTRIBUTES = dict(zip(
    ATTRIBUTE_NAMES,
    ("non_personal_usage", "significant_effort", "building_level", "periodic", "small_team", "not_shared"),
))

# Only deployment-related attributes can differ between two devices of the
# same type; what the data is (nature, identifiability) never changes.
CONTEXTUAL_ATTRIBUTES = ("location_scope", "collection_frequency", "access_scope", "sharing_scope")

# Device name (as created by seed_devices.py) -> attributes that differ from the profile
DEVICE_OVERRIDES = {
    # Library
    "Library Entrance CCTV":             {"sharing_scope": "same_subsystem"},
    "Library Archive Climate Sensor":    {"access_scope": "key_personnel"},
    "Library Archive Leak Detector":     {"access_scope": "key_personnel"},
    # Admin Building
    "Registrar Records Room Smart Lock": {"access_scope": "key_personnel"},
    # R&D
    "R&D Entrance Card Reader":          {"access_scope": "key_personnel"},
    "R&D Prototype Lab Smart Lock":      {"access_scope": "key_personnel", "sharing_scope": "not_shared"},
    "R&D Corridor CCTV":                 {"access_scope": "key_personnel", "sharing_scope": "not_shared"},
    "R&D Smart Meter":                   {"sharing_scope": "internal_services"},
    # IT and Multimedia Services
    "IT Server Room Smart Lock":         {"access_scope": "key_personnel", "sharing_scope": "not_shared"},
    "IT Server Room Climate Sensor":     {"access_scope": "key_personnel"},
    "IT Corridor CCTV":                  {"sharing_scope": "same_subsystem"},
    # BD Lab (Civil Engineering)
    "Civil Lab Smart Meter":             {"sharing_scope": "internal_services"},
    "Civil Corridor PIR Sensor":         {"collection_frequency": "periodic"},
}

KNOWN_VALUES = {
    attribute: {p[attribute] for p in [*RAW_ATTRIBUTE_PROFILES.values(), DEFAULT_ATTRIBUTES]}
    for attribute in CONTEXTUAL_ATTRIBUTES
}

# collection_frequency -> (window in days, spacing in minutes, sample count range)
FREQUENCY_TO_SAMPLING = {
    "occasional":     (30, None, (1, 2)),
    "weekly_several": (14, 60 * 24 * 2, (4, 6)),
    "periodic":       (3, 60 * 5, (6, 10)),
    "frequent":       (1, 60, (12, 20)),
    "continuous":     (0.25, 10, (10, 15)),
}


def validate_overrides():
    for device_name, overrides in DEVICE_OVERRIDES.items():
        for attribute, value in overrides.items():
            if attribute not in CONTEXTUAL_ATTRIBUTES:
                raise ValueError(f"'{device_name}': '{attribute}' cannot be overridden.")
            if value not in KNOWN_VALUES[attribute]:
                raise ValueError(f"'{device_name}': unknown value '{value}' for '{attribute}'.")


def attributes_for(data_point: str, device_name: str) -> dict:
    key = data_point.lower()
    attributes = dict(DEFAULT_ATTRIBUTES)

    for keyword, profile in RAW_ATTRIBUTE_PROFILES.items():
        if keyword in key:
            attributes = dict(profile)
            break

    attributes.update(DEVICE_OVERRIDES.get(device_name, {}))
    return attributes


def value_generator_for(data_point: str):
    key = data_point.lower()

    if "temperature" in key:
        return lambda: f"{round(random.uniform(18, 26), 1)}°C"
    if "humidity" in key:
        return lambda: f"{round(random.uniform(30, 60), 1)}%"
    if "video" in key or "image" in key:
        return lambda: "1 frame captured"
    if "presence" in key or "occupancy" in key or "localisation" in key:
        return lambda: random.choice(["Occupied", "Vacant"])
    if "identity" in key or "access timestamps" in key:
        return lambda: f"Badge #{random.randint(1000, 9999)}"
    if "plate identifier" in key:
        return lambda: f"Plate {random.choice('ABCDEFGH')}{random.randint(100, 999)}"
    if "electricity" in key:
        return lambda: f"{round(random.uniform(0.1, 3.5), 2)} kWh"
    if "water" in key:
        return lambda: f"{round(random.uniform(0.5, 8.0), 2)} L"
    if "environmental" in key:
        return lambda: f"{round(random.uniform(15, 30), 1)}°C ambient"
    if "event location" in key:
        return lambda: random.choice(["Zone A", "Zone B", "Zone C"])

    return lambda: "N/A"


def instances_for_device_type(device_type):
    raw = device_type.primary_data_collected or "General data"
    points = [p.strip() for p in raw.split(",") if p.strip()]
    return points if points else ["General data"]


def generate_samples(instance, data_point, collection_frequency: str):
    value_generator = value_generator_for(data_point)
    window_days, spacing_minutes, count_range = FREQUENCY_TO_SAMPLING[collection_frequency]
    window_minutes = window_days * 24 * 60

    for _ in range(random.randint(*count_range)):
        if spacing_minutes is None:
            minutes_ago = random.randint(0, int(window_minutes))
        else:
            steps = random.randint(0, int(window_minutes // max(1, spacing_minutes)))
            jitter = random.randint(-spacing_minutes // 3, spacing_minutes // 3)
            minutes_ago = min(int(window_minutes), max(0, steps * spacing_minutes + jitter))

        db.session.add(DeviceDataSample(
            data_value=value_generator(),
            captured_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
            id_instance=instance.id_instance,
        ))


def seed():
    validate_overrides()

    app = create_app()
    with app.app_context():
        factors_by_name = {f.name: f for f in RiskFactor.query.filter_by(is_deleted=False).all()}
        if len(factors_by_name) != 7:
            print(f"Expected 7 RiskFactor rows, found {len(factors_by_name)}. Run seed_reference_data.py first.")
            return

        devices = Device.query.filter_by(is_deleted=False).all()

        known_device_names = {d.name for d in devices}
        for name in DEVICE_OVERRIDES:
            if name not in known_device_names:
                print(f"Warning: override defined for '{name}' but no such device exists.")

        for device in devices:
            if CollectionInstance.query.filter_by(id_device=device.id_device).count() > 0:
                continue
            if device.device_type is None:
                continue

            for data_point in instances_for_device_type(device.device_type):
                attributes = attributes_for(data_point, device.name)

                instance = CollectionInstance(
                    data_description=data_point,
                    id_device=device.id_device,
                    **{name: attributes[name] for name in ATTRIBUTE_NAMES},
                )
                db.session.add(instance)
                db.session.flush()

                try:
                    ratings = compute_factor_ratings(instance)
                except InvalidAttributeError as e:
                    print(f"Skipping instance '{data_point}' on device '{device.name}': {e}")
                    db.session.rollback()
                    continue

                for factor_name, rating in ratings.items():
                    factor = factors_by_name.get(factor_name)
                    if factor:
                        db.session.add(InstanceFactorScore(
                            rating=rating,
                            id_instance=instance.id_instance,
                            id_factor=factor.id_factor,
                        ))

                generate_samples(instance, data_point, attributes["collection_frequency"])

        db.session.commit()
        print("Simulated collection instances, factor ratings, and data samples seeded.")


if __name__ == "__main__":
    seed()