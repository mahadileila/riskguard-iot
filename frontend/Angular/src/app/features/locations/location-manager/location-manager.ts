import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Notification, NotificationType } from '../../../shared/components/notification/notification';
import { LocationService } from '../../../core/services/location.service';
import { Building, Location } from '../../../core/models/location.model';

type DeleteTarget = { kind: 'building' | 'location'; id: string; label: string };

@Component({
  selector: 'app-location-manager',
  standalone: true,
  imports: [CommonModule, FormsModule, Notification],
  templateUrl: './location-manager.html'
})
export class LocationManager implements OnInit {
  buildings: Building[] = [];
  locations: Location[] = [];
  selectedBuilding: Building | null = null;
  loading = true;

  notificationType: NotificationType = null;
  notificationMessage: string | null = null;

  showBuildingForm = false;
  editingBuildingId: string | null = null;
  formBuildingName = '';

  showLocationForm = false;
  editingLocationId: string | null = null;
  formFloor = '';
  formZone = '';

  deleteTarget: DeleteTarget | null = null;

  constructor(private locationService: LocationService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.loadBuildings();
  }

  private showNotification(type: NotificationType, message: string) {
    this.notificationType = type;
    this.notificationMessage = message;
    this.cdr.detectChanges();
    setTimeout(() => {
      this.notificationType = null;
      this.notificationMessage = null;
      this.cdr.detectChanges();
    }, 4000);
  }

  loadBuildings(selectId?: string) {
    this.loading = true;
    this.locationService.getBuildings().subscribe({
      next: (data) => {
        this.buildings = data;
        this.loading = false;
        const keepId = selectId ?? this.selectedBuilding?.id_building;
        const target = data.find(b => b.id_building === keepId) ?? data[0] ?? null;
        this.selectBuilding(target);
      },
      error: () => {
        this.loading = false;
        this.showNotification('error', 'Unable to load buildings.');
      }
    });
  }

  selectBuilding(building: Building | null) {
    this.selectedBuilding = building;
    this.locations = [];
    if (!building) { this.cdr.detectChanges(); return; }
    this.locationService.getLocations(building.id_building).subscribe({
      next: (data) => { this.locations = data; this.cdr.detectChanges(); },
      error: () => this.showNotification('error', 'Unable to load locations.')
    });
  }

  // ---------- Buildings ----------
  openAddBuilding() {
    this.editingBuildingId = null;
    this.formBuildingName = '';
    this.showBuildingForm = true;
  }

  openEditBuilding(b: Building) {
    this.editingBuildingId = b.id_building;
    this.formBuildingName = b.name;
    this.showBuildingForm = true;
  }

  saveBuilding() {
    if (!this.formBuildingName.trim()) {
      this.showNotification('error', 'Building name is required.');
      return;
    }
    const payload = { name: this.formBuildingName.trim() };
    const wasEditing = !!this.editingBuildingId;
    const request = this.editingBuildingId
      ? this.locationService.updateBuilding(this.editingBuildingId, payload)
      : this.locationService.createBuilding(payload);

    request.subscribe({
      next: (b) => {
        this.showBuildingForm = false;
        this.loadBuildings(b.id_building);
        this.showNotification('success', wasEditing ? 'Building updated.' : 'Building created.');
      },
      error: () => this.showNotification('error', 'Error while saving the building.')
    });
  }

  // ---------- Locations ----------
  openAddLocation() {
    this.editingLocationId = null;
    this.formFloor = '';
    this.formZone = '';
    this.showLocationForm = true;
  }

  openEditLocation(l: Location) {
    this.editingLocationId = l.id_location;
    this.formFloor = l.floor;
    this.formZone = l.zone ?? '';
    this.showLocationForm = true;
  }

  saveLocation() {
    if (!this.selectedBuilding) return;
    if (!this.formFloor.trim()) {
      this.showNotification('error', 'Floor is required.');
      return;
    }
    const zone = this.formZone.trim() || null;
    const wasEditing = !!this.editingLocationId;
    const request = this.editingLocationId
      ? this.locationService.updateLocation(this.editingLocationId, { floor: this.formFloor.trim(), zone })
      : this.locationService.createLocation({
          id_building: this.selectedBuilding.id_building,
          floor: this.formFloor.trim(),
          zone
        });

    request.subscribe({
      next: () => {
        this.showLocationForm = false;
        this.loadBuildings(this.selectedBuilding?.id_building);
        this.showNotification('success', wasEditing ? 'Location updated.' : 'Location created.');
      },
      error: () => this.showNotification('error', 'Error while saving the location.')
    });
  }

  // ---------- Delete ----------
  askDeleteBuilding(b: Building) {
    this.deleteTarget = { kind: 'building', id: b.id_building, label: b.name };
  }

  askDeleteLocation(l: Location) {
    this.deleteTarget = { kind: 'location', id: l.id_location, label: l.label };
  }

  cancelDelete() {
    this.deleteTarget = null;
  }

  confirmDelete() {
    if (!this.deleteTarget) return;
    const target = this.deleteTarget;
    const request = target.kind === 'building'
      ? this.locationService.deleteBuilding(target.id)
      : this.locationService.deleteLocation(target.id);

    request.subscribe({
      next: () => {
        this.deleteTarget = null;
        this.loadBuildings(target.kind === 'location' ? this.selectedBuilding?.id_building : undefined);
        this.showNotification('success', `"${target.label}" deleted.`);
      },
      error: (err) => {
        this.deleteTarget = null;
        this.showNotification(
          'error',
          err.status === 409
            ? (target.kind === 'building'
                ? 'Cannot delete: this building still has locations.'
                : 'Cannot delete: devices are still located here.')
            : 'Error while deleting.'
        );
      }
    });
  }
}