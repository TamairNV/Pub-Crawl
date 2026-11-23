import {Component, inject, OnInit, ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {AuthService} from '../auth';
import { firstValueFrom } from 'rxjs';


@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class AdminDashboardComponent implements OnInit {
  constructor(private cdr: ChangeDetectorRef) {}
  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);

  events: any[] = [];
  eventName = '';
  creating = false;
  createError = '';

  // Owner only: who is an admin
  users: any[] = [];
  userSearch = '';
  roleMessage = '';

  // Owner only: delete / restore / reset events
  deletedCount = 0;
  eventToDelete: any | null = null;
  deletingEvent = false;
  deleteMessage = '';

  eventToReset: any | null = null;
  resettingEvent = false;
  resetClearMedia = true;
  resetError = '';

  ngOnInit() {
    this.getEvents();
    this.http.get('/api/me').subscribe({
      next: (response: any) => {
        const cur = this.authService.getSession()();
        if (response.status === 'success' && cur) {
          this.authService.setSession({ ...cur, role: response.received.role });
        }
        if (this.authService.isOwner()) {
          this.getManagedUsers();
          this.getDeletedCount();
        }
        this.cdr.detectChanges();
      },
      error: () => {
        if (this.authService.isOwner()) {
          this.getManagedUsers();
          this.getDeletedCount();
        }
      }
    });
  }

  // Step 1 of a new crawl: just a name. Everything else is set up on the crawl's own page.
  async createCrawl() {
    const name = this.eventName.trim();
    if (!name || this.creating) {
      return;
    }
    this.creating = true;
    this.createError = '';
    try {
      const response: any = await firstValueFrom(
        this.http.post('/api/create-crawl', { name, id: crypto.randomUUID() })
      );
      if (response.status === 'success') {
        this.router.navigate(['/event-details', response.received]);
      } else {
        this.createError = 'Could not create the crawl. Try again.';
      }
    } catch (error) {
      this.createError = 'Could not create the crawl. Are you still logged in as an admin?';
    }
    this.creating = false;
    this.cdr.detectChanges();
  }

  getEvents() {
    this.http.get('/api/get-events').subscribe({
      next: (response: any) => {
        if (response.status == 'success') {
          this.events = (response.received || []).slice().sort((a: any, b: any) => {
            const ta = a?.created_at ? new Date(a.created_at).getTime() : 0;
            const tb = b?.created_at ? new Date(b.created_at).getTime() : 0;
            return tb - ta;
          });
          this.cdr.detectChanges();
        }
      }
    });
  }

  getDeletedCount() {
    this.http.get('/api/get-deleted-events').subscribe({
      next: (response: any) => {
        if (response.status === 'success') {
          this.deletedCount = (response.received || []).length;
          this.cdr.detectChanges();
        }
      },
      error: () => {}
    });
  }

  askDeleteEvent(event: any) {
    this.eventToDelete = event;
    this.deleteMessage = '';
  }

  cancelDeleteEvent() {
    if (this.deletingEvent) return;
    this.eventToDelete = null;
  }

  confirmDeleteEvent() {
    if (!this.eventToDelete || this.deletingEvent) return;
    const target = this.eventToDelete;
    this.deletingEvent = true;
    this.deleteMessage = '';
    this.http.post('/api/delete-event', { event_id: target.id }).subscribe({
      next: (response: any) => {
        this.deletingEvent = false;
        if (response.status === 'success') {
          this.events = this.events.filter(e => e.id !== target.id);
          this.deletedCount += 1;
          this.eventToDelete = null;
          this.deleteMessage = `Moved "${target.name}" to Restore.`;
        } else {
          this.deleteMessage = response.received || 'Could not delete event.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.deletingEvent = false;
        this.deleteMessage = err?.error?.received || 'Could not delete event.';
        this.cdr.detectChanges();
      }
    });
  }

  askResetEvent(event: any) {
    this.eventToReset = event;
    this.resetClearMedia = true;
    this.resetError = '';
    this.deleteMessage = '';
  }

  cancelResetEvent() {
    if (this.resettingEvent) return;
    this.eventToReset = null;
  }

  confirmResetEvent() {
    if (!this.eventToReset || this.resettingEvent) return;
    const target = this.eventToReset;
    this.resettingEvent = true;
    this.resetError = '';
    this.http.post('/api/reset-event', { event_id: target.id, clear_media: this.resetClearMedia }).subscribe({
      next: (response: any) => {
        this.resettingEvent = false;
        if (response.status === 'success') {
          const c = response.received || {};
          this.eventToReset = null;
          this.deleteMessage =
            `Reset "${target.name}" (${c.points || 0} pts, ${c.team_points || 0} team pts, ${c.tasks || 0} tasks, ${c.votes || 0} votes${this.resetClearMedia ? `, ${c.photos || 0} media` : ''} cleared).`;
        } else {
          this.resetError = response.received || 'Could not reset crawl scores.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.resettingEvent = false;
        this.resetError = err?.error?.received || 'Could not reset crawl scores.';
        this.cdr.detectChanges();
      }
    });
  }

  getManagedUsers() {
    this.http.get('/api/manage-users').subscribe({
      next: (response: any) => {
        if (response.status == 'success') {
          this.users = response.received;
          this.cdr.detectChanges();
        }
      }
    });
  }

  filteredUsers() {
    const q = this.userSearch.trim().toLowerCase();
    return q ? this.users.filter(u => String(u.name).toLowerCase().includes(q)) : this.users;
  }

  roleOf(user: any) {
    return String(user.role || 'player').toLowerCase();
  }

  setRole(user: any, role: 'admin' | 'player') {
    this.roleMessage = '';
    this.http.post('/api/set-user-role', { user_id: user.id, role }).subscribe({
      next: (response: any) => {
        if (response.status == 'success') {
          user.role = response.received.role;
          this.roleMessage = role === 'admin'
            ? `${user.name} is now an admin.`
            : `${user.name} is no longer an admin.`;
        } else {
          this.roleMessage = response.received || 'Could not change that role.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.roleMessage = err?.error?.received || 'Could not change that role.';
        this.cdr.detectChanges();
      }
    });
  }

  logout() {
    this.http.post('/api/logout-user', {}).subscribe({ complete: () => {} });
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
