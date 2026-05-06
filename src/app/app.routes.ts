import { Routes } from '@angular/router';
import {CreateAccountComponent} from './account/create_account'
import {LoginComponent} from './account/login';
import {AdminDashboardComponent} from './admin/dashboard';

export const routes: Routes = [
  { path: 'create-account', component: CreateAccountComponent }, // Home/Login page
  { path: 'admin-dashboard', component: AdminDashboardComponent }, // Where they go after create_account
  { path: 'login', component: LoginComponent },
  { path: '',redirectTo: '/login',pathMatch : 'full' }
];
