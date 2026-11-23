import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../auth';

// /join/:token, opened from the organiser's QR code. Guests just type a name; no account needed.
@Component({
  selector: 'app-join',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './join.html',
  styleUrls: ['../account/login.css', './join.css'],
})
export class JoinComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  token = '';
  loading = true;
  joining = false;
  error = '';
  crawl: any = null;
  name = '';
  teamId: string | null = null;

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    this.http.post('/api/join-preview', { token: this.token }).subscribe({
      next: (res: any) => {
        this.loading = false;
        this.crawl = res.received;
        if (this.crawl.already_joined) {
          this.router.navigate(['/event-play', this.crawl.event_id]);
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.received || "Couldn't open this invite.";
        this.cdr.detectChanges();
      },
    });
  }

  get signedInName(): string | null {
    return this.crawl?.logged_in ? (this.auth.currentUser()?.name || 'you') : null;
  }

  joinCrawl() {
    if (this.joining) return;
    if (!this.crawl?.logged_in && !this.name.trim()) {
      this.error = 'Type your name first.';
      return;
    }
    this.joining = true;
    this.error = '';
    this.http.post('/api/join', { token: this.token, name: this.name.trim(), team_id: this.teamId }).subscribe({
      next: (res: any) => {
        const p = res.received.profile;
        if (p) this.auth.setSession({ id: p.id, name: p.name, role: p.role });
        this.router.navigate(['/event-play', res.received.event_id]);
      },
      error: (err) => {
        this.joining = false;
        this.error = err?.error?.received || "Couldn't join. Try again.";
        this.cdr.detectChanges();
      },
    });
  }
}
