import { Component, OnInit, OnDestroy, ChangeDetectorRef, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Chart, registerables } from 'chart.js';
import { DashboardService } from '../../../core/services/dashboard.service';
import { DashboardBuilding, DashboardDevice, RiskLabel, ScoreHistoryPoint } from '../../../core/models/dashboard.model';
import { FilterComboBox, FilterOption } from '../../../shared/components/filter-combo-box/filter-combo-box';

Chart.register(...registerables);

const UNASSIGNED = 'unassigned';

const COLOR_HEX: Record<string, string> = {
  green: '#16a34a',
  orange: '#f59e0b',
  red: '#dc2626',
  gray: '#9ca3af',
};

type TrendRange = '30d' | '12m';

interface BuildingRow {
  id: string;
  name: string;
  deviceCount: number;
  average: number | null;
  classification: RiskLabel | null;
}

interface FloorRow {
  floor: number;
  deviceCount: number;
  average: number | null;
  classification: RiskLabel | null;
}

interface SubsystemRow {
  name: string;
  average: number;
  classification: RiskLabel;
}

interface TrendPoint {
  label: string;
  average: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FilterComboBox],
  templateUrl: './dashboard.html'
})
export class Dashboard implements OnInit, OnDestroy {
  @ViewChild('subsystemChartCanvas') subsystemChartCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('trendChartCanvas') trendChartCanvas?: ElementRef<HTMLCanvasElement>;

  // Raw data (loaded once)
  devices: DashboardDevice[] = [];
  buildings: DashboardBuilding[] = [];
  history: ScoreHistoryPoint[] = [];

  loading = true;
  error: string | null = null;

  // Filters
  selectedBuildingId: string | null = null;
  selectedFloor: number | null = null;
  onlyAtRisk = true;
  trendRange: TrendRange = '30d';

  // Derived data (recomputed whenever a filter changes)
  totalDevices = 0;
  highRiskCount = 0;
  attentionCount = 0;
  averageScore = 0;
  averageClassification: RiskLabel | null = null;
  buildingRows: BuildingRow[] = [];
  floorRows: FloorRow[] = [];        // top floor first (building cross-section)
  floorRowsAsc: FloorRow[] = [];     // ground first (filter dropdown)
  subsystemRows: SubsystemRow[] = [];
  trendPoints: TrendPoint[] = [];
  visibleDevices: DashboardDevice[] = [];

  // Options for the dropdown filters
  buildingOptions: FilterOption[] = [];
  floorOptions: FilterOption[] = [];

  private filteredDevices: DashboardDevice[] = [];
  private chart: Chart | null = null;
  private trendChart: Chart | null = null;

  constructor(
    private dashboardService: DashboardService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    forkJoin({
      devices: this.dashboardService.getDevices(),
      buildings: this.dashboardService.getBuildings(),
      history: this.dashboardService.getScoreHistory().pipe(
        catchError(() => of([] as ScoreHistoryPoint[]))
      ),
    }).subscribe({
      next: ({ devices, buildings, history }) => {
        this.devices = devices;
        this.buildings = buildings;
        this.history = history;
        this.recompute();
        this.loading = false;
        this.cdr.detectChanges();
        this.updateChart();
        this.updateTrendChart();
      },
      error: () => {
        this.error = 'Unable to load dashboard data.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  ngOnDestroy() {
    this.chart?.destroy();
    this.trendChart?.destroy();
  }

  // ---------- Filter actions ----------

  selectBuilding(id: string | null) {
    this.selectedBuildingId = id;
    this.selectedFloor = null;
    this.refresh();
  }

  // Used by the floor cross-section: clicking the active floor again clears it
  selectFloor(floor: number | null) {
    this.selectedFloor = this.selectedFloor === floor ? null : floor;
    this.refresh();
  }

  // Used by the floor dropdown: direct selection (value is a string or null)
  onFloorSelected(value: string | null) {
    this.selectedFloor = value === null ? null : Number(value);
    this.refresh();
  }

  clearFilters() {
    this.selectedBuildingId = null;
    this.selectedFloor = null;
    this.refresh();
  }

  setOnlyAtRisk(value: boolean) {
    this.onlyAtRisk = value;
    this.refresh();
  }

  setTrendRange(range: TrendRange) {
    this.trendRange = range;
    this.refresh();
  }

  private refresh() {
    this.recompute();
    this.cdr.detectChanges();
    this.updateChart();
    this.updateTrendChart();
  }

  // ---------- Template helpers ----------

  get hasActiveFilter(): boolean {
    return this.selectedBuildingId !== null || this.selectedFloor !== null;
  }

  get selectedBuilding(): DashboardBuilding | null {
    return this.buildings.find(b => b.id_building === this.selectedBuildingId) ?? null;
  }

  get selectedFloorValue(): string | null {
    return this.selectedFloor === null ? null : String(this.selectedFloor);
  }

  get scopeLabel(): string {
    if (this.selectedBuildingId === UNASSIGNED) return 'Unassigned devices';
    const building = this.selectedBuilding;
    if (!building) return 'All buildings';
    return this.selectedFloor === null
      ? building.name
      : `${building.name} · ${this.floorLabel(this.selectedFloor)}`;
  }

  get hasUnassigned(): boolean {
    return this.buildingRows.some(b => b.id === UNASSIGNED);
  }

  floorLabel(floor: number): string {
    if (floor === 0) return 'Ground floor';
    if (floor < 0) return `Basement ${Math.abs(floor)}`;
    return `Floor ${floor}`;
  }

  floorShort(floor: number): string {
    if (floor === 0) return 'G';
    if (floor < 0) return `B${Math.abs(floor)}`;
    return String(floor);
  }

  locationLabel(d: DashboardDevice): string {
    if (!d.building_name) return 'Unassigned';
    const parts = [d.building_name];
    if (d.floor !== null) parts.push(this.floorLabel(d.floor));
    if (d.zone) parts.push(d.zone);
    return parts.join(' · ');
  }

  hex(color?: string | null): string {
    return COLOR_HEX[color ?? ''] ?? COLOR_HEX['gray'];
  }

  badgeClass(label?: string | null): string {
    switch (label) {
      case 'High':   return 'bg-red-50 text-red-700 ring-red-600/20';
      case 'Medium': return 'bg-amber-50 text-amber-700 ring-amber-600/20';
      case 'Low':    return 'bg-green-50 text-green-700 ring-green-600/20';
      default:       return 'bg-gray-100 text-gray-600 ring-gray-500/20';
    }
  }

  // ---------- Computation (all client-side, instant) ----------

  private matches(d: DashboardDevice, buildingId: string | null, floor: number | null): boolean {
    let inBuilding = true;
    if (buildingId === UNASSIGNED) inBuilding = d.id_building === null;
    else if (buildingId) inBuilding = d.id_building === buildingId;
    return inBuilding && (floor === null || d.floor === floor);
  }

  private isScored(d: DashboardDevice): boolean {
    return d.active_instances_count > 0;
  }

  private average(devices: DashboardDevice[]): number | null {
    const scored = devices.filter(d => this.isScored(d));
    if (scored.length === 0) return null;
    const sum = scored.reduce((acc, d) => acc + d.normalized_score, 0);
    return Math.round((sum / scored.length) * 100) / 100;
  }

  // Same thresholds as the backend classification bands.
  private classify(average: number | null): RiskLabel | null {
    if (average === null) return null;
    if (average <= 0) return { label: 'No Risk', color: 'gray' };
    if (average < 34) return { label: 'Low', color: 'green' };
    if (average < 67) return { label: 'Medium', color: 'orange' };
    return { label: 'High', color: 'red' };
  }

  private recompute() {
    this.filteredDevices = this.devices.filter(d =>
      this.matches(d, this.selectedBuildingId, this.selectedFloor)
    );
    const scored = this.filteredDevices.filter(d => this.isScored(d));

    // KPI cards
    this.totalDevices = this.filteredDevices.length;
    this.highRiskCount = scored.filter(d => d.classification.label === 'High').length;
    this.attentionCount = scored.filter(d => ['Medium', 'High'].includes(d.classification.label)).length;
    const avg = this.average(this.filteredDevices);
    this.averageScore = avg ?? 0;
    this.averageClassification = this.classify(avg);

    // Risk by subsystem (current selection)
    const bySubsystem = new Map<string, DashboardDevice[]>();
    for (const d of scored) {
      const key = d.subsystem_name ?? 'Unknown';
      bySubsystem.set(key, [...(bySubsystem.get(key) ?? []), d]);
    }
    this.subsystemRows = [...bySubsystem.entries()]
      .map(([name, group]) => {
        const average = this.average(group) ?? 0;
        return { name, average, classification: this.classify(average)! };
      })
      .sort((a, b) => b.average - a.average);

    // Risk by building (always global, used as navigation)
    this.buildingRows = this.buildings.map(b => {
      const group = this.devices.filter(d => d.id_building === b.id_building);
      const average = this.average(group);
      return {
        id: b.id_building,
        name: b.name,
        deviceCount: group.length,
        average,
        classification: this.classify(average),
      };
    });
    const unassigned = this.devices.filter(d => d.id_building === null);
    if (unassigned.length > 0) {
      const average = this.average(unassigned);
      this.buildingRows.push({
        id: UNASSIGNED,
        name: 'Unassigned',
        deviceCount: unassigned.length,
        average,
        classification: this.classify(average),
      });
    }

    // Risk by floor (selected building, ignores the floor filter so the
    // cross-section stays visible while a floor is selected)
    this.floorRows = [];
    const building = this.selectedBuilding;
    if (building) {
      const inBuilding = this.devices.filter(d => d.id_building === building.id_building);
      const floors = new Set<number>();
      for (let f = 1; f <= building.floor_count; f++) floors.add(f);
      for (const d of inBuilding) if (d.floor !== null) floors.add(d.floor);

      this.floorRows = [...floors].sort((a, b) => b - a).map(floor => {
        const group = inBuilding.filter(d => d.floor === floor);
        const average = this.average(group);
        return { floor, deviceCount: group.length, average, classification: this.classify(average) };
      });
    }
    this.floorRowsAsc = [...this.floorRows].reverse();

    // Options for the dropdown filters
    this.buildingOptions = this.buildingRows.map(b => ({
      value: b.id,
      label: b.name,
      count: b.deviceCount,
      color: this.hex(b.classification?.color),
    }));

    this.floorOptions = this.floorRowsAsc.map(f => ({
      value: String(f.floor),
      label: this.floorLabel(f.floor),
      count: f.deviceCount,
      color: f.deviceCount > 0 ? this.hex(f.classification?.color) : undefined,
    }));

    // Risk trend (current selection)
    this.trendPoints = this.computeTrend();

    // Device list
    const list = this.onlyAtRisk
      ? this.filteredDevices.filter(d => this.isScored(d) && ['Medium', 'High'].includes(d.classification.label))
      : this.filteredDevices;
    this.visibleDevices = [...list].sort((a, b) => b.normalized_score - a.normalized_score);
  }

  // Average of the selected devices' snapshots: per day over 30 days, per month over 12 months
  private computeTrend(): TrendPoint[] {
    const ids = new Set(this.filteredDevices.filter(d => this.isScored(d)).map(d => d.id_device));
    const monthly = this.trendRange === '12m';
    const cutoff = this.trendCutoff(monthly);

    const buckets = new Map<string, { sum: number; count: number }>();
    for (const p of this.history) {
      if (!ids.has(p.id_device) || p.date < cutoff) continue;
      const key = monthly ? p.date.slice(0, 7) : p.date;
      const bucket = buckets.get(key) ?? { sum: 0, count: 0 };
      bucket.sum += p.score;
      bucket.count += 1;
      buckets.set(key, bucket);
    }

    return [...buckets.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, { sum, count }]) => ({
        label: this.trendLabel(key, monthly),
        average: Math.round((sum / count) * 100) / 100,
      }));
  }

  private trendCutoff(monthly: boolean): string {
    const date = new Date();
    if (monthly) {
      date.setUTCDate(1);
      date.setUTCMonth(date.getUTCMonth() - 11);
    } else {
      date.setUTCDate(date.getUTCDate() - 29);
    }
    return date.toISOString().slice(0, 10);
  }

  private trendLabel(key: string, monthly: boolean): string {
    const date = new Date(monthly ? `${key}-01T00:00:00Z` : `${key}T00:00:00Z`);
    return date.toLocaleDateString(
      'en-GB',
      monthly
        ? { month: 'short', year: 'numeric', timeZone: 'UTC' }
        : { day: 'numeric', month: 'short', timeZone: 'UTC' }
    );
  }

  // ---------- Charts ----------

  private updateChart() {
    const canvas = this.subsystemChartCanvas?.nativeElement;
    if (!canvas) return;

    const labels = this.subsystemRows.map(r => r.name);
    const values = this.subsystemRows.map(r => r.average);
    const colors = this.subsystemRows.map(r => this.hex(r.classification.color));

    // Update in place so bars animate smoothly when a filter changes.
    if (this.chart) {
      this.chart.data.labels = labels;
      this.chart.data.datasets[0].data = values;
      this.chart.data.datasets[0].backgroundColor = colors;
      this.chart.update();
      return;
    }

    this.chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Average risk score',
          data: values,
          backgroundColor: colors,
          borderRadius: 6,
          maxBarThickness: 28,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        plugins: { legend: { display: false } },
        scales: {
          x: { min: 0, max: 100, grid: { color: '#f3f4f6' }, title: { display: true, text: 'Average score (%)' } },
          y: { grid: { display: false } }
        }
      }
    });
  }

  private updateTrendChart() {
    const canvas = this.trendChartCanvas?.nativeElement;
    if (!canvas) return;

    const labels = this.trendPoints.map(p => p.label);
    const values = this.trendPoints.map(p => p.average);

    if (this.trendChart) {
      this.trendChart.data.labels = labels;
      this.trendChart.data.datasets[0].data = values;
      this.trendChart.update();
      return;
    }

    this.trendChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Average risk score',
          data: values,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => `${ctx.parsed.y}%` } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } },
          y: { min: 0, max: 100, grid: { color: '#f3f4f6' }, ticks: { callback: value => `${value}%` } }
        }
      }
    });
  }
}