export interface RiskLabel {
  label: string;
  color: string;
}

export interface DashboardDeviceSummary {
  id_device: string;
  name: string;
  subsystem_name: string | null;
  active_instances_count?: number;
  normalized_score: number;
  classification: RiskLabel;
}

export interface SubsystemRisk {
  subsystem_name: string;
  average_score: number;
  classification: RiskLabel;
}

export interface DashboardSummary {
  total_devices: number;
  no_active_collection_count: number;
  subsystems_count: number;
  high_risk_devices_count: number;
  average_score: number;
  risk_by_subsystem: SubsystemRisk[];
  devices_requiring_attention: DashboardDeviceSummary[];
  devices_by_risk: DashboardDeviceSummary[];
}

export interface RiskTrendPoint {
  date: string;
  avg_score: number;
}

// Shape of GET /api/devices (only the fields the dashboard needs)
export interface DashboardDevice {
  id_device: string;
  name: string;
  subsystem_name: string | null;
  active_instances_count: number;
  normalized_score: number;
  classification: RiskLabel;
  id_building: string | null;
  building_name: string | null;
  floor: number | null;
  zone: string | null;
}

export interface DashboardBuilding {
  id_building: string;
  name: string;
  floor_count: number;
}

export interface ScoreHistoryPoint {
  id_device: string;
  date: string;
  score: number;
}