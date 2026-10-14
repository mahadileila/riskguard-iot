import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Notification, NotificationType } from '../../../shared/components/notification/notification';
import { BuildingService } from '../../../core/services/building.service';
import { Building } from '../../../core/models/building.model';

@Component({
  selector: 'app-building-list',
  standalone: true,
  imports: [CommonModule, FormsModule, Notification],
  templateUrl: './building-list.html'
})
export class BuildingList implements OnInit {
  buildings: Building[] = [];
  searchTerm = '';
  loading = true;
  loadError: string | null = null;

  notificationType: NotificationType = null;
  notificationMessage: string | null = null;

  showForm = false;
  editingId: string | null = null;
  formName = '';
  formFloorCount: number | null = null;

  showDeleteForm = false;
  buildingToDelete: Building | null = null;

  constructor(
    private buildingService: BuildingService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadBuildings();
  }

  get filteredBuildings(): Building[] {
    if (!this.searchTerm.trim()) return this.buildings;
    const term = this.searchTerm.toLowerCase();
    return this.buildings.filter(b => b.name.toLowerCase().includes(term));
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

  loadBuildings() {
    this.loading = true;
    this.loadError = null;
    this.buildingService.getBuildings().subscribe({
      next: (data) => {
        this.buildings = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.buildings = [];
        this.loadError = 'Unable to load buildings. Please check that the server is running and try again.';
        this.cdr.detectChanges();
      }
    });
  }

  openAddForm() {
    this.editingId = null;
    this.formName = '';
    this.formFloorCount = null;
    this.showForm = true;
  }

  openEditForm(building: Building) {
    this.editingId = building.id_building;
    this.formName = building.name;
    this.formFloorCount = building.floor_count;
    this.showForm = true;
  }

  cancelForm() {
    this.showForm = false;
  }

  saveBuilding() {
    if (!this.formName.trim()) {
      this.showNotification('error', 'Building name is required.');
      return;
    }

    const floorCount = Number(this.formFloorCount);
    if (!Number.isInteger(floorCount) || floorCount < 1 || floorCount > 200) {
      this.showNotification('error', 'Number of floors must be a whole number between 1 and 200.');
      return;
    }

    const payload = { name: this.formName.trim(), floor_count: floorCount };
    const wasEditing = !!this.editingId;

    const request = this.editingId
      ? this.buildingService.updateBuilding(this.editingId, payload)
      : this.buildingService.createBuilding(payload);

    request.subscribe({
      next: () => {
        this.showForm = false;
        this.loadBuildings();
        this.showNotification('success', wasEditing ? 'Building updated.' : 'Building created.');
      },
      error: (err) => {
        this.showNotification(
          'error',
          err.error?.error ?? 'Error while saving the building.'
        );
      }
    });
  }

  deleteBuilding(building: Building) {
    this.buildingToDelete = building;
    this.showDeleteForm = true;
  }

  cancelDelete() {
    this.showDeleteForm = false;
    this.buildingToDelete = null;
  }

  confirmDelete() {
    if (!this.buildingToDelete) return;

    const target = this.buildingToDelete;

    this.buildingService.deleteBuilding(target.id_building).subscribe({
      next: () => {
        this.showDeleteForm = false;
        this.buildingToDelete = null;
        this.loadBuildings();
        this.showNotification('success', `"${target.name}" deleted.`);
      },
      error: (err) => {
        this.showDeleteForm = false;
        this.buildingToDelete = null;
        this.showNotification(
          'error',
          err.status === 409
            ? 'Cannot delete: devices are still located in this building.'
            : 'Error while deleting.'
        );
      }
    });
  }
}