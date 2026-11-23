import {
  ChangeDetectorRef,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-password-reveal',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="pw-reveal-bar">
      <button
        type="button"
        [class]="btnClass"
        (click)="toggleReveal()"
        [disabled]="loading || !userId"
      >
        {{ loading ? 'Loading...' : (revealedPassword !== null ? '🙈 Hide Password' : '🔑 Reveal Password') }}
      </button>
      <span class="pw-secret" *ngIf="revealedPassword !== null">{{ revealedPassword }}</span>
      <span class="pw-error" *ngIf="errorMsg">{{ errorMsg }}</span>
    </div>
  `,
})
export class PasswordRevealComponent implements OnChanges {
  @Input() userId: string | null = null;
  @Input() eventId: string | null | undefined = null;
  @Input() btnClass = 'btn btn-secondary btn-sm';

  private http = inject(HttpClient);
  private cdr = inject(ChangeDetectorRef);

  revealedPassword: string | null = null;
  loading = false;
  errorMsg = '';

  ngOnChanges(changes: SimpleChanges) {
    if (changes['userId'] || changes['eventId']) {
      this.revealedPassword = null;
      this.errorMsg = '';
      this.loading = false;
    }
  }

  toggleReveal() {
    if (!this.userId || this.loading) return;
    if (this.revealedPassword !== null) {
      this.revealedPassword = null;
      this.errorMsg = '';
      return;
    }
    this.loading = true;
    this.errorMsg = '';
    this.http
      .post('/api/reveal-password', {
        user_id: this.userId,
        event_id: this.eventId || null,
      })
      .subscribe({
        next: (res: any) => {
          this.loading = false;
          if (res.status === 'success' && res.received) {
            this.revealedPassword = String(res.received.password ?? '');
          } else {
            this.errorMsg = res.received || 'Could not reveal password';
          }
          this.cdr.detectChanges();
        },
        error: (err) => {
          this.loading = false;
          this.errorMsg = err?.error?.received || 'Could not reveal password';
          this.cdr.detectChanges();
        },
      });
  }
}
