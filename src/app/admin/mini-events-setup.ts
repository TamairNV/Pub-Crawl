import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { EventAward, MiniWheel, WheelItem, formatRewardBadge } from '../shared/mini-events.types';

const PALETTE = ['#fbbf24', '#60a5fa', '#34d399', '#f87171', '#c084fc', '#fb923c', '#2dd4bf', '#f472b6'];

interface ItemDraft {
  label: string;
  description: string;
  requires_completion: boolean;
  effect_choice: 'add_points' | 'deduct_player' | 'deduct_team' | 'steal_team' | 'none';
  points: number;
  colour: string;
}

@Component({
  selector: 'app-mini-events-setup',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './mini-events-setup.html',
  styleUrl: './mini-events-setup.css',
})
export class MiniEventsSetupComponent implements OnChanges {
  @Input() eventId: string | null = '';
  @Output() countsChanged = new EventEmitter<{ wheels: number; awards: number }>();

  private http = inject(HttpClient);
  private cdr = inject(ChangeDetectorRef);

  wheels: MiniWheel[] = [];
  awards: EventAward[] = [];
  busy = false;
  toast = '';
  schemaError = '';

  // New wheel form
  newWheelName = '';
  newWheelDesc = '';

  // Per-wheel item draft
  drafts: { [wheelId: string]: ItemDraft } = {};

  // New award form
  newAwardName = '';
  newAwardDesc = '';
  newAwardTarget: 'player' | 'team' | 'either' = 'player';

  ngOnChanges(changes: SimpleChanges) {
    if (changes['eventId'] && this.eventId) {
      this.loadMiniEvents();
    }
  }

  private flash(msg: string) {
    this.toast = msg;
    this.cdr.detectChanges();
    setTimeout(() => {
      if (this.toast === msg) {
        this.toast = '';
        this.cdr.detectChanges();
      }
    }, 3000);
  }

  loadMiniEvents() {
    if (!this.eventId) return;
    this.http.post('/api/get-mini-events', { event_id: this.eventId }).subscribe({
      next: (res: any) => {
        if (res.status === 'success') {
          this.schemaError = '';
          this.wheels = res.received.wheels || [];
          this.awards = res.received.awards || [];
          for (const w of this.wheels) {
            if (!this.drafts[w.id]) {
              this.resetDraft(w.id, w.items.length);
            }
          }
          this.countsChanged.emit({ wheels: this.wheels.length, awards: this.awards.length });
          this.cdr.detectChanges();
        } else {
          this.schemaError = res.received || 'Could not load mini events.';
          this.cdr.detectChanges();
        }
      },
      error: (err) => {
        this.schemaError = err?.status === 500
          ? 'Mini-events database tables are not created yet. Run the DB migration script on the server.'
          : (err?.error?.received || 'Could not load mini events.');
        this.cdr.detectChanges();
      },
    });
  }

  private resetDraft(wheelId: string, count: number) {
    this.drafts[wheelId] = {
      label: '',
      description: '',
      requires_completion: true,
      effect_choice: 'add_points',
      points: 2,
      colour: PALETTE[count % PALETTE.length],
    };
  }

  draftFor(wheel: MiniWheel): ItemDraft {
    if (!this.drafts[wheel.id]) {
      this.resetDraft(wheel.id, wheel.items.length);
    }
    return this.drafts[wheel.id];
  }

  describeItem(item: WheelItem): string {
    return formatRewardBadge(item.effect_type, item.points);
  }

  createWheel() {
    const name = this.newWheelName.trim();
    if (!name || !this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/create-wheel', {
      event_id: this.eventId,
      name,
      description: this.newWheelDesc.trim(),
    }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.newWheelName = '';
          this.newWheelDesc = '';
          this.loadMiniEvents();
          this.flash(`Wheel "${name}" added`);
        } else {
          this.flash('Could not create wheel');
        }
      },
      error: () => { this.busy = false; this.flash('Could not create wheel'); },
    });
  }

  deleteWheel(wheel: MiniWheel) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/delete-wheel', { event_id: this.eventId, wheel_id: wheel.id }).subscribe({
      next: () => {
        this.busy = false;
        this.loadMiniEvents();
        this.flash(`Deleted ${wheel.name}`);
      },
      error: () => { this.busy = false; },
    });
  }

  addWheelItem(wheel: MiniWheel) {
    const d = this.draftFor(wheel);
    const label = d.label.trim();
    if (!label || !this.eventId || this.busy) return;

    let effect_type: WheelItem['effect_type'] = 'add_points';
    let points = Math.abs(Number(d.points || 0));
    if (d.effect_choice === 'deduct_player') {
      effect_type = 'add_points';
      points = -points;
    } else if (d.effect_choice === 'deduct_team') {
      effect_type = 'deduct_team';
    } else if (d.effect_choice === 'steal_team') {
      effect_type = 'steal_team';
    } else if (d.effect_choice === 'none') {
      effect_type = 'none';
      points = 0;
    }

    this.busy = true;
    this.http.post('/api/add-wheel-item', {
      event_id: this.eventId,
      wheel_id: wheel.id,
      label,
      description: d.description.trim(),
      requires_completion: d.requires_completion,
      effect_type,
      points,
      colour: d.colour,
    }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.resetDraft(wheel.id, wheel.items.length + 1);
          this.loadMiniEvents();
          this.flash('Task added to wheel');
        } else {
          this.flash('Could not add item');
        }
      },
      error: () => { this.busy = false; this.flash('Could not add item'); },
    });
  }

  deleteWheelItem(item: WheelItem) {
    if (!this.eventId || this.busy) return;
    this.http.post('/api/delete-wheel-item', { event_id: this.eventId, item_id: item.id }).subscribe({
      next: () => this.loadMiniEvents(),
    });
  }

  seedWheelItems(wheel: MiniWheel) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/seed-wheel-items', { event_id: this.eventId, wheel_id: wheel.id }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.loadMiniEvents();
          this.flash('Added starter wheel tasks');
        } else {
          this.flash(res.received || 'Could not add starter tasks');
        }
      },
      error: () => { this.busy = false; this.flash('Could not add starter tasks'); },
    });
  }

  createAward() {
    const name = this.newAwardName.trim();
    if (!name || !this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/create-award', {
      event_id: this.eventId,
      name,
      description: this.newAwardDesc.trim(),
      target_type: this.newAwardTarget,
    }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.newAwardName = '';
          this.newAwardDesc = '';
          this.loadMiniEvents();
          this.flash(`Award "${name}" added`);
        } else {
          this.flash(res.received || 'Could not add award');
        }
      },
      error: () => { this.busy = false; this.flash('Could not add award'); },
    });
  }

  seedAwards() {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/seed-default-awards', { event_id: this.eventId }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.loadMiniEvents();
          this.flash('Starter awards added');
        } else {
          this.flash(res.received || 'Could not add starter awards');
        }
      },
      error: () => { this.busy = false; this.flash('Could not add starter awards'); },
    });
  }

  deleteAward(award: EventAward) {
    if (!this.eventId || this.busy) return;
    this.http.post('/api/delete-award', { event_id: this.eventId, award_id: award.id }).subscribe({
      next: (res: any) => {
        if (res.status === 'success') {
          this.loadMiniEvents();
        } else {
          this.flash(res.received || 'Could not delete award');
        }
      },
      error: () => this.flash('Could not delete award'),
    });
  }

  targetLabel(t: string): string {
    if (t === 'team') return 'Teams';
    if (t === 'either') return 'Players or Teams';
    return 'Players';
  }
}
