import { Routes } from '@angular/router';
import {CreateAccountComponent} from './account/create_account'
import {LoginComponent} from './account/login';
import {AdminDashboardComponent} from './admin/dashboard';
import {RestoreCrawlsComponent} from './admin/restore';
import {EventDetailsComponent} from './admin/event-details';
import {RefComponent} from './admin/ref';
import {PlayerDashboard} from './player/playerDashboard';
import {EventPlay} from './player/eventPlay';
import {MapComponent} from './photos/map'
import {UploadComponent} from './photos/upload';
import {JoinComponent} from './join/join';
import {NewCrawlWizardComponent} from './wizard/wizard';
import {TeamRevealComponent} from './reveal/reveal';
import {AdminCodesComponent} from './admin-codes/admin-codes';
import {RecapComponent} from './recap/recap';

export const routes: Routes = [
  { path: 'create-account', component: CreateAccountComponent }, // Home/Login page
  { path: 'admin-dashboard', component: AdminDashboardComponent }, // Where they go after create_account
  { path: 'admin-restore', component: RestoreCrawlsComponent },
  { path: 'login', component: LoginComponent },
  { path: 'join/:token', component: JoinComponent },
  { path: 'new-crawl', component: NewCrawlWizardComponent },
  { path: 'reveal/:id', component: TeamRevealComponent },
  { path: 'admin-codes', component: AdminCodesComponent },
  { path: 'recap/:id', component: RecapComponent },
  { path: '',redirectTo: '/login',pathMatch : 'full' },
  { path: 'event-details/:id', component: EventDetailsComponent },
  { path: 'ref/:id', component: RefComponent },
  { path: 'player-dashboard', component: PlayerDashboard },
  { path: 'event-play/:id', component: EventPlay },
  { path: 'map-view/:id', component: MapComponent },
  { path: 'upload/:id', component: UploadComponent },
  { path: '**', redirectTo: '/login' }
];
