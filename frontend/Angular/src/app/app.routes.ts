import { Routes } from '@angular/router';
import { Layout } from './shared/components/layout/layout';
import { Login } from './features/auth/login/login';
import { authGuard } from './core/guards/auth.guard';
import { DeviceList } from './features/devices/device-list/device-list';
import { BmsSubsystemList } from './features/bms-subsystems/bms-subsystem-list/bms-subsystem-list';
import { DeviceTypeList } from './features/device-types/device-type-list/device-type-list';
import { DeviceDetail } from './features/devices/device-detail/device-detail';
import { Dashboard } from './features/dashboard/dashboard/dashboard';
import { RiskFactorList } from './features/risk-factors/risk-factor-list/risk-factor-list';
import { RiskClassificationList } from './features/risk-classifications/risk-classification-list/risk-classification-list';
import { LocationManager } from './features/locations/location-manager/location-manager';

export const routes: Routes = [
  { path: 'login', component: Login },
  {
    path: '',
    component: Layout,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: Dashboard, data: { breadcrumb: 'Dashboard' } },
      { path: 'devices', component: DeviceList, data: { breadcrumb: 'Devices' } },
      { path: 'devices/:id', component: DeviceDetail, data: { breadcrumb: 'Device Detail' } },
      { path: 'device-types', component: DeviceTypeList, data: { breadcrumb: 'Device Types' } },
      { path: 'subsystems', component: BmsSubsystemList, data: { breadcrumb: 'BMS Subsystems' } },
      { path: 'risk-factors', component: RiskFactorList, data: { breadcrumb: 'Risk Factors' } },
      { path: 'risk-classifications', component: RiskClassificationList, data: { breadcrumb: 'Risk Classifications' } },
      { path: 'locations', component: LocationManager, data: { breadcrumb: 'Buildings & Locations' }},
    ]
  }
];