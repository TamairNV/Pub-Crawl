import { Component, Input, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';

interface PaymentState {
  available: boolean;
  stripe?: boolean;
  paid?: boolean;
  tier?: string | null;
  team_count?: number;
  free_team_limit?: number;
  enforced?: boolean;
  tiers?: { [key: string]: { amount: number; label: string } };
}

// "Unlock this crawl" card on Crawl Setup. Hidden until payments are set up on the server
// (Stripe keys + migration). Only the signed Stripe webhook marks a crawl paid; the
// ?paid=1 return just shows a waiting message and polls the status.
@Component({
  selector: 'app-unlock-crawl',
  standalone: true,
  template: `
    @if (state(); as s) {
      @if (s.available) {
        <section class="unlock" [class.unlocked]="s.paid">
          @if (s.paid) {
            <h3>✓ Crawl unlocked</h3>
            <p>{{ tierLabel(s.tier) }}: unlimited teams. Cheers!</p>
          } @else if (waiting()) {
            <h3>Payment received?</h3>
            <p>Unlocking your crawl… this takes a few seconds.</p>
          } @else {
            <h3>Unlock this crawl</h3>
            <p>Free crawls get up to {{ s.free_team_limit }} teams (you have {{ s.team_count }}). Unlock for unlimited teams.</p>
            @if (s.stripe) {
            <div class="tiers">
              @for (key of tierKeys(s); track key) {
                <button type="button" class="tier-btn" [disabled]="busy()" (click)="buy(key)">
                  {{ s.tiers![key].label }}<strong>{{ price(s.tiers![key].amount) }}</strong>
                </button>
              }
            </div>
            }
            <form class="code-form" (submit)="redeem($event, codeInput.value)">
              <input #codeInput class="code-input" name="code" placeholder="Got a code?" autocomplete="off" autocapitalize="characters">
              <button type="submit" class="code-btn" [disabled]="busy()">Use code</button>
            </form>
            @if (cancelled()) { <p class="note">Payment cancelled. Nothing was charged.</p> }
            @if (error()) { <p class="error">{{ error() }}</p> }
          }
        </section>
      }
    }
  `,
  styles: [`
    .unlock {
      margin: 1.5rem 0; padding: 1.25rem; border: 4px solid #111827; border-radius: 16px;
      background: #fef3c7; box-shadow: 6px 6px 0 #111827; color: #111827;
    }
    .unlock.unlocked { background: #dcfce7; }
    h3 { margin: 0 0 .5rem; font-size: 1.6rem; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }
    p { margin: 0 0 1rem; font-size: 1.15rem; font-weight: 700; }
    .tiers { display: flex; flex-wrap: wrap; gap: 1rem; }
    .tier-btn {
      flex: 1 1 12rem; min-height: 4.5rem; padding: .75rem 1rem; font-size: 1.25rem; font-weight: 900;
      border: 4px solid #111827; border-radius: 14px; background: #fbbf24; color: #111827; cursor: pointer;
      box-shadow: 4px 4px 0 #111827; display: flex; flex-direction: column; align-items: center; gap: .25rem;
      touch-action: manipulation;
    }
    .tier-btn strong { font-size: 1.6rem; }
    .tier-btn:active { transform: translate(3px, 3px); box-shadow: 1px 1px 0 #111827; }
    .tier-btn:disabled { opacity: .6; cursor: wait; }
    .note { margin: 1rem 0 0; }
    .code-form { display: flex; gap: .6rem; margin-top: 1rem; }
    .code-input { flex: 1; min-width: 0; padding: .8rem 1rem; font: 900 max(16px, 1.2rem) inherit; font-family: inherit;
      letter-spacing: .12em; text-transform: uppercase; border: 3px solid #111827; border-radius: 12px; }
    .code-btn { min-width: 6.5rem; border: 3px solid #111827; border-radius: 12px; background: #bbf7d0; font: 900 1.05rem inherit;
      font-family: inherit; box-shadow: 3px 3px 0 #111827; }
    .error { margin: 1rem 0 0; color: #b91c1c; }
  `]
})
export class UnlockCrawlComponent implements OnInit, OnDestroy {
  @Input({ required: true }) eventId!: string;

  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);

  state = signal<PaymentState | null>(null);
  busy = signal(false);
  waiting = signal(false);
  cancelled = signal(false);
  error = signal('');
  private pollTimer: any = null;
  private polls = 0;

  ngOnInit() {
    const paid = this.route.snapshot.queryParamMap.get('paid');
    this.waiting.set(paid === '1');
    this.cancelled.set(paid === '0');
    this.load();
  }

  ngOnDestroy() {
    if (this.pollTimer) { clearTimeout(this.pollTimer); }
  }

  redeem(ev: Event, code: string) {
    ev.preventDefault();
    if (!code.trim() || this.busy()) return;
    this.busy.set(true); this.error.set('');
    this.http.post<any>('/api/redeem-access-code', { event_id: this.eventId, code }).subscribe({
      next: () => { this.busy.set(false); this.load(); },
      error: (err) => { this.busy.set(false); this.error.set(err?.error?.received || "That code doesn't work."); },
    });
  }

  load() {
    this.http.post<any>('/api/payments/status', { event_id: this.eventId }).subscribe({
      next: (res) => {
        const s: PaymentState = res?.received || { available: false };
        this.state.set(s);
        if (this.waiting() && !s.paid) {
          if (this.polls++ < 20) {
            this.pollTimer = setTimeout(() => this.load(), 3000);
          } else {
            this.waiting.set(false);
            this.error.set('Still waiting for Stripe. Refresh in a minute; if it says not paid, nothing was charged twice.');
          }
        } else {
          this.waiting.set(false);
        }
      },
      error: () => this.state.set({ available: false })
    });
  }

  buy(tier: string) {
    this.busy.set(true);
    this.error.set('');
    this.http.post<any>('/api/payments/checkout', { event_id: this.eventId, tier }).subscribe({
      next: (res) => {
        const url = res?.received?.url;
        if (url) { window.location.href = url; } else { this.fail(res?.received); }
      },
      error: (err) => this.fail(err?.error?.received)
    });
  }

  private fail(msg?: string) {
    this.busy.set(false);
    this.error.set(msg || 'Could not start the payment. Try again.');
  }

  tierKeys(s: PaymentState) { return Object.keys(s.tiers || {}); }
  tierLabel(t?: string | null) { return t === 'code' ? 'Unlocked with a code' : ((t && this.state()?.tiers?.[t]?.label) || 'Paid crawl'); }
  price(pence: number) { return '£' + (pence / 100).toFixed(2).replace(/\.00$/, ''); }
}
