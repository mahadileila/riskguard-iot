import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Building, Location } from '../models/location.model';

@Injectable({ providedIn: 'root' })
export class LocationService {
  constructor(private api: ApiService) {}

  getBuildings() { return this.api.get<Building[]>('/buildings'); }
  createBuilding(payload: { name: string }) { return this.api.post<Building>('/buildings', payload); }
  updateBuilding(id: string, payload: { name: string }) { return this.api.put<Building>(`/buildings/${id}`, payload); }
  deleteBuilding(id: string) { return this.api.delete<unknown>(`/buildings/${id}`); }

  getLocations(idBuilding?: string) {
    return this.api.get<Location[]>(idBuilding ? `/locations?id_building=${idBuilding}` : '/locations');
  }
  createLocation(payload: { id_building: string; floor: string; zone: string | null }) {
    return this.api.post<Location>('/locations', payload);
  }
  updateLocation(id: string, payload: { floor: string; zone: string | null }) {
    return this.api.put<Location>(`/locations/${id}`, payload);
  }
  deleteLocation(id: string) { return this.api.delete<unknown>(`/locations/${id}`); }
}