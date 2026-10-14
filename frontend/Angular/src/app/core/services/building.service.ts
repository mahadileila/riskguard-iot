import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Building } from '../models/building.model';

@Injectable({ providedIn: 'root' })
export class BuildingService {
  constructor(private api: ApiService) {}

  getBuildings() {
    return this.api.get<Building[]>('/buildings');
  }

  createBuilding(payload: { name: string; floor_count: number }) {
    return this.api.post<Building>('/buildings', payload);
  }

  updateBuilding(id: string, payload: { name: string; floor_count: number }) {
    return this.api.put<Building>(`/buildings/${id}`, payload);
  }

  deleteBuilding(id: string) {
    return this.api.delete<unknown>(`/buildings/${id}`);
  }
}