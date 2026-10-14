from datetime import datetime
from flask import Blueprint, jsonify, request
from app import db
from sqlalchemy import func
from app.services.risk_scoring import CLASSIFICATION_BANDS
from app.services.factor_mapping import compute_factor_ratings, InvalidAttributeError
from functools import wraps
from app.services.auth import verify_admin_credentials, generate_token, decode_token
import jwt as pyjwt

from app.models import (
    Device,
    DeviceType,
    BmsSubsystem,
    Building,
    RiskFactor,
    FactorGroup,
    CollectionInstance,
    InstanceFactorScore,
    DeviceDataSample,
    RiskScoreHistory,
)
from app.services.risk_scoring import (
    compute_device_score,
    compute_instance_score,
    classify_score,
    IncompleteScoringDataError,
)


main = Blueprint("main", __name__)

@main.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400

    if not verify_admin_credentials(data["username"], data["password"]):
        return jsonify({"error": "Invalid username or password"}), 401

    from flask import current_app
    token = generate_token(data["username"], current_app.config["SECRET_KEY"])

    return jsonify({"token": token, "username": data["username"]})

def require_auth(view_function):
    @wraps(view_function)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.removeprefix("Bearer ").strip()

        from flask import current_app
        try:
            decode_token(token, current_app.config["SECRET_KEY"])
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return view_function(*args, **kwargs)
    return wrapper

@main.before_request
def check_authentication():
    # Public endpoints: the login route itself, the root health-check,
    # and CORS preflight requests (which browsers send without headers).
    public_paths = ("/api/auth/login", "/")
    if request.path in public_paths or request.method == "OPTIONS":
        return None

    if not request.path.startswith("/api/"):
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.removeprefix("Bearer ").strip()

    from flask import current_app
    try:
        decode_token(token, current_app.config["SECRET_KEY"])
    except pyjwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except pyjwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

    return None


# ============================================================
# HOME
# ============================================================

@main.route("/")
def index():
    return jsonify({"message": "IoT risk dashboard API is operational"})


def serialize_device(device):
    score, classification = compute_device_score(device.id_device)
    active_count = CollectionInstance.query.filter_by(
        id_device=device.id_device
    ).count()
    building = device.building

    return {
        "id_device": device.id_device,
        "name": device.name,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "id_device_type": device.id_device_type,
        "device_type_name": device.device_type.name if device.device_type else None,
        "subsystem_name": device.device_type.subsystem.name if device.device_type and device.device_type.subsystem else None,
        "active_instances_count": active_count,
        "normalized_score": score,
        "classification": classification,
        "id_building": device.id_building,
        "building_name": building.name if building else None,
        "floor": device.floor,
        "zone": device.zone,
    }


def validate_placement(id_building, floor):
    """Checks that the building exists and that the floor is inside its range.
    Returns (building, floor_number, error_response); error_response is None
    when the placement is valid."""
    building = Building.query.filter_by(id_building=id_building, is_deleted=False).first()
    if building is None:
        return None, None, (jsonify({"error": "Invalid id_building"}), 400)

    try:
        floor_number = int(floor)
    except (TypeError, ValueError):
        return None, None, (jsonify({"error": "Field 'floor' must be a whole number"}), 400)

    if floor_number < 1 or floor_number > building.floor_count:
        return None, None, (jsonify({
            "error": f"Floor must be between 1 and {building.floor_count} for this building"
        }), 400)

    return building, floor_number, None

