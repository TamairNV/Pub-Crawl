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

interface ActiveSpinState {
  taskId: string;
  title: string;
  wheelName: string;
  items: WheelItem[];
  spinCommand: SpinCommand | null;
  spinning: boolean;
  done: boolean;
  resultTask: PlayerTask | null;
  alreadySpunNote: string;
}

@Component({
  selector: 'app-player-mini-events',
  standalone: true,
  imports: [CommonModule, FormsModule, SpinWheelComponent],
  templateUrl: './player-mini-events.html',
  styleUrl: './player-mini-events.css',
})
export class PlayerMiniEventsComponent implements OnChanges {
  @Input() eventId: string | null = '';
  @Input() currentUser: any = null;
  @Input() users: any[] = [];
  @Input() teams: any[] = [];
  @Input() wheels: MiniWheel[] = [];
  @Input() tasks: PlayerTask[] = [];
  @Input() awards: EventAward[] = [];
  @Input() awardsSettings: { voting_open: boolean; results_visible: boolean } = {
    voting_open: true,
    results_visible: false,
  };
  @Input() awardsVotes: any = { my_votes: {}, tally: {} };

  @Output() stateChanged = new EventEmitter<void>();

  private http = inject(HttpClient);
  private cdr = inject(ChangeDetectorRef);

  toast = '';
  busy = false;
  minimizedSignatures: { [sig: string]: boolean } = {};
  spinningState: ActiveSpinState | null = null;
  private spinSeq = 0;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['tasks'] && this.spinningState && !this.spinningState.spinning && this.spinningState.done) {
      // Keep resultTask synced with latest status once animation finishes
      const latest = (this.tasks || []).find((t) => t.id === this.spinningState?.taskId);
      if (latest && latest.status === 'completed' && this.spinningState.resultTask?.status !== 'completed') {
        this.spinningState.resultTask = latest;
      }
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

  get activeTasks(): PlayerTask[] {
    return (this.tasks || []).filter(
      (t) => t.status === 'pending' || t.status === 'ready_to_spin' || t.status === 'awaiting_target'
    );
  }

  get completedTasks(): PlayerTask[] {
    return (this.tasks || []).filter((t) => t.status === 'completed');
  }

  get popupTask(): PlayerTask | null {
    if (this.spinningState) return null;
    for (const t of this.activeTasks) {
      const sig = `${t.id}:${t.status}`;
      if (!this.minimizedSignatures[sig]) {
        return t;
      }
    }
    return null;
  }

  minimizeTaskPopup(task: PlayerTask) {
    this.minimizedSignatures[`${task.id}:${task.status}`] = true;
  }

  reopenTaskPopup(task: PlayerTask) {
    delete this.minimizedSignatures[`${task.id}:${task.status}`];
  }

  rewardBadge(task: PlayerTask): string {
    return formatRewardBadge(task.reward_type, task.reward_points, task.reward_wheel_name);
  }

  wheelForTask(task: PlayerTask): MiniWheel | undefined {
    const wid = task.reward_wheel_id || task.wheel_id;
    return (this.wheels || []).find((w) => w.id === wid);
  }

  otherTeams(): any[] {
    const me = (this.users || []).find((u) => u.userID === this.currentUser?.id);
    const myTeamId = me?.teamID;
    if (!myTeamId) return this.teams || [];
    const others = (this.teams || []).filter((t) => t.id !== myTeamId);
    return others.length > 0 ? others : this.teams || [];
  }

  claimDone(task: PlayerTask) {
    if (!this.eventId || this.busy) return;
    this.busy = true;
    this.http
      .post('/api/claim-task-done', {
        event_id: this.eventId,
        task_id: task.id,
      })
      .subscribe({
        next: (res: any) => {
          this.busy = false;
          if (res.status === 'success') {
            task.player_claimed_done = true;
            this.flash('Ref notified! Waiting for confirmation.');
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not notify ref');
          }
        },
        error: () => {
          this.busy = false;
          this.flash('Could not notify ref');
        },
      });
  }

  startSpinOverlay(task: PlayerTask) {
    const wheel = this.wheelForTask(task);
    if (!wheel || !wheel.items?.length) {
      this.flash('Wheel has no items yet');
      return;
    }
    this.spinningState = {
      taskId: task.id,
      title: task.title,
      wheelName: wheel.name,
      items: [...wheel.items],
      spinCommand: null,
      spinning: false,
      done: false,
      resultTask: null,
      alreadySpunNote: '',
    };
  }

  triggerTaskSpin() {
    if (!this.eventId || !this.spinningState || this.spinningState.spinning) return;
    const s = this.spinningState;
    s.spinning = true;
    this.http
      .post('/api/spin-task-wheel', {
        event_id: this.eventId,
        task_id: s.taskId,
      })
      .subscribe({
        next: (res: any) => {
          if (res.status !== 'success') {
            s.spinning = false;
            this.flash(res.received || 'Could not spin wheel');
            return;
          }
          const data = res.received;
          if (data.already_spun) {
            s.spinning = false;
            s.done = true;
            s.resultTask = data.task;
            s.alreadySpunNote = 'Already spun (possibly by the ref)!';
            this.stateChanged.emit();
            this.cdr.detectChanges();
            return;
          }
          s.resultTask = data.task;
          s.spinCommand = {
            seq: ++this.spinSeq,
            index: data.chosen_index,
            item: data.chosen_item,
          };
          this.cdr.detectChanges();
        },
        error: (err) => {
          s.spinning = false;
          this.flash(err?.error?.received || 'Could not spin wheel');
        },
      });
  }

  onSpinAnimationDone() {
    if (!this.spinningState) return;
    this.spinningState.spinning = false;
    this.spinningState.done = true;
    this.stateChanged.emit();
    this.cdr.detectChanges();
  }

  closeSpinOverlay() {
    if (this.spinningState?.spinning && !this.spinningState.done) return;
    this.spinningState = null;
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
            if (this.spinningState?.taskId === task.id) {
              this.spinningState.resultTask = updated;
            }
            this.flash(updated?.result_summary || 'Applied!');
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

  // ---------- Awards ----------

  myVoteKey(awardId: string): string {
    const v = this.awardsVotes?.my_votes?.[awardId];
    if (!v) return '';
    return `${v.nominee_type}:${v.nominee_id}`;
  }

  myVoteLabel(awardId: string): string {
    const v = this.awardsVotes?.my_votes?.[awardId];
    if (!v) return '';
    if (v.nominee_type === 'team') {
      const tm = (this.teams || []).find((t) => t.id === v.nominee_id);
      return tm ? `${tm.name} Team` : 'Selected Team';
    }
    const u = (this.users || []).find((x) => x.userID === v.nominee_id);
    return u ? u.name : 'Selected Player';
  }

  castMyVote(award: EventAward, selectedKey: string) {
    if (!this.eventId || !selectedKey) return;
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
      })
      .subscribe({
        next: (res: any) => {
          if (res.status === 'success') {
            if (!this.awardsVotes.my_votes) this.awardsVotes.my_votes = {};
            this.awardsVotes.my_votes[award.id] = { nominee_id: nomineeId, nominee_type: nomineeType };
            this.flash(`Vote saved for ${award.name}!`);
            this.stateChanged.emit();
          } else {
            this.flash(res.received || 'Could not save vote');
          }
        },
        error: (err) => this.flash(err?.error?.received || 'Could not save vote'),
      });
  }
}
