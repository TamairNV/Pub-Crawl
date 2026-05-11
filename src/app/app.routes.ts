import { Routes } from '@angular/router';
import {CreateAccountComponent} from './account/create_account'
import {LoginComponent} from './account/login';
import {AdminDashboardComponent} from './admin/dashboard';
import {EventDetailsComponent} from './admin/event-details';
import {RefComponent} from './admin/ref';

export const routes: Routes = [
  { path: 'create-account', component: CreateAccountComponent }, // Home/Login page
  { path: 'admin-dashboard', component: AdminDashboardComponent }, // Where they go after create_account
  { path: 'login', component: LoginComponent },
  { path: '',redirectTo: '/login',pathMatch : 'full' },
  { path: 'event-details/:id', component: EventDetailsComponent },
  { path: 'ref/:id', component: RefComponent }
];
