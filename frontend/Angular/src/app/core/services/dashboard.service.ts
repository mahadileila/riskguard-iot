import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import {
  DashboardSummary,
  RiskTrendPoint,
  DashboardDevice,
  DashboardBuilding,
  ScoreHistoryPoint,
} from '../models/dashboard.model';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  constructor(private api: ApiService) {}

  getSummary() {
    return this.api.get<DashboardSummary>('/dashboard/summary');
  }

  getRiskTrend() {
    return this.api.get<RiskTrendPoint[]>('/dashboard/risk-trend');
  }

  // New: the dashboard now filters client-side, so it needs the raw lists.
  getDevices() {
    return this.api.get<DashboardDevice[]>('/devices');
  }

  getBuildings() {
    return this.api.get<DashboardBuilding[]>('/buildings');
  }

  getScoreHistory() {
    return this.api.get<ScoreHistoryPoint[]>('/dashboard/score-history');
  }
}