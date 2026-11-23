import {Component, inject, OnInit, ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { MiniEventsSetupComponent } from './mini-events-setup';
import { AuthService } from '../auth';
import { PasswordRevealComponent } from '../shared/password-reveal';
import { UnlockCrawlComponent } from '../shared/unlock-crawl';

// Colours offered for new teams, in order
const TEAM_COLOURS = ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#ec4899', '#14b8a6', '#f97316'];
const TEAM_NAMES = ['Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Pink', 'Teal', 'Orange'];

@Component({
  selector: 'app-event-details',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MiniEventsSetupComponent, PasswordRevealComponent, UnlockCrawlComponent],
  templateUrl: './event-details.html',
  styleUrl: './event-details.css'
})
export class EventDetailsComponent implements OnInit {
  constructor(private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}
  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);

  showResetModal = false;
  resetClearMedia = true;
  resetting = false;
  resetError = '';

  currentEventID: string | null = '';
  eventName = '';

  userDetails: any[] = [];      // players in this crawl
  teams: any[] = [];
  people: any[] = [];           // everyone, for adding players
  baseRules: any[] = [];
  locationsRules: any[] = [];   // pubs in order (rule fields may be empty)

  // Step 1: teams
  newTeamName = '';
  newTeamColor = TEAM_COLOURS[0];

  // Step 2: players
  playerSearch = '';
  picked: { [id: string]: boolean } = {};
  addToTeam = '__even__';
  inspectPlayerId: string | null = null;

  togglePlayerInspector(user: any) {
    this.inspectPlayerId = this.inspectPlayerId === user.userID ? null : user.userID;
  }

  // Step 3: pubs
  newLocationName = '';
  newLocationRule = '';
  newLocationRuleDescription = '';
  showPubRule = false;

  // Editing a rule on an existing pub
  editingPubId: string | null = null;
  editPubRuleName = '';
  editPubRuleDescription = '';

  // Step 4: rules (whole crawl or specific pub)
  newBaseRule = '';
  newBaseRuleDescription = '';
  newRulePubId = '';

  // Steps 5 & 6 counts
  wheelCount = 0;
  awardCount = 0;

  message = '';
  busy = false;

  // Refs: organiser + co-refs
  refs: any[] = [];
  canChangeRefs = false;
  newRefName = '';
  refMessage = '';

  // QR / link invites
  joinUrl = '';
  qrSrc = '';
  maxPlayers = 60;
  joinPlayers = 0;
  joinHardMax = 300;
  joinMessage = '';
  copied = false;

  ngOnInit() {
    this.http.get('/api/me').subscribe({
      next: (res: any) => {
        const cur = this.authService.getSession()();
        if (res.status === 'success') {
          this.authService.setSession({
            ...(cur || {}),
            id: res.received.id,
            name: res.received.name,
            role: res.received.role
          });
          this.cdr.detectChanges();
        }
      },
      error: () => {}
    });
    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      this.refreshAll();
      this.loadRefs();
      this.loadJoinInfo();
    });
  }

  loadJoinInfo() {
    if (!this.currentEventID) return;
    this.http.post('/api/join-info', { event_id: this.currentEventID }).subscribe({
      next: (res: any) => {
        if (res.status !== 'success') return;
        this.joinUrl = res.received.url;
        this.maxPlayers = res.received.max_players;
        this.joinPlayers = res.received.players;
        this.joinHardMax = res.received.hard_max;
        this.qrSrc = `/api/join-qr.svg?event_id=${encodeURIComponent(this.currentEventID || '')}&t=${res.received.token.slice(0, 6)}`;
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  copyJoinUrl() {
    navigator.clipboard?.writeText(this.joinUrl).then(() => {
      this.copied = true; this.cdr.detectChanges();
      setTimeout(() => { this.copied = false; this.cdr.detectChanges(); }, 2000);
    });
  }

  regenerateJoinLink() {
    if (!confirm('Make a new invite link? The old QR code and link stop working.')) return;
    this.http.post('/api/regenerate-join-link', { event_id: this.currentEventID }).subscribe({
      next: () => { this.joinMessage = 'New link made. Share the new QR code.'; this.loadJoinInfo(); },
      error: (err) => { this.joinMessage = err?.error?.received || 'Could not make a new link.'; this.cdr.detectChanges(); }
    });
  }

  savePlayerCap() {
    this.http.post('/api/set-player-cap', { event_id: this.currentEventID, max_players: this.maxPlayers }).subscribe({
      next: () => { this.joinMessage = `Player limit set to ${this.maxPlayers}.`; this.cdr.detectChanges(); },
      error: (err) => { this.joinMessage = err?.error?.received || 'Could not save.'; this.cdr.detectChanges(); }
    });
  }

  loadRefs() {
    if (!this.currentEventID) return;
    this.http.post('/api/event-refs', { event_id: this.currentEventID }).subscribe({
      next: (res: any) => {
        if (res.status === 'success') {
          this.refs = res.received.refs || [];
          this.canChangeRefs = !!res.received.can_change;
          this.cdr.detectChanges();
        }
      },
      error: () => {}
    });
  }

  addRef() {
    const name = this.newRefName.trim();
    if (!name) return;
    this.refMessage = '';
    this.http.post('/api/add-event-ref', { event_id: this.currentEventID, name }).subscribe({
      next: (res: any) => {
        if (res.status === 'success') { this.refs = res.received; this.newRefName = ''; }
        else { this.refMessage = res.received; }
        this.cdr.detectChanges();
      },
      error: (err) => { this.refMessage = err?.error?.received || 'Could not add that ref.'; this.cdr.detectChanges(); }
    });
  }

  removeRef(r: any) {
    this.http.post('/api/remove-event-ref', { event_id: this.currentEventID, user_id: r.id }).subscribe({
      next: (res: any) => { if (res.status === 'success') { this.refs = res.received; this.cdr.detectChanges(); } },
      error: (err) => { this.refMessage = err?.error?.received || 'Could not remove that ref.'; this.cdr.detectChanges(); }
    });
  }

  openResetModal() {
    this.resetClearMedia = true;
    this.resetError = '';
    this.showResetModal = true;
  }

  closeResetModal() {
    if (this.resetting) return;
    this.showResetModal = false;
  }

  confirmResetCrawl() {
    if (!this.currentEventID || this.resetting) return;
    this.resetting = true;
    this.resetError = '';
    this.http.post('/api/reset-event', {
      event_id: this.currentEventID,
      clear_media: this.resetClearMedia
    }).subscribe({
      next: (res: any) => {
        this.resetting = false;
        if (res.status === 'success') {
          const c = res.received || {};
          this.showResetModal = false;
          this.refreshAll();
          this.flash(
            `Reset complete (${c.points || 0} pts, ${c.team_points || 0} team pts, ${c.tasks || 0} tasks, ${c.votes || 0} votes${this.resetClearMedia ? `, ${c.photos || 0} media` : ''} cleared).`
          );
        } else {
          this.resetError = res.received || 'Could not reset crawl scores.';
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.resetting = false;
        this.resetError = err?.error?.received || 'Could not reset crawl scores.';
        this.cdr.detectChanges();
      }
    });
  }

  onMiniCountsChanged(counts: { wheels: number; awards: number }) {
    this.wheelCount = counts.wheels;
    this.awardCount = counts.awards;
    this.cdr.detectChanges();
  }

  refreshAll() {
    this.getEventDetails();
    this.getLocationRules();
    this.getBaseRules();
    this.getUsers();
  }

  scrollTo(sectionId: string) {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  flash(text: string) {
    this.message = text;
    this.cdr.detectChanges();
    setTimeout(() => { if (this.message === text) { this.message = ''; this.cdr.detectChanges(); } }, 3000);
  }

  // ---------- progress ----------
  get pubs() {
    return this.locationsRules;
  }

  pubsWithRules() {
    return this.pubs.filter(p => p.ruleName);
  }

  totalRulesCount() {
    return this.baseRules.length + this.pubsWithRules().length;
  }

  isReady() {
    return this.teams.length > 0 && this.userDetails.length > 0 && this.pubs.length > 0;
  }

  teamColour(teamId: string) {
    return this.teams.find(t => t.id === teamId)?.colour || '#d1d5db';
  }

  teamSize(teamId: string) {
    return this.userDetails.filter(u => u.teamID === teamId).length;
  }

  // ---------- loading ----------
  getEventDetails() {
    this.http.post('/api/get-event-details', { event_id: this.currentEventID }).subscribe({
      next: (response: any) => {
        if (response.status == 'success') {
          this.userDetails = response.received.users || [];
          this.teams = response.received.teams || [];
          this.eventName = response.received.event?.name || '';
          this.newTeamColor = this.nextColour();
          this.cdr.detectChanges();
        }
      }
    });
  }

  getBaseRules() {
    this.http.post('/api/get-base-rules', { event_id: this.currentEventID }).subscribe({
      next: (response: any) => {
        this.baseRules = response.status == 'success' ? response.received : [];
        this.cdr.detectChanges();
      }
    });
  }

  getLocationRules() {
    this.http.post('/api/get-locations-rules', { event_id: this.currentEventID }).subscribe({
      next: (response: any) => {
        this.locationsRules = response.status == 'success' ? response.received : [];
        this.cdr.detectChanges();
      }
    });
  }

  getUsers() {
    this.http.get('/api/get-users').subscribe({
      next: (response: any) => {
        if (Array.isArray(response)) {
          this.people = response;
          this.cdr.detectChanges();
        }
      }
    });
  }

  // ---------- step 1: teams ----------
  nextColour() {
    const used = new Set(this.teams.map(t => String(t.colour).toLowerCase()));
    return TEAM_COLOURS.find(c => !used.has(c)) || TEAM_COLOURS[this.teams.length % TEAM_COLOURS.length];
  }

  addTeam(name: string = this.newTeamName, colour: string = this.newTeamColor, after?: () => void) {
    name = name.trim();
    if (!name) {
      return;
    }
    this.http.post('/api/save-new-team', { name, colour, event_id: this.currentEventID }).subscribe({
      next: (response: any) => {
        if (response.status == 'success') {
          this.newTeamName = '';
          if (after) { after(); } else { this.getEventDetails(); this.flash(`Team ${name} added`); }
        }
      }
    });
  }

  quickTeams(count: number) {
    let done = 0;
    for (let i = 0; i < count; i++) {
      this.addTeam(`${TEAM_NAMES[i]} Team`, TEAM_COLOURS[i], () => {
        done++;
        if (done === count) { this.getEventDetails(); this.flash(`${count} teams added`); }
      });
    }
  }

  // ---------- step 2: players ----------
  availablePeople() {
    const inCrawl = new Set(this.userDetails.map(u => u.userID));
    const q = this.playerSearch.trim().toLowerCase();
    return this.people
      .filter(p => !inCrawl.has(p.id))
      .filter(p => !q || String(p.name).toLowerCase().includes(q))
      .sort((a, b) => String(a.name).localeCompare(String(b.name)));
  }

  pickedCount() {
    return this.availablePeople().filter(p => this.picked[p.id]).length;
  }

  pickAllShown(value: boolean) {
    for (const p of this.availablePeople()) {
      this.picked[p.id] = value;
    }
  }

  addPickedPlayers() {
    const chosen = this.availablePeople().filter(p => this.picked[p.id]);
    if (!chosen.length || !this.teams.length || this.busy) {
      return;
    }
    // "Spread evenly" puts each new player in the team with the fewest players so far
    const sizes: { [id: string]: number } = {};
    for (const t of this.teams) { sizes[t.id] = this.teamSize(t.id); }
    const payload = chosen.map(p => {
      let teamId = this.addToTeam;
      if (teamId === '__even__') {
        teamId = this.teams.reduce((a, b) => (sizes[b.id] < sizes[a.id] ? b : a)).id;
      }
      sizes[teamId]++;
      return { userId: p.id, eventId: this.currentEventID, teamId };
    });

    this.busy = true;
    this.http.post('/api/save-people-to-event', payload).subscribe({
      next: (response: any) => {
        this.busy = false;
        if (response.status == 'success') {
          this.picked = {};
          this.playerSearch = '';
          this.getEventDetails();
          this.flash(`${payload.length} player${payload.length === 1 ? '' : 's'} added`);
        } else {
          this.flash('Could not add those players');
        }
      },
      error: () => { this.busy = false; this.flash('Could not add those players'); }
    });
  }

  changeTeam(user: any, newTeamId: string) {
    this.http.post('/api/update-user-team', {
      user_id: user.userID, event_id: this.currentEventID, new_team_id: newTeamId
    }).subscribe({
      next: () => { this.getEventDetails(); this.flash(`${user.name} moved`); }
    });
  }

  removeUser(user: any) {
    this.http.post('/api/remove-user', { user_id: user.userID, event_id: this.currentEventID }).subscribe({
      next: () => { this.getEventDetails(); this.flash(`${user.name} removed`); }
    });
  }

  // ---------- step 3: pubs ----------
  saveLocation() {
    const name = this.newLocationName.trim();
    if (!name || this.busy) {
      return;
    }
    this.busy = true;
    this.http.post('/api/add-new-location', { event_id: this.currentEventID, name }).subscribe({
      next: (response: any) => {
        this.busy = false;
        if (response.status != 'success') {
          this.flash('Could not add that pub');
          return;
        }
        const ruleName = this.newLocationRule.trim();
        if (ruleName) {
          this.http.post('/api/add-new-rule', {
            pub_id: response.received, name: ruleName,
            description: this.newLocationRuleDescription.trim(), event_id: this.currentEventID
          }).subscribe({ next: () => this.getLocationRules() });
        } else {
          this.getLocationRules();
        }
        this.newLocationName = '';
        this.newLocationRule = '';
        this.newLocationRuleDescription = '';
        this.showPubRule = false;
        this.flash(`${name} added to the route`);
      },
      error: () => { this.busy = false; this.flash('Could not add that pub'); }
    });
  }

  openPubRuleEditor(pub: any) {
    if (this.editingPubId === pub.id) {
      this.cancelPubRuleEditor();
      return;
    }
    this.editingPubId = pub.id;
    this.editPubRuleName = pub.ruleName || '';
    this.editPubRuleDescription = pub.ruleDescription || '';
    this.cdr.detectChanges();
  }

  cancelPubRuleEditor() {
    this.editingPubId = null;
    this.editPubRuleName = '';
    this.editPubRuleDescription = '';
    this.cdr.detectChanges();
  }

  savePubRule(pub: any) {
    const name = this.editPubRuleName.trim();
    if (!name || this.busy) {
      return;
    }
    this.busy = true;
    this.http.post('/api/set-pub-rule', {
      pub_id: pub.id,
      event_id: this.currentEventID,
      name,
      description: this.editPubRuleDescription.trim()
    }).subscribe({
      next: (response: any) => {
        this.busy = false;
        if (response.status == 'success') {
          this.cancelPubRuleEditor();
          this.getLocationRules();
          this.flash(`Rule saved for ${pub.pubName}`);
        } else {
          this.flash('Could not save rule');
        }
      },
      error: () => {
        this.busy = false;
        this.flash('Could not save rule');
      }
    });
  }

  clearPubRule(pub: any) {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.http.post('/api/set-pub-rule', {
      pub_id: pub.id,
      event_id: this.currentEventID,
      name: '',
      description: ''
    }).subscribe({
      next: () => {
        this.busy = false;
        if (this.editingPubId === pub.id) {
          this.cancelPubRuleEditor();
        }
        this.getLocationRules();
        this.flash(`Rule removed from ${pub.pubName}`);
      },
      error: () => {
        this.busy = false;
        this.flash('Could not remove rule');
      }
    });
  }

  editPubRuleFromRulesSection(pub: any) {
    this.editingPubId = pub.id;
    this.editPubRuleName = pub.ruleName || '';
    this.editPubRuleDescription = pub.ruleDescription || '';
    this.cdr.detectChanges();
    this.scrollTo('pubs');
  }

  movePub(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= this.pubs.length) {
      return;
    }
    const order = this.pubs.map(p => p.id);
    [order[index], order[target]] = [order[target], order[index]];
    // Show the new order straight away, then save it
    const moved = [...this.locationsRules];
    [moved[index], moved[target]] = [moved[target], moved[index]];
    this.locationsRules = moved.map((p, i) => ({ ...p, order_index: i + 1 }));
    this.http.post('/api/reorder-locations', { event_id: this.currentEventID, pub_ids: order }).subscribe({
      next: () => this.getLocationRules(),
      error: () => this.getLocationRules()
    });
  }

  removeLocation(pub: any) {
    this.http.post('/api/remove-location', { pub_id: pub.id }).subscribe({
      next: () => {
        // Close the gap in the numbering
        const order = this.pubs.filter(p => p.id !== pub.id).map(p => p.id);
        this.http.post('/api/reorder-locations', { event_id: this.currentEventID, pub_ids: order }).subscribe({
          next: () => this.getLocationRules(),
          error: () => this.getLocationRules()
        });
        this.flash(`${pub.pubName} removed`);
      }
    });
  }

  // ---------- step 4: rules ----------
  saveBaseRule() {
    const name = this.newBaseRule.trim();
    if (!name || this.busy) {
      return;
    }
    const description = this.newBaseRuleDescription.trim();
    if (this.newRulePubId) {
      const targetPub = this.pubs.find(p => p.id === this.newRulePubId);
      this.busy = true;
      this.http.post('/api/set-pub-rule', {
        pub_id: this.newRulePubId,
        event_id: this.currentEventID,
        name,
        description
      }).subscribe({
        next: (response: any) => {
          this.busy = false;
          if (response.status == 'success') {
            this.newBaseRule = '';
            this.newBaseRuleDescription = '';
            this.newRulePubId = '';
            this.getLocationRules();
            this.flash(targetPub ? `Rule saved for ${targetPub.pubName}` : 'Pub rule saved');
          } else {
            this.flash('Could not save pub rule');
          }
        },
        error: () => {
          this.busy = false;
          this.flash('Could not save pub rule');
        }
      });
      return;
    }

    this.busy = true;
    this.http.post('/api/add-new-rule', {
      pub_id: null, name, description, event_id: this.currentEventID
    }).subscribe({
      next: () => {
        this.busy = false;
        this.newBaseRule = '';
        this.newBaseRuleDescription = '';
        this.getBaseRules();
        this.flash('Rule added');
      },
      error: () => {
        this.busy = false;
        this.flash('Could not add rule');
      }
    });
  }

  removeBaseRule(rule: any) {
    this.http.post('/api/remove-base-rule', { rule_id: rule.id }).subscribe({
      next: () => this.getBaseRules()
    });
  }
}