@main.route("/api/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    devices = Device.query.filter_by(is_deleted=False).all()
    subsystems = BmsSubsystem.query.filter_by(is_deleted=False).all()

    serialized_devices = [serialize_device(d) for d in devices]

    total_devices = len(serialized_devices)
    no_active_collection_count = sum(1 for d in serialized_devices if d["active_instances_count"] == 0)
    high_risk_count = sum(
        1 for d in serialized_devices
        if d["active_instances_count"] > 0 and d["classification"]["label"] == "High"
    )

    # Average score across devices that actually have active collection —
    # a device with "No Risk" (0, no active instance) would otherwise drag
    # the average down artificially for devices that simply aren't collecting.
    scored_devices = [d for d in serialized_devices if d["active_instances_count"] > 0]
    average_score = (
        round(sum(d["normalized_score"] for d in scored_devices) / len(scored_devices), 2)
        if scored_devices else 0.0
    )

    # Risk distribution by subsystem: average score of that subsystem's
    # devices with active collection, classified with the same thresholds
    # used everywhere else in the app.
    risk_by_subsystem = []
    for subsystem in subsystems:
        subsystem_devices = [
            d for d in scored_devices if d["subsystem_name"] == subsystem.name
        ]
        if not subsystem_devices:
            continue

        avg = round(sum(d["normalized_score"] for d in subsystem_devices) / len(subsystem_devices), 2)
        classification = classify_score(avg) if avg > 0 else {"label": "No Risk", "color": "gray"}

        risk_by_subsystem.append({
            "subsystem_name": subsystem.name,
            "average_score": avg,
            "classification": classification
        })

    risk_by_subsystem.sort(key=lambda s: s["average_score"], reverse=True)

    # Devices requiring attention: Medium or High only, highest risk first.
    devices_requiring_attention = sorted(
        [d for d in scored_devices if d["classification"]["label"] in ("Medium", "High")],
        key=lambda d: d["normalized_score"],
        reverse=True
    )

    devices_by_risk = sorted(serialized_devices, key=lambda d: d["normalized_score"], reverse=True)

    return jsonify({
        "total_devices": total_devices,
        "no_active_collection_count": no_active_collection_count,
        "subsystems_count": len(subsystems),
        "high_risk_devices_count": high_risk_count,
        "average_score": average_score,
        "risk_by_subsystem": risk_by_subsystem,
        "devices_requiring_attention": [
            {
                "id_device": d["id_device"],
                "name": d["name"],
                "subsystem_name": d["subsystem_name"],
                "normalized_score": d["normalized_score"],
                "classification": d["classification"],
            }
            for d in devices_requiring_attention
        ],
        "devices_by_risk": [
            {
                "id_device": d["id_device"],
                "name": d["name"],
                "subsystem_name": d["subsystem_name"],
                "active_instances_count": d["active_instances_count"],
                "normalized_score": d["normalized_score"],
                "classification": d["classification"],
            }
            for d in devices_by_risk
        ]
    })

@main.route("/api/dashboard/risk-trend", methods=["GET"])
def get_dashboard_risk_trend():
    results = (
        db.session.query(
            func.date(RiskScoreHistory.computed_at).label("day"),
            func.avg(RiskScoreHistory.score).label("avg_score")
        )
        .join(Device, Device.id_device == RiskScoreHistory.id_device)
        .filter(Device.is_deleted == False)
        .group_by(func.date(RiskScoreHistory.computed_at))
        .order_by(func.date(RiskScoreHistory.computed_at))
        .all()
    )

    return jsonify([
        {"date": row.day, "avg_score": round(float(row.avg_score), 2)}
        for row in results
    ])

@main.route("/api/instances/ingest", methods=["POST"])
def ingest_instance():
    """Simulates receiving a new collection instance from the external
    data-collection system. In production, this is the endpoint that
    system would call with the raw category attributes; here it also
    computes and stores the resulting factor ratings immediately."""
    data = request.get_json()

    required_fields = [
        "id_device", "data_description", "data_nature", "identifiability_level",
        "location_scope", "collection_frequency", "access_scope", "sharing_scope"
    ]
    if not data or any(field not in data for field in required_fields):
        return jsonify({"error": "Required fields: " + ", ".join(required_fields)}), 400

    device = Device.query.filter_by(id_device=data["id_device"], is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Invalid id_device"}), 400

    instance = CollectionInstance(
        data_description=data["data_description"],
        id_device=data["id_device"],
        data_nature=data["data_nature"],
        identifiability_level=data["identifiability_level"],
        location_scope=data["location_scope"],
        collection_frequency=data["collection_frequency"],
        access_scope=data["access_scope"],
        sharing_scope=data["sharing_scope"],
    )
    db.session.add(instance)
    db.session.flush()

    try:
        ratings = compute_factor_ratings(instance)
    except InvalidAttributeError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    factors_by_name = {f.name: f for f in RiskFactor.query.filter_by(is_deleted=False).all()}
    for factor_name, rating in ratings.items():
        factor = factors_by_name.get(factor_name)
        if factor:
            db.session.add(InstanceFactorScore(
                rating=rating,
                id_instance=instance.id_instance,
                id_factor=factor.id_factor,
            ))

    db.session.commit()
    return jsonify({"id_instance": instance.id_instance, "ratings": ratings}), 201

# ============================================================
# SUBSYSTEMS
# ============================================================

@main.route("/api/subsystems", methods=["GET"])
def get_subsystems():
    subsystems = BmsSubsystem.query.filter_by(is_deleted=False).all()
    return jsonify([
        {
            "id_subsystem": s.id_subsystem,
            "name": s.name,
            "linked_device_types_count": len([dt for dt in s.device_types if not dt.is_deleted]),
        }
        for s in subsystems
    ])


@main.route("/api/subsystems/<id_subsystem>", methods=["GET"])
def get_subsystem(id_subsystem):
    subsystem = BmsSubsystem.query.filter_by(id_subsystem=id_subsystem, is_deleted=False).first()
    if subsystem is None:
        return jsonify({"error": "Subsystem not found"}), 404

    return jsonify({
        "id_subsystem": subsystem.id_subsystem,
        "name": subsystem.name,
        "linked_device_types_count": len([dt for dt in subsystem.device_types if not dt.is_deleted]),
    })


@main.route("/api/subsystems", methods=["POST"])
def create_subsystem():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Field 'name' is required"}), 400

    subsystem = BmsSubsystem(name=data["name"], is_deleted=False)
    db.session.add(subsystem)
    db.session.commit()

    return jsonify({"id_subsystem": subsystem.id_subsystem, "name": subsystem.name}), 201


@main.route("/api/subsystems/<id_subsystem>", methods=["PUT"])
def update_subsystem(id_subsystem):
    subsystem = BmsSubsystem.query.filter_by(id_subsystem=id_subsystem, is_deleted=False).first()
    if subsystem is None:
        return jsonify({"error": "Subsystem not found"}), 404

    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Field 'name' is required"}), 400

    subsystem.name = data["name"]
    db.session.commit()

    return jsonify({"id_subsystem": subsystem.id_subsystem, "name": subsystem.name}), 200


@main.route("/api/subsystems/<id_subsystem>", methods=["DELETE"])
def delete_subsystem(id_subsystem):
    subsystem = BmsSubsystem.query.filter_by(id_subsystem=id_subsystem, is_deleted=False).first()
    if subsystem is None:
        return jsonify({"error": "Subsystem not found"}), 404

    active_device_types = [dt for dt in subsystem.device_types if not dt.is_deleted]
    if active_device_types:
        return jsonify({
            "error": f"Cannot delete: {len(active_device_types)} device type(s) are still linked to this subsystem"
        }), 409

    subsystem.is_deleted = True
    db.session.commit()

    return jsonify({"message": "Subsystem deleted"}), 200


# ============================================================
# DEVICE TYPES
# ============================================================

@main.route("/api/device-types", methods=["GET"])
def get_device_types():
    device_types = DeviceType.query.filter_by(is_deleted=False).all()
    return jsonify([
        {
            "id_device_type": dt.id_device_type,
            "name": dt.name,
            "primary_data_collected": dt.primary_data_collected,
            "id_subsystem": dt.id_subsystem,
        }
        for dt in device_types
    ])


@main.route("/api/device-types/<id_device_type>", methods=["GET"])
def get_device_type(id_device_type):
    device_type = DeviceType.query.filter_by(id_device_type=id_device_type, is_deleted=False).first()
    if device_type is None:
        return jsonify({"error": "Device type not found"}), 404

    return jsonify({
        "id_device_type": device_type.id_device_type,
        "name": device_type.name,
        "primary_data_collected": device_type.primary_data_collected,
        "id_subsystem": device_type.id_subsystem,
    })


@main.route("/api/device-types", methods=["POST"])
def create_device_type():
    data = request.get_json()
    if not data or "name" not in data or "id_subsystem" not in data:
        return jsonify({"error": "Fields 'name' and 'id_subsystem' are required"}), 400

    subsystem = BmsSubsystem.query.filter_by(id_subsystem=data["id_subsystem"], is_deleted=False).first()
    if subsystem is None:
        return jsonify({"error": "Invalid id_subsystem"}), 400

    device_type = DeviceType(
        name=data["name"],
        id_subsystem=data["id_subsystem"],
        primary_data_collected=data.get("primary_data_collected"),
        is_deleted=False
    )
    db.session.add(device_type)
    db.session.commit()

    return jsonify({
        "id_device_type": device_type.id_device_type,
        "name": device_type.name,
        "primary_data_collected": device_type.primary_data_collected,
        "id_subsystem": device_type.id_subsystem,
    }), 201


@main.route("/api/device-types/<id_device_type>", methods=["PUT"])
def update_device_type(id_device_type):
    device_type = DeviceType.query.filter_by(id_device_type=id_device_type, is_deleted=False).first()
    if device_type is None:
        return jsonify({"error": "Device type not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "name" in data:
        if not data["name"]:
            return jsonify({"error": "Field 'name' cannot be empty"}), 400
        device_type.name = data["name"]

    if "primary_data_collected" in data:
        device_type.primary_data_collected = data["primary_data_collected"]

    if "id_subsystem" in data:
        subsystem = BmsSubsystem.query.filter_by(id_subsystem=data["id_subsystem"], is_deleted=False).first()
        if subsystem is None:
            return jsonify({"error": "Invalid id_subsystem"}), 400
        device_type.id_subsystem = data["id_subsystem"]

    db.session.commit()

    return jsonify({
        "id_device_type": device_type.id_device_type,
        "name": device_type.name,
        "primary_data_collected": device_type.primary_data_collected,
        "id_subsystem": device_type.id_subsystem,
    }), 200


@main.route("/api/device-types/<id_device_type>", methods=["DELETE"])
def delete_device_type(id_device_type):
    device_type = DeviceType.query.filter_by(id_device_type=id_device_type, is_deleted=False).first()
    if device_type is None:
        return jsonify({"error": "Device type not found"}), 404

    active_devices = Device.query.filter_by(id_device_type=id_device_type, is_deleted=False).all()
    if active_devices:
        return jsonify({
            "error": f"Cannot delete: {len(active_devices)} device(s) are still linked to this device type"
        }), 409

    device_type.is_deleted = True
    db.session.commit()

    return jsonify({"message": "Device type deleted"}), 200


# ============================================================
# DEVICES
# ============================================================

@main.route("/api/devices", methods=["GET"])
def get_devices():
    devices = Device.query.filter_by(is_deleted=False).all()
    return jsonify([serialize_device(d) for d in devices])


@main.route("/api/devices/<string:id_device>", methods=["GET"])
def get_device(id_device):
    device = Device.query.filter_by(id_device=id_device, is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    return jsonify(serialize_device(device))


@main.route("/api/devices", methods=["POST"])
def create_device():
    data = request.get_json()
    if not data or "name" not in data or "id_device_type" not in data:
        return jsonify({"error": "Fields 'name' and 'id_device_type' are required"}), 400

    device_type = DeviceType.query.filter_by(id_device_type=data["id_device_type"], is_deleted=False).first()
    if device_type is None:
        return jsonify({"error": "Invalid id_device_type"}), 400

    if not data.get("id_building") or data.get("floor") in (None, ""):
        return jsonify({"error": "Fields 'id_building' and 'floor' are required"}), 400

    building, floor_number, error = validate_placement(data["id_building"], data["floor"])
    if error:
        return error

    device = Device(
        name=data["name"],
        id_device_type=data["id_device_type"],
        created_at=datetime.utcnow(),
        is_deleted=False,
        id_building=building.id_building,
        floor=floor_number,
        zone=(data.get("zone") or "").strip() or None,
    )
    db.session.add(device)
    db.session.commit()

    return jsonify(serialize_device(device)), 201


@main.route("/api/devices/<string:id_device>", methods=["PUT"])
def update_device(id_device):
    device = Device.query.filter_by(id_device=id_device, is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "name" in data:
        if not data["name"]:
            return jsonify({"error": "Field 'name' cannot be empty"}), 400
        device.name = data["name"]

    if "id_device_type" in data:
        device_type = DeviceType.query.filter_by(id_device_type=data["id_device_type"], is_deleted=False).first()
        if device_type is None:
            return jsonify({"error": "Invalid id_device_type"}), 400
        device.id_device_type = data["id_device_type"]

    if "id_building" in data or "floor" in data:
        new_building_id = data.get("id_building", device.id_building)
        new_floor = data.get("floor", device.floor)
        building, floor_number, error = validate_placement(new_building_id, new_floor)
        if error:
            return error
        device.id_building = building.id_building
        device.floor = floor_number

    if "zone" in data:
        device.zone = (data["zone"] or "").strip() or None

    db.session.commit()

    return jsonify(serialize_device(device)), 200


@main.route("/api/devices/<string:id_device>", methods=["DELETE"])
def delete_device(id_device):
    device = Device.query.filter_by(id_device=id_device, is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    device.is_deleted = True
    db.session.commit()

    return jsonify({"message": "Device deleted"}), 200


@main.route("/api/devices/<id_device>/risk-score", methods=["GET"])
def get_device_risk_score(id_device):
    device = Device.query.filter_by(id_device=id_device, is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    score, classification = compute_device_score(id_device)

    return jsonify({
        "id_device": id_device,
        "normalized_score": score,
        "classification": classification
    })


@main.route("/api/devices/<id_device>/instances", methods=["GET"])
def get_device_instances(id_device):
    device = Device.query.filter_by(id_device=id_device, is_deleted=False).first()
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    instances = CollectionInstance.query.filter_by(id_device=id_device).all()

    result = []
    for instance in instances:
        try:
            score = compute_instance_score(instance.id_instance)
            classification = classify_score(score)
        except IncompleteScoringDataError:
            score = None
            classification = None

        ratings = InstanceFactorScore.query.filter_by(id_instance=instance.id_instance).all()
        samples = DeviceDataSample.query.filter_by(
            id_instance=instance.id_instance
        ).order_by(DeviceDataSample.captured_at.desc()).all()

        result.append({
            "id_instance": instance.id_instance,
            "data_description": instance.data_description,
            "normalized_score": score,
            "classification": classification,
            "raw_attributes": {
                "data_nature": instance.data_nature,
                "identifiability_level": instance.identifiability_level,
                "location_scope": instance.location_scope,
                "collection_frequency": instance.collection_frequency,
                "access_scope": instance.access_scope,
                "sharing_scope": instance.sharing_scope,
            },
            "factor_ratings": [
                {"factor_name": r.factor.name, "rating": r.rating}
                for r in ratings
            ],
            "data_samples": [
                {"data_value": s.data_value, "captured_at": s.captured_at.isoformat() if s.captured_at else None}
                for s in samples
            ]
        })

    return jsonify(result)


# ============================================================
# BUILDINGS
# ============================================================

def parse_floor_count(value):
    """Returns (floor_count, error_message). A building has 1 to 200 floors."""
    try:
        floor_count = int(value)
    except (TypeError, ValueError):
        return None, "Field 'floor_count' must be a whole number"
    if floor_count < 1 or floor_count > 200:
        return None, "Field 'floor_count' must be between 1 and 200"
    return floor_count, None


def serialize_building(building):
    return {
        "id_building": building.id_building,
        "name": building.name,
        "floor_count": building.floor_count,
        "devices_count": len([d for d in building.devices if not d.is_deleted]),
    }


@main.route("/api/buildings", methods=["GET"])
def get_buildings():
    buildings = Building.query.filter_by(is_deleted=False).order_by(Building.name).all()
    return jsonify([serialize_building(b) for b in buildings])


@main.route("/api/buildings/<id_building>", methods=["GET"])
def get_building(id_building):
    building = Building.query.filter_by(id_building=id_building, is_deleted=False).first()
    if building is None:
        return jsonify({"error": "Building not found"}), 404

    return jsonify(serialize_building(building))


@main.route("/api/buildings", methods=["POST"])
def create_building():
    data = request.get_json()
    if not data or not str(data.get("name", "")).strip() or data.get("floor_count") in (None, ""):
        return jsonify({"error": "Fields 'name' and 'floor_count' are required"}), 400

    floor_count, error = parse_floor_count(data["floor_count"])
    if error:
        return jsonify({"error": error}), 400

    building = Building(name=data["name"].strip(), floor_count=floor_count, is_deleted=False)
    db.session.add(building)
    db.session.commit()

    return jsonify(serialize_building(building)), 201


@main.route("/api/buildings/<id_building>", methods=["PUT"])
def update_building(id_building):
    building = Building.query.filter_by(id_building=id_building, is_deleted=False).first()
    if building is None:
        return jsonify({"error": "Building not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "name" in data:
        if not str(data["name"]).strip():
            return jsonify({"error": "Field 'name' cannot be empty"}), 400
        building.name = data["name"].strip()

    if "floor_count" in data:
        floor_count, error = parse_floor_count(data["floor_count"])
        if error:
            return jsonify({"error": error}), 400

        # Never remove a floor that still hosts devices.
        highest_used_floor = max(
            (d.floor for d in building.devices if not d.is_deleted and d.floor is not None),
            default=0,
        )
        if floor_count < highest_used_floor:
            return jsonify({
                "error": f"Cannot reduce to {floor_count} floor(s): devices are still located on floor {highest_used_floor}"
            }), 409

        building.floor_count = floor_count

    db.session.commit()

    return jsonify(serialize_building(building)), 200


@main.route("/api/buildings/<id_building>", methods=["DELETE"])
def delete_building(id_building):
    building = Building.query.filter_by(id_building=id_building, is_deleted=False).first()
    if building is None:
        return jsonify({"error": "Building not found"}), 404

    active_devices = [d for d in building.devices if not d.is_deleted]
    if active_devices:
        return jsonify({
            "error": f"Cannot delete: {len(active_devices)} device(s) are still located in this building"
        }), 409

    building.is_deleted = True
    db.session.commit()

    return jsonify({"message": "Building deleted"}), 200


# ============================================================
# RISK FACTORS
# ============================================================

@main.route("/api/risk-factors", methods=["GET"])
def get_risk_factors():
    factors = RiskFactor.query.filter_by(is_deleted=False).all()
    return jsonify([
        {
            "id_factor": f.id_factor,
            "name": f.name,
            "id_factor_group": f.id_factor_group,
            "group_name": f.group.name if f.group else None,
        }
        for f in factors
    ])


@main.route("/api/risk-factors/<id_factor>", methods=["GET"])
def get_risk_factor(id_factor):
    factor = RiskFactor.query.filter_by(id_factor=id_factor, is_deleted=False).first()
    if factor is None:
        return jsonify({"error": "Risk factor not found"}), 404

    return jsonify({
        "id_factor": factor.id_factor,
        "name": factor.name,
        "id_factor_group": factor.id_factor_group,
        "group_name": factor.group.name if factor.group else None,
    })


@main.route("/api/risk-factors", methods=["POST"])
def create_risk_factor():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("id_factor_group"):
        return jsonify({"error": "Fields 'name' and 'id_factor_group' are required"}), 400

    group = FactorGroup.query.filter_by(id_factor_group=data["id_factor_group"]).first()
    if group is None:
        return jsonify({"error": "Invalid id_factor_group"}), 400

    factor = RiskFactor(name=data["name"], id_factor_group=data["id_factor_group"], is_deleted=False)
    db.session.add(factor)
    db.session.commit()

    return jsonify({
        "id_factor": factor.id_factor,
        "name": factor.name,
        "id_factor_group": factor.id_factor_group,
    }), 201


@main.route("/api/risk-factors/<id_factor>", methods=["PUT"])
def update_risk_factor(id_factor):
    factor = RiskFactor.query.filter_by(id_factor=id_factor, is_deleted=False).first()
    if factor is None:
        return jsonify({"error": "Risk factor not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    if "name" in data:
        if not data["name"]:
            return jsonify({"error": "Field 'name' cannot be empty"}), 400
        factor.name = data["name"]

    if "id_factor_group" in data:
        group = FactorGroup.query.filter_by(id_factor_group=data["id_factor_group"]).first()
        if group is None:
            return jsonify({"error": "Invalid id_factor_group"}), 400
        factor.id_factor_group = data["id_factor_group"]

    db.session.commit()

    return jsonify({
        "id_factor": factor.id_factor,
        "name": factor.name,
        "id_factor_group": factor.id_factor_group,
    }), 200


@main.route("/api/risk-factors/<id_factor>", methods=["DELETE"])
def delete_risk_factor(id_factor):
    factor = RiskFactor.query.filter_by(id_factor=id_factor, is_deleted=False).first()
    if factor is None:
        return jsonify({"error": "Risk factor not found"}), 404

    linked_scores = InstanceFactorScore.query.filter_by(id_factor=id_factor).count()
    if linked_scores > 0:
        return jsonify({
            "error": f"Cannot delete: {linked_scores} instance factor score(s) are still linked to this risk factor"
        }), 409

    factor.is_deleted = True
    db.session.commit()

    return jsonify({"message": "Risk factor deleted"}), 200


# ============================================================
# FACTOR GROUPS (read-only reference list)
# ============================================================

@main.route("/api/factor-groups", methods=["GET"])
def get_factor_groups():
    groups = FactorGroup.query.all()
    return jsonify([{"id_factor_group": g.id_factor_group, "name": g.name} for g in groups])


# ============================================================
# DEVICE DATA SAMPLES (read-only)
# ============================================================

@main.route("/api/instances/<id_instance>/data-samples", methods=["GET"])
def get_instance_data_samples(id_instance):
    samples = DeviceDataSample.query.filter_by(id_instance=id_instance).all()
    return jsonify([
        {
            "id_sample": s.id_sample,
            "captured_at": s.captured_at.isoformat() if s.captured_at else None,
            "data_value": s.data_value,
            "id_instance": s.id_instance,
        }
        for s in samples
    ])

# ============================================================
# RISK CLASSIFICATIONS (read-only reference list)
# ============================================================

@main.route("/api/risk-classifications", methods=["GET"])
def get_risk_classifications():
    bands = []
    for low, high, label, color in CLASSIFICATION_BANDS:
        bands.append({
            "label": label,
            "min_score": low,
            "max_score": high,
            "color": color,
            "description": None
        })
    return jsonify(bands)