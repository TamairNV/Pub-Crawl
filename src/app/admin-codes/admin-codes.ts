import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';

// Super-admin (OWNER): free-access codes for friends, with usage.
@Component({
  selector: 'app-admin-codes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe],
  templateUrl: './admin-codes.html',
  styleUrls: ['../admin/dashboard.css', './admin-codes.css'],
})
export class AdminCodesComponent implements OnInit {
  private http = inject(HttpClient);
  private cdr = inject(ChangeDetectorRef);
  codes: any[] = [];
  label = ''; maxUses = 1; expiresDays: number | null = 90; custom = '';
  message = ''; justMade = '';

  ngOnInit() { this.load(); }

  load() {
    this.http.post<any>('/api/access-codes', {}).subscribe({
      next: (res) => { this.codes = res.received || []; this.cdr.detectChanges(); },
      error: (err) => { this.message = err?.status === 403 ? 'Owner only.' : 'Could not load codes.'; this.cdr.detectChanges(); },
    });
  }

  create() {
    this.message = '';
    this.http.post<any>('/api/create-access-code', {
      label: this.label, max_uses: this.maxUses, expires_days: this.expiresDays, code: this.custom,
    }).subscribe({
      next: (res) => { this.justMade = res.received; this.label = ''; this.custom = ''; this.load(); },
      error: (err) => { this.message = err?.error?.received || 'Could not create the code.'; this.cdr.detectChanges(); },
    });
  }

  toggle(c: any) {
    this.http.post('/api/set-access-code-active', { id: c.id, active: !c.active }).subscribe(() => this.load());
  }

  copy(code: string) { navigator.clipboard?.writeText(code); this.message = `Copied ${code}`; }
}
