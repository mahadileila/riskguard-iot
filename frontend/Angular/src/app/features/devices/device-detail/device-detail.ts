import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule, Location } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { DeviceService } from '../../../core/services/device.service';
import { Device } from '../../../core/models/device.model';
import { CollectionInstance } from '../../../core/models/instance.model';

@Component({
  selector: 'app-device-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './device-detail.html'
})
export class DeviceDetail implements OnInit {
  deviceId = '';
  device: Device | null = null;
  instances: CollectionInstance[] = [];
  activeTab: 'general' | 'instances' | 'samples' = 'general';
  loading = true;
  error: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private deviceService: DeviceService,
    private location: Location,
    private cdr: ChangeDetectorRef
  ) {}

  goBack() {
    this.location.back();
  }

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.error = "Missing device id.";
      this.loading = false;
      return;
    }
    this.deviceId = id;

    this.deviceService.getDevice(id).subscribe({
      next: (device) => {
        this.device = device;
        this.deviceService.getDeviceInstances(id).subscribe({
          next: (instances) => {
            this.instances = instances;
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.error = "Unable to load collection instances.";
            this.loading = false;
            this.cdr.detectChanges();
          }
        });
      },
      error: () => {
        this.error = "Device not found.";
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  get allSamples(): { instance_description: string; data_value: string; captured_at: string }[] {
    return this.instances
      .flatMap(instance =>
        instance.data_samples.map(sample => ({
          instance_description: instance.data_description ?? 'Unnamed instance',
          data_value: sample.data_value,
          captured_at: sample.captured_at
        }))
      )
      .sort((a, b) => new Date(b.captured_at).getTime() - new Date(a.captured_at).getTime());
  }

  // "Building A - Main Tower · Floor 2 · Open space", or an em dash for devices without a location
  get locationLabel(): string {
    if (!this.device?.building_name) return '—';
    const parts = [this.device.building_name, `Floor ${this.device.floor}`];
    if (this.device.zone) parts.push(this.device.zone);
    return parts.join(' · ');
  }

  setTab(tab: 'general' | 'instances' | 'samples') {
    this.activeTab = tab;
  }

  private readonly ATTRIBUTE_LABELS: Record<string, string> = {
    // Data nature
    environmental: 'Environmental',
    non_personal_usage: 'Non-personal usage data',
    behavioural: 'Behavioural',
    behavioural_contextual: 'Behavioural (contextual)',
    identity_biometric: 'Identity / biometric',

    // Identifiability
    cannot_link: 'Cannot be linked',
    significant_effort: 'Linkable with significant effort',
    additional_information: 'Linkable with additional information',
    minimal_information: 'Linkable with minimal information',
    direct: 'Directly identifies',

    // Location scope
    none: 'No spatial information',
    building_level: 'Building-level',
    room_zone: 'Room / zone-level',
    room_zone_over_time: 'Room / zone-level, tracked over time',
    precise_continuous: 'Precise and continuous',

    // Collection frequency
    occasional: 'Occasional / rare',
    weekly_several: 'Several times per week',
    periodic: 'Periodic (a few times per day)',
    frequent: 'Frequent (hourly / near-continuous)',
    continuous: 'Continuous / real-time',

    // Access scope
    key_personnel: '1-2 key personnel',
    small_team: 'Small, defined team',
    defined_group: 'Defined group',
    multiple_departments: 'Multiple departments',
    broadly_accessible: 'Broadly accessible',

    // Sharing scope
    not_shared: 'Not shared',
    same_subsystem: 'Within the same subsystem',
    internal_services: 'Internal building services',
    external_partner_contract: 'External partner (contractual)',
    external_third_party: 'External third party',
  };

  formatAttribute(value: string): string {
    return this.ATTRIBUTE_LABELS[value] ?? value;
  }
}