import { Injectable } from '@angular/core';
import { ApiService } from './api.service';
import { Device } from '../models/device.model';
import { CollectionInstance } from '../models/instance.model';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DeviceService {
  constructor(private api: ApiService) {}

  getDevices() {
    return this.api.get<Device[]>('/devices');
  }

  getDevice(id: string) {
    return this.api.get<Device>(`/devices/${id}`);
  }

  createDevice(device: Partial<Device>) {
    return this.api.post<Device>('/devices', device);
  }

  updateDevice(id: string, device: Partial<Device>) {
    return this.api.put<Device>(`/devices/${id}`, device);
  }

  deleteDevice(id: string) {
    return this.api.delete<void>(`/devices/${id}`);
  }

  getDeviceInstances(id: string) {
    return this.api.get<CollectionInstance[]>(`/devices/${id}/instances`);
  }

  importSamples(id: string, file: File): Observable<{ imported: number }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.api.post<{ imported: number }>(`/devices/${id}/data-samples/import`, formData);
  }
}