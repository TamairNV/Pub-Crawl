import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import {
  EventAward,
  MiniWheel,
  PlayerTask,
  WheelItem,
  formatRewardBadge,
} from '../shared/mini-events.types';
import { SpinCommand, SpinWheelComponent } from '../shared/spin-wheel/spin-wheel';
import { PasswordRevealComponent } from '../shared/password-reveal';

interface SpinModalState {
  mode: 'task' | 'direct';
  playerId: string;
  playerName: string;
  teamId?: string;
  taskId?: string;
  wheelId: string;
  wheelName: string;
  items: WheelItem[];
  spinCommand: SpinCommand | null;
  spinningBusy: boolean;
  animationDone: boolean;
  resultTask: PlayerTask | null;
  alreadySpunNote: string;
}

@Component({
  selector: 'app-ref-mini-events',
  standalone: true,
  imports: [CommonModule, FormsModule, SpinWheelComponent, PasswordRevealComponent],
  templateUrl: './ref-mini-events.html',
  styleUrl: './ref-mini-events.css',
})
export class RefMiniEventsComponent implements OnChanges {
  @Input() eventId: string | null = '';
  @Input() currentUser: any = null;
  @Input() users: any[] = [];
  @Input() teams: any[] = [];
  @Input() points: any[] = [];
  @Input() teamAdjustments: any[] = [];
  @Input() wheels: MiniWheel[] = [];
  @Input() tasks: PlayerTask[] = [];
  @Input() awards: EventAward[] = [];
  @Input() awardsSettings: { voting_open: boolean; results_visible: boolean } = {
    voting_open: true,
    results_visible: false,
  };
  @Input() awardsVotes: any = { my_votes: {}, tally: {}, votes_by_voter: {} };
  @Input() liveStateError = '';
  @Input() selectedPlayer: any | null = null;

  @Output() closePlayerModal = new EventEmitter<void>();
  @Output() stateChanged = new EventEmitter<void>();

  private http = inject(HttpClient);
  private cdr = inject(ChangeDetectorRef);

  toast = '';
  busy = false;
  showCompleted = false;

  // Player modal state
  modalTab: 'random' | 'custom' | 'spin' = 'random';
  randomWheelId = ''; // '' = any wheel
  randomRewardMode: 'item' | 'spin_wheel' = 'spin_wheel';
  randomRewardWheelId = '';

  customPrefillKey = '';
  customTitle = '';
  customDesc = '';
  customRewardType: 'spin_wheel' | 'add_points' | 'deduct_team' | 'steal_team' | 'none' = 'add_points';
  customRewardPoints = 2;
  customRewardWheelId = '';
  customWheelId = '';
  customWheelItemId = '';

  directSpinWheelId = '';

  // Spin modal state
  spinModal: SpinModalState | null = null;
  private spinSeq = 0;

  // Proxy voting state
  proxyVoterId = '';
  private proxyVoterManual = false;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['wheels'] && this.wheels.length > 0) {
      const firstId = this.wheels[0].id;
      if (!this.wheels.some((w) => w.id === this.randomRewardWheelId)) {
        this.randomRewardWheelId = firstId;
      }
      if (!this.wheels.some((w) => w.id === this.customRewardWheelId)) {
        this.customRewardWheelId = firstId;
      }
      if (!this.wheels.some((w) => w.id === this.directSpinWheelId)) {
        this.directSpinWheelId = firstId;
      }
      if (this.randomWheelId && !this.wheels.some((w) => w.id === this.randomWheelId)) {
        this.randomWheelId = '';
      }
    }

    if ((changes['users'] || changes['currentUser']) && !this.proxyVoterManual) {
      if (this.users.length > 0) {
        this.proxyVoterId = this.users[0].userID;
      } else if (this.currentUser?.id && !this.proxyVoterId) {
        this.proxyVoterId = this.currentUser.id;
      }
    }

    if (changes['selectedPlayer'] && this.selectedPlayer) {
      this.customPrefillKey = '';
      this.customWheelId = '';
      this.customWheelItemId = '';
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
    }, 3200);
  }

  // ---------- Computed helpers ----------

  playerPoints(userId: string): number {
    const p = this.points.find((x) => x.userID === userId);
    return p ? Number(p.total_points || 0) : 0;
  }

  teamStandings() {
    const adjMap: { [id: string]: number } = {};
    for (const a of this.teamAdjustments || []) {
      adjMap[a.team_id] = Number(a.adjustment || 0);
    }
    const list = (this.teams || []).map((t) => {
      const members = (this.users || []).filter((u) => u.teamID === t.id);
      const memberTotal = members.reduce((sum, m) => sum + this.playerPoints(m.userID), 0);
      const adjustment = adjMap[t.id] || 0;
      return {
        id: t.id,
        name: t.name,
        colour: t.colour || '#fbbf24',
        adjustment,
        totalPoints: memberTotal + adjustment,
      };
    });
    return list.sort((a, b) => b.totalPoints - a.totalPoints);
  }

  get activeTasks(): PlayerTask[] {
    return (this.tasks || []).filter(
      (t) => t.status === 'pending' || t.status === 'ready_to_spin' || t.status === 'awaiting_target'
    );
  }

  get completedTasks(): PlayerTask[] {
    return (this.tasks || []).filter((t) => t.status === 'completed');
  }

  get selectedPlayerTasks(): PlayerTask[] {
    if (!this.selectedPlayer) return [];
    return this.activeTasks.filter((t) => t.user_id === this.selectedPlayer.userID);
  }

  rewardBadge(task: PlayerTask): string {
    return formatRewardBadge(task.reward_type, task.reward_points, task.reward_wheel_name);
  }

  sliceBadge(item: WheelItem): string {
    return formatRewardBadge(item.effect_type, item.points);
  }

  otherTeamsFor(teamId?: string | null): any[] {
    if (!teamId) return this.teams || [];
    const others = (this.teams || []).filter((t) => t.id !== teamId);
    return others.length > 0 ? others : this.teams || [];
  }

  get allWheelSlices(): { key: string; wheel: MiniWheel; item: WheelItem }[] {
    const out: { key: string; wheel: MiniWheel; item: WheelItem }[] = [];
    for (const w of this.wheels || []) {
      for (const item of w.items || []) {
        out.push({ key: `${w.id}::${item.id}`, wheel: w, item });
      }
    }
    return out;
  }

  get totalWheelSlices(): number {
    return (this.wheels || []).reduce((sum, w) => sum + (w.items?.length || 0), 0);
  }

  // ---------- Assign tasks & wheels ----------

  onPrefillChange() {
    if (!this.customPrefillKey) {
      this.customWheelId = '';
      this.customWheelItemId = '';
      return;
    }
    const found = this.allWheelSlices.find((x) => x.key === this.customPrefillKey);
    if (!found) return;
    this.customWheelId = found.wheel.id;
    this.customWheelItemId = found.item.id;
    this.customTitle = found.item.label;
    this.customDesc = found.item.description || '';
    this.customRewardType = found.item.effect_type;
    this.customRewardPoints = Number(found.item.points || 0);
  }

  assignRandomTask() {
    if (!this.eventId || !this.selectedPlayer || this.busy) return;
    if (this.totalWheelSlices === 0) {
      this.flash('Add at least one wheel slice in Event Details first');
      return;
    }
    if (this.randomRewardMode === 'spin_wheel' && !this.randomRewardWheelId) {
      this.flash('Pick a reward wheel');
      return;
    }
    this.busy = true;
    const payload: any = {
      event_id: this.eventId,
      user_id: this.selectedPlayer.userID,
      mode: 'random',
      wheel_id: this.randomWheelId || null,
    };
    if (this.randomRewardMode === 'spin_wheel') {
      payload.reward_wheel_id = this.randomRewardWheelId;
    }
    this.http.post('/api/assign-player-task', payload).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.flash(`Sent random task to ${this.selectedPlayer.name}!`);
          this.stateChanged.emit();
        } else {
          this.flash(res.received || 'Could not assign task');
        }
      },
      error: (err) => {
        this.busy = false;
        this.flash(err?.error?.received || 'Could not assign task');
      },
    });
  }

  assignCustomTask() {
    if (!this.eventId || !this.selectedPlayer || !this.customTitle.trim() || this.busy) return;
    if (this.customRewardType === 'spin_wheel' && !this.customRewardWheelId) {
      this.flash('Create a wheel first to unlock a spin');
      return;
    }
    this.busy = true;
    this.http
      .post('/api/assign-player-task', {
        event_id: this.eventId,
        user_id: this.selectedPlayer.userID,
        mode: 'custom',
        wheel_id: this.customWheelId || null,
        wheel_item_id: this.customWheelItemId || null,
        title: this.customTitle.trim(),
        description: this.customDesc.trim(),
        reward_type: this.customRewardType,
        reward_points: Number(this.customRewardPoints || 0),
        reward_wheel_id: this.customRewardType === 'spin_wheel' ? this.customRewardWheelId : null,
      })
      .subscribe({
        next: (res: any) => {
          this.busy = false;
          if (res.status === 'success') {
            this.customTitle = '';
            this.customDesc = '';
            this.customPrefillKey = '';
            this.customWheelId = '';
            this.customWheelItemId = '';
            this.flash(`Sent task to ${this.selectedPlayer.name}!`);
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not assign task');
          }
        },
        error: (err) => {
          this.busy = false;
          this.flash(err?.error?.received || 'Could not assign task');
        },
      });
  }

  // ---------- Confirm, Cancel, Spin & Target Team ----------

  confirmTask(task: PlayerTask, targetTeamId?: string) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http
      .post('/api/confirm-player-task', {
        event_id: this.eventId,
        task_id: task.id,
        target_team_id: targetTeamId || null,
      })
      .subscribe({
        next: (res: any) => {
          this.busy = false;
          if (res.status === 'success') {
            const updated: PlayerTask = res.received.task;
            this.flash(updated?.result_summary || 'Task confirmed!');
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not confirm task');
          }
        },
        error: (err) => {
          this.busy = false;
          this.flash(err?.error?.received || 'Could not confirm task');
        },
      });
  }

  cancelTask(task: PlayerTask) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http
      .post('/api/cancel-player-task', {
        event_id: this.eventId,
        task_id: task.id,
      })
      .subscribe({
        next: (res: any) => {
          this.busy = false;
          if (res.status === 'success') {
            if (this.spinModal?.resultTask?.id === task.id) {
              this.spinModal = null;
            }
            this.flash('Task cancelled');
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not cancel task');
          }
        },
        error: () => {
          this.busy = false;
          this.flash('Could not cancel task');
        },
      });
  }

  applyTargetTeam(task: PlayerTask, targetTeamId: string) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http
      .post('/api/apply-task-target', {
        event_id: this.eventId,
        task_id: task.id,
        target_team_id: targetTeamId,
      })
      .subscribe({
        next: (res: any) => {
          this.busy = false;
          if (res.status === 'success') {
            const updated: PlayerTask = res.received.task;
            if (this.spinModal?.resultTask?.id === task.id) {
              this.spinModal.resultTask = updated;
            }
            this.flash(updated?.result_summary || 'Points updated!');
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not apply points');
          }
        },
        error: (err) => {
          this.busy = false;
          this.flash(err?.error?.received || 'Could not apply points');
        },
      });
  }

  openTaskSpinModal(task: PlayerTask) {
    const wheelId = task.reward_wheel_id || task.wheel_id || '';
    const wheel = this.wheels.find((w) => w.id === wheelId);
    if (!wheel || !wheel.items?.length) {
      this.flash('That wheel has no slices yet');
      return;
    }
    this.spinModal = {
      mode: 'task',
      playerId: task.user_id,
      playerName: task.user_name || 'Player',
      teamId: task.user_team_id,
      taskId: task.id,
      wheelId: wheel.id,
      wheelName: wheel.name,
      items: [...wheel.items],
      spinCommand: null,
      spinningBusy: false,
      animationDone: false,
      resultTask: null,
      alreadySpunNote: '',
    };
  }

  openDirectSpinModal(player: any, wheelId: string) {
    const wheel = this.wheels.find((w) => w.id === wheelId);
    if (!wheel || !wheel.items?.length) {
      this.flash('Select a wheel with at least 1 slice');
      return;
    }
    this.spinModal = {
      mode: 'direct',
      playerId: player.userID,
      playerName: player.name,
      teamId: player.teamID,
      wheelId: wheel.id,
      wheelName: wheel.name,
      items: [...wheel.items],
      spinCommand: null,
      spinningBusy: false,
      animationDone: false,
      resultTask: null,
      alreadySpunNote: '',
    };
  }

  triggerSpinModal() {
    if (!this.eventId || !this.spinModal || this.spinModal.spinningBusy) return;
    const modal = this.spinModal;
    modal.spinningBusy = true;

    const url = modal.mode === 'task' ? '/api/spin-task-wheel' : '/api/spin-direct-wheel';
    const body =
      modal.mode === 'task'
        ? { event_id: this.eventId, task_id: modal.taskId }
        : { event_id: this.eventId, user_id: modal.playerId, wheel_id: modal.wheelId };

    this.http.post(url, body).subscribe({
      next: (res: any) => {
        if (res.status !== 'success') {
          modal.spinningBusy = false;
          this.flash(res.received || 'Could not spin wheel');
          return;
        }
        const data = res.received;
        if (data.already_spun) {
          modal.spinningBusy = false;
          modal.animationDone = true;
          modal.resultTask = data.task;
          modal.alreadySpunNote = 'Already spun!';
          this.stateChanged.emit();
          this.cdr.detectChanges();
          return;
        }
        modal.resultTask = data.task;
        modal.spinCommand = {
          seq: ++this.spinSeq,
          index: data.chosen_index,
          item: data.chosen_item,
        };
        this.cdr.detectChanges();
      },
      error: (err) => {
        modal.spinningBusy = false;
        this.flash(err?.error?.received || 'Could not spin wheel');
      },
    });
  }

  onWheelAnimationFinished() {
    if (!this.spinModal) return;
    this.spinModal.spinningBusy = false;
    this.spinModal.animationDone = true;
    this.stateChanged.emit();
    this.cdr.detectChanges();
  }

  closeSpinModal() {
    if (this.spinModal?.spinningBusy && !this.spinModal?.animationDone) return;
    this.spinModal = null;
  }

  // ---------- Awards & Proxy Voting ----------

  onProxyVoterChange() {
    this.proxyVoterManual = true;
  }

  jumpToProxyVote(player: any) {
    this.proxyVoterManual = true;
    this.proxyVoterId = player.userID;
    this.closePlayerModal.emit();
    setTimeout(() => {
      document.getElementById('ref-awards-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
  }

  voterVoteCount(userId: string): number {
    const map = this.awardsVotes?.votes_by_voter?.[userId];
    return map ? Object.keys(map).length : 0;
  }

  currentProxyVoteKey(awardId: string): string {
    const v = this.awardsVotes?.votes_by_voter?.[this.proxyVoterId]?.[awardId];
    if (!v) return '';
    return `${v.nominee_type}:${v.nominee_id}`;
  }

  voterSummaryName(): string {
    const found = this.users.find((u) => u.userID === this.proxyVoterId);
    if (found) return found.name;
    if (this.currentUser?.id === this.proxyVoterId) return `${this.currentUser.name} (Ref)`;
    return 'Selected Player';
  }

  isCurrentUserParticipant(): boolean {
    return !!this.currentUser?.id && this.users.some((u) => u.userID === this.currentUser.id);
  }

  castProxyVote(award: EventAward, selectedKey: string) {
    if (!this.eventId || !this.proxyVoterId || !selectedKey) return;
    const parts = selectedKey.split(':');
    const nomineeType = parts[0] as 'player' | 'team';
    const nomineeId = parts.slice(1).join(':');
    if (!nomineeId) return;

    this.http
      .post('/api/cast-award-vote', {
        event_id: this.eventId,
        award_id: award.id,
        nominee_id: nomineeId,
        nominee_type: nomineeType,
        voter_user_id: this.proxyVoterId,
      })
      .subscribe({
        next: (res: any) => {
          if (res.status === 'success') {
            this.flash(`Saved vote for ${this.voterSummaryName()}!`);
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not save vote');
          }
        },
        error: (err) => this.flash(err?.error?.received || 'Could not save vote'),
      });
  }

  toggleAwardsSetting(field: 'voting_open' | 'results_visible') {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    const payload: any = { event_id: this.eventId };
    payload[field] = !this.awardsSettings[field];
    this.http.post('/api/set-awards-settings', payload).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.stateChanged.emit();
        } else {
          this.flash(res.received || 'Could not update setting');
        }
      },
      error: () => {
        this.busy = false;
        this.flash('Could not update setting');
      },
    });
  }

  seedDefaultAwards() {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http.post('/api/seed-default-awards', { event_id: this.eventId }).subscribe({
      next: (res: any) => {
        this.busy = false;
        if (res.status === 'success') {
          this.flash('Starter awards added!');
          this.stateChanged.emit();
        } else {
          this.flash(res.received || 'Could not add awards');
        }
      },
      error: () => {
        this.busy = false;
        this.flash('Could not add awards');
      },
    });
  }
}
