import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth';

@Component({
  selector: 'app-admin-restore',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './restore.html',
  styleUrl: './restore.css',
})
export class RestoreCrawlsComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  authService = inject(AuthService);

  deletedEvents: any[] = [];
  loading = true;
  schemaMissing = false;
  message = '';
  errorMessage = '';
  busyId: string | null = null;

  eventToPurge: any | null = null;
  purging = false;

  ngOnInit() {
    this.http.get('/api/me').subscribe({
      next: (res: any) => {
        const cur = this.authService.getSession()();
        if (res.status === 'success') {
          this.authService.setSession({
            ...(cur || {}),
            id: res.received.id,
            name: res.received.name,
            role: res.received.role,
          });
        }
        if (!this.authService.isOwner()) {
          this.router.navigate(['/admin-dashboard']);
          return;
        }
        this.loadDeletedEvents();
      },
      error: () => {
        this.router.navigate(['/login']);
      },
    });
  }

  loadDeletedEvents() {
    this.loading = true;
    this.errorMessage = '';
    this.http.get('/api/get-deleted-events').subscribe({
      next: (res: any) => {
        this.loading = false;
        if (res.status === 'success') {
          this.schemaMissing = false;
          this.deletedEvents = res.received || [];
        } else {
          this.schemaMissing = !!res.schema_missing;
          this.errorMessage = res.received || 'Could not load deleted crawls.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.loading = false;
        this.schemaMissing = !!err?.error?.schema_missing;
        this.errorMessage = err?.error?.received || 'Could not load deleted crawls.';
        this.cdr.detectChanges();
      },
    });
  }

  restoreEvent(event: any) {
    if (this.busyId) return;
    this.busyId = event.id;
    this.message = '';
    this.errorMessage = '';
    this.http.post('/api/restore-event', { event_id: event.id }).subscribe({
      next: (res: any) => {
        this.busyId = null;
        if (res.status === 'success') {
          this.deletedEvents = this.deletedEvents.filter((e) => e.id !== event.id);
          this.message = `Restored "${event.name}". It is back on your dashboard.`;
        } else {
          this.errorMessage = res.received || 'Could not restore crawl.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.busyId = null;
        this.errorMessage = err?.error?.received || 'Could not restore crawl.';
        this.cdr.detectChanges();
      },
    });
  }

  askPurge(event: any) {
    this.eventToPurge = event;
    this.errorMessage = '';
  }

  cancelPurge() {
    if (this.purging) return;
    this.eventToPurge = null;
  }

  confirmPurge() {
    if (!this.eventToPurge || this.purging) return;
    const target = this.eventToPurge;
    this.purging = true;
    this.errorMessage = '';
    this.http.post('/api/purge-event', { event_id: target.id }).subscribe({
      next: (res: any) => {
        this.purging = false;
        if (res.status === 'success') {
          this.deletedEvents = this.deletedEvents.filter((e) => e.id !== target.id);
          this.eventToPurge = null;
          this.message = `Permanently deleted "${target.name}".`;
        } else {
          this.errorMessage = res.received || 'Could not permanently delete crawl.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.purging = false;
        this.errorMessage = err?.error?.received || 'Could not permanently delete crawl.';
        this.cdr.detectChanges();
      },
    });
  }
}
