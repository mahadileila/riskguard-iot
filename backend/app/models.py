import uuid
from datetime import datetime, timezone
from app import db


def generate_uuid():
    return str(uuid.uuid4())


class FactorGroup(db.Model):
    __tablename__ = "FACTOR_GROUP"

    id_factor_group = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50), nullable=False)  # 'impact' ou 'likelihood'

    factors = db.relationship("RiskFactor", backref="group", lazy=True)

    def __repr__(self):
        return f"<FactorGroup {self.name}>"


class RiskFactor(db.Model):
    __tablename__ = "RISK_FACTOR"

    id_factor = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    id_factor_group = db.Column(
        db.String(36), db.ForeignKey("FACTOR_GROUP.id_factor_group"), nullable=False
    )

    def __repr__(self):
        return f"<RiskFactor {self.name}>"


class BmsSubsystem(db.Model):
    __tablename__ = "BMS_SUBSYSTEM"

    id_subsystem = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    device_types = db.relationship("DeviceType", backref="subsystem", lazy=True)

    def __repr__(self):
        return f"<BmsSubsystem {self.name}>"


class DeviceType(db.Model):
    __tablename__ = "DEVICE_TYPE"

    id_device_type = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50))
    primary_data_collected = db.Column(db.String(50))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    id_subsystem = db.Column(
        db.String(36), db.ForeignKey("BMS_SUBSYSTEM.id_subsystem"), nullable=False
    )

    devices = db.relationship("Device", backref="device_type", lazy=True)

    def __repr__(self):
        return f"<DeviceType {self.name}>"


class Building(db.Model):
    __tablename__ = "BUILDING"

    id_building = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(100), nullable=False)
    floor_count = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)

    devices = db.relationship("Device", backref="building", lazy=True)

    def __repr__(self):
        return f"<Building {self.name} ({self.floor_count} floors)>"


class Device(db.Model):
    __tablename__ = "DEVICE"

    id_device = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    id_device_type = db.Column(
        db.String(36), db.ForeignKey("DEVICE_TYPE.id_device_type"), nullable=False
    )
    id_building = db.Column(
        db.String(36), db.ForeignKey("BUILDING.id_building"), nullable=True
    )
    floor = db.Column(db.Integer, nullable=True)
    zone = db.Column(db.String(50), nullable=True)

    instances = db.relationship("CollectionInstance", backref="device", lazy=True)
    score_history = db.relationship("RiskScoreHistory", backref="device", lazy=True)

    def __repr__(self):
        return f"<Device {self.name}>"


class CollectionInstance(db.Model):
    __tablename__ = "COLLECTION_INSTANCE"

    id_instance = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    data_description = db.Column(db.String(50))
    id_device = db.Column(db.String(36), db.ForeignKey("DEVICE.id_device"), nullable=False)

    data_nature = db.Column(db.String(30), nullable=False)
    identifiability_level = db.Column(db.String(30), nullable=False)
    location_scope = db.Column(db.String(30), nullable=False)
    collection_frequency = db.Column(db.String(30), nullable=False)
    access_scope = db.Column(db.String(30), nullable=False)
    sharing_scope = db.Column(db.String(30), nullable=False)

    factor_scores = db.relationship("InstanceFactorScore", backref="instance", lazy=True)
    data_samples = db.relationship("DeviceDataSample", backref="instance", lazy=True)

    def __repr__(self):
        return f"<CollectionInstance {self.data_description}>"


class InstanceFactorScore(db.Model):
    __tablename__ = "INSTANCE_FACTOR_SCORE"

    id_instance_factor_score = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    rating = db.Column(db.Integer)  # 0 à 4
    id_instance = db.Column(
        db.String(36), db.ForeignKey("COLLECTION_INSTANCE.id_instance"), nullable=False
    )
    id_factor = db.Column(
        db.String(36), db.ForeignKey("RISK_FACTOR.id_factor"), nullable=False
    )

    factor = db.relationship("RiskFactor")

    def __repr__(self):
        return f"<InstanceFactorScore {self.rating}>"


class DeviceDataSample(db.Model):
    __tablename__ = "DEVICE_DATA_SAMPLE"

    id_sample = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    captured_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    data_value = db.Column(db.String(50))
    id_instance = db.Column(
        db.String(36), db.ForeignKey("COLLECTION_INSTANCE.id_instance"), nullable=False
    )

    def __repr__(self):
        return f"<DeviceDataSample {self.data_value}>"


class RiskScoreHistory(db.Model):
    __tablename__ = "RISK_SCORE_HISTORY"

    id_history = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    score = db.Column(db.Numeric(5, 2), nullable=False)
    classification = db.Column(db.String(20), nullable=False)
    computed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    id_device = db.Column(db.String(36), db.ForeignKey("DEVICE.id_device"), nullable=False)

    def __repr__(self):
        return f"<RiskScoreHistory {self.score} @ {self.computed_at}>"