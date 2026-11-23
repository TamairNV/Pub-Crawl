import { Component, computed, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { OfflineService } from './offline.service';

@Component({
  selector: 'app-offline-badge',
  standalone: true,
  imports: [CommonModule, DatePipe],
  template: `
    <button type="button" class="offline-badge" *ngIf="show()" [class.ok]="off.online()" (click)="off.flush()">
      <ng-container *ngIf="!off.online(); else syncing">
        OFFLINE<span *ngIf="off.pending()"> · {{ off.pending() }} pending</span>
        <small *ngIf="off.lastLive()"> · updated {{ off.lastLive() | date:'HH:mm' }}</small>
      </ng-container>
      <ng-template #syncing>Syncing {{ off.pending() }}…</ng-template>
    </button>
  `,
  styles: [`
    .offline-badge {
      position: fixed; left: 50%; transform: translateX(-50%); bottom: calc(12px + env(safe-area-inset-bottom));
      z-index: 1000; background: #ef4444; color: #fff; border: 3px solid #111827; border-radius: 999px;
      box-shadow: 3px 3px 0 #111827; padding: .55rem 1.1rem; font: 900 1rem "Nunito", system-ui, sans-serif;
      letter-spacing: .03em; white-space: nowrap; cursor: pointer;
    }
    .offline-badge.ok { background: #fbbf24; color: #111827; }
    small { font-weight: 700; }
  `],
})
export class OfflineBadgeComponent {
  off = inject(OfflineService);
  show = computed(() => !this.off.online() || this.off.pending() > 0);
}
