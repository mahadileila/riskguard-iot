import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Notification, NotificationType } from '../../../shared/components/notification/notification';
import { DeviceTypeService } from '../../../core/services/device-type.service';
import { SubsystemService } from '../../../core/services/subsystem.service';
import { DeviceType } from '../../../core/models/device-type.model';
import { BmsSubsystem } from '../../../core/models/subsystem.model';

@Component({
  selector: 'app-device-type-list',
  standalone: true,
  imports: [CommonModule, FormsModule, Notification],
  templateUrl: './device-type-list.html'
})
export class DeviceTypeList implements OnInit {
  deviceTypes: DeviceType[] = [];
  subsystems: BmsSubsystem[] = [];
  searchTerm = '';
  loading = true;

  notificationType: NotificationType = null;
  notificationMessage: string | null = null;

  showForm = false;
  editingId: string | null = null;
  formName = '';
  formSubsystemId = '';
  formPrimaryData = '';

  showDeleteForm = false;
  deviceTypeToDelete: DeviceType | null = null;
  selectedSubsystemId: string | null = null;

  constructor(
    private deviceTypeService: DeviceTypeService,
    private subsystemService: SubsystemService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadData();
  }

  get filteredDeviceTypes(): DeviceType[] {
    const term = this.searchTerm.trim().toLowerCase();

    return this.deviceTypes.filter(dt =>
      (this.selectedSubsystemId === null || dt.id_subsystem === this.selectedSubsystemId) &&
      (!term || dt.name.toLowerCase().includes(term))
    );
  }

  resetFilters() {
    this.searchTerm = '';
    this.selectedSubsystemId = null;
  }

  subsystemName(id: string): string {
    return this.subsystems.find(s => s.id_subsystem === id)?.name ?? '—';
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
    this.deviceTypeService.getDeviceTypes().subscribe({
      next: (types) => {
        this.deviceTypes = types;
        this.subsystemService.getSubsystems().subscribe({
          next: (subsystems) => {
            this.subsystems = subsystems;
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.loading = false;
            this.showNotification('error', "Unable to load subsystems.");
          }
        });
      },
      error: () => {
        this.loading = false;
        this.showNotification('error', "Unable to load device types.");
      }
    });
  }

  openAddForm() {
    this.editingId = null;
    this.formName = '';
    this.formSubsystemId = '';
    this.formPrimaryData = '';
    this.showForm = true;
  }

  openEditForm(deviceType: DeviceType) {
    this.editingId = deviceType.id_device_type;
    this.formName = deviceType.name;
    this.formSubsystemId = deviceType.id_subsystem;
    this.formPrimaryData = deviceType.primary_data_collected ?? '';
    this.showForm = true;
  }

  cancelForm() {
    this.showForm = false;
  }

  saveDeviceType() {
    if (!this.formName.trim() || !this.formSubsystemId) {
      this.showForm = false;
      this.showNotification('error', "Name and Subsystem are required.");
      return;
    }

    const payload = {
      name: this.formName,
      id_subsystem: this.formSubsystemId,
      primary_data_collected: this.formPrimaryData || null
    };

    const request = this.editingId
      ? this.deviceTypeService.updateDeviceType(this.editingId, payload)
      : this.deviceTypeService.createDeviceType(payload);

    request.subscribe({
      next: () => {
        this.showForm = false;
        this.loadData();
        this.showNotification('success', this.editingId ? "Device type updated." : "Device type created.");
      },
      error: () => {
        this.showForm = false;
        this.showNotification('error', "Error while saving.");
      }
    });
  }

  deleteDeviceType(deviceType: DeviceType) {
    this.deviceTypeToDelete = deviceType;
    this.showDeleteForm = true;
  }

  cancelDelete() {
    this.showDeleteForm = false;
    this.deviceTypeToDelete = null;
  }

  confirmDelete() {
    if (!this.deviceTypeToDelete) return;

    const target = this.deviceTypeToDelete;

    this.deviceTypeService.deleteDeviceType(target.id_device_type).subscribe({
      next: () => {
        this.showDeleteForm = false;
        this.deviceTypeToDelete = null;
        this.loadData();
        this.showNotification('success', `"${target.name}" deleted.`);
      },
      error: (err) => {
        this.showDeleteForm = false;
        this.deviceTypeToDelete = null;
        this.showNotification(
          'error',
          err.status === 409
            ? "Cannot delete: devices are still linked to this type."
            : "Error while deleting."
        );
        this.cdr.detectChanges();
      }
    });
  }
}