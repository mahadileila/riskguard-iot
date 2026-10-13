export interface Device {
  id_device: string;
  name: string;
  created_at: string;
  id_device_type: string;
  device_type_name: string | null;
  subsystem_name: string | null;
  active_instances_count: number;
  normalized_score: number;
  classification: { label: string; color: string };
  id_location: string | null;
  id_building: string | null;
  building_name: string | null;
  floor: string | null;
  zone: string | null;
}