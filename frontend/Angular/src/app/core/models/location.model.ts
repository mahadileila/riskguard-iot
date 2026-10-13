export interface Building {
  id_building: string;
  name: string;
  locations_count?: number;
}

export interface Location {
  id_location: string;
  id_building: string;
  building_name: string;
  floor: string;
  zone: string | null;
  label: string;
}