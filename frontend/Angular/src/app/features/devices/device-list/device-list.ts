import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Notification, NotificationType } from '../../../shared/components/notification/notification';
import { DeviceService } from '../../../core/services/device.service';
import { DeviceTypeService } from '../../../core/services/device-type.service';
import { BuildingService } from '../../../core/services/building.service';
import { Device } from '../../../core/models/device.model';
import { DeviceType } from '../../../core/models/device-type.model';
import { Building } from '../../../core/models/building.model';

@Component({
  selector: 'app-device-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, Notification],
  templateUrl: './device-list.html'
})
export class DeviceList implements OnInit {
  devices: Device[] = [];
  deviceTypes: DeviceType[] = [];
  buildings: Building[] = [];
  floors: number[] = [];
  searchTerm = '';
  loading = true;

  notificationType: NotificationType = null;
  notificationMessage: string | null = null;

  showForm = false;
  editingId: string | null = null;
  formName = '';
  formDeviceTypeId = '';
  formBuildingId = '';
  formFloor: number | null = null;
  formZone = '';

  showDeleteForm = false;
  deviceToDelete: Device | null = null;

  constructor(
    private deviceService: DeviceService,
    private deviceTypeService: DeviceTypeService,
    private buildingService: BuildingService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadData();
    this.loadBuildings();
  }

  get filteredDevices(): Device[] {
    if (!this.searchTerm.trim()) return this.devices;
    const term = this.searchTerm.toLowerCase();
    return this.devices.filter(d => d.name.toLowerCase().includes(term));
  }

  deviceTypeName(id: string): string {
    return this.deviceTypes.find(dt => dt.id_device_type === id)?.name ?? '—';
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

  loadData() {
    this.loading = true;
    this.deviceService.getDevices().subscribe({
      next: (devices) => {
        this.devices = devices;
        this.deviceTypeService.getDeviceTypes().subscribe({
          next: (types) => {
            this.deviceTypes = types;
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.loading = false;
            this.showNotification('error', "Unable to load device types.");
          }
        });
      },
      error: () => {
        this.loading = false;
        this.showNotification('error', "Unable to load devices.");
      }
    });
  }

  // Independent from loadData(): a failure here must never block the device list.
  loadBuildings() {
    this.buildingService.getBuildings().subscribe({
      next: (buildings) => {
        this.buildings = buildings;
        this.cdr.detectChanges();
      },
      error: () => {
        this.showNotification('error', "Unable to load buildings.");
      }
    });
  }

  // Builds the list of selectable floors (1..floor_count) for the selected building.
  private updateFloors() {
    const building = this.buildings.find(b => b.id_building === this.formBuildingId);
    this.floors = building
      ? Array.from({ length: building.floor_count }, (_, i) => i + 1)
      : [];
    this.cdr.detectChanges();
  }

  onBuildingChange() {
    this.formFloor = null;
    this.updateFloors();
  }

  openAddForm() {
    this.editingId = null;
    this.formName = '';
    this.formDeviceTypeId = '';
    this.formBuildingId = '';
    this.formFloor = null;
    this.formZone = '';
    this.floors = [];
    this.showForm = true;
  }

  openEditForm(device: Device) {
    this.editingId = device.id_device;
    this.formName = device.name;
    this.formDeviceTypeId = device.id_device_type;
    this.formBuildingId = device.id_building ?? '';
    this.updateFloors();
    // Devices created before buildings existed have no floor yet.
    this.formFloor = device.floor ?? null;
    this.formZone = device.zone ?? '';
    this.showForm = true;
  }

  cancelForm() {
    this.showForm = false;
  }

  saveDevice() {
    if (!this.formName.trim() || !this.formDeviceTypeId || !this.formBuildingId || this.formFloor === null) {
      this.showForm = false;
      this.showNotification('error', "Name, Device Type, Building and Floor are required.");
      return;
    }

    const payload = {
      name: this.formName,
      id_device_type: this.formDeviceTypeId,
      id_building: this.formBuildingId,
      floor: this.formFloor,
      zone: this.formZone.trim() || null
    };

    const wasEditing = !!this.editingId;

    const request = this.editingId
      ? this.deviceService.updateDevice(this.editingId, payload)
      : this.deviceService.createDevice(payload);

    request.subscribe({
      next: () => {
        this.showForm = false;
        this.loadData();
        this.showNotification('success', wasEditing ? "Device updated." : "Device created.");
      },
      error: (err) => {
        this.showForm = false;
        this.showNotification('error', err.error?.error ?? "Error while saving.");
      }
    });
  }

  deleteDevice(device: Device) {
    this.deviceToDelete = device;
    this.showDeleteForm = true;
  }

  cancelDelete() {
    this.showDeleteForm = false;
    this.deviceToDelete = null;
  }

  confirmDelete() {
    if (!this.deviceToDelete) return;

    const target = this.deviceToDelete;

    this.deviceService.deleteDevice(target.id_device).subscribe({
      next: () => {
        this.showDeleteForm = false;
        this.deviceToDelete = null;
        this.loadData();
        this.showNotification('success', `"${target.name}" deleted.`);
      },
      error: () => {
        this.showDeleteForm = false;
        this.deviceToDelete = null;
        this.showNotification('error', "Error while deleting.");
        this.cdr.detectChanges();
      }
    });
  }

  exportToCsv() {
    const headers = ['Device Name', 'Type', 'Subsystem', 'Building', 'Floor', 'Position', 'Risk Score', 'Level'];

    const rows = this.filteredDevices.map(d => [
      d.name,
      d.device_type_name || '',
      d.subsystem_name || '',
      d.building_name || '',
      d.floor !== null && d.floor !== undefined ? d.floor.toString() : '',
      d.zone || '',
      d.active_instances_count > 0 ? d.normalized_score.toString() : '',
      d.active_instances_count > 0 ? d.classification.label : 'No Risk',
    ]);

    const csvContent = [headers, ...rows]
      .map(row => row.map(cell => this.escapeCsvCell(cell)).join(','))
      .join('\n');

     const blob = new Blob(['﻿' + csvContent], { type: 'text/csv;charset=utf-8;' });

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `devices-export-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  private escapeCsvCell(value: string): string {
     const escaped = value.replace(/"/g, '""');
    return `"${escaped}"`;
  }
}