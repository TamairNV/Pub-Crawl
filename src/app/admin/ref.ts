import { Component, inject, OnDestroy, OnInit, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../auth';
import { RefMiniEventsComponent } from './ref-mini-events';
import { EventAward, MiniWheel, PlayerTask } from '../shared/mini-events.types';


@Component({
  selector: 'app-ref',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RefMiniEventsComponent],
  templateUrl: './ref.html',
  styleUrl: './ref.css'
})



export class RefComponent implements OnInit, OnDestroy {
  protected currentEventID: string | null | undefined;
  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);
  userDetails: any[] = [];
  teams: any[] = [];
  currentUser: any;
  selectedPlayer: any | null = null;

  wheels: MiniWheel[] = [];
  tasks: PlayerTask[] = [];
  teamAdjustments: any[] = [];
  awards: EventAward[] = [];
  awardsSettings = { voting_open: true, results_visible: false };
  awardsVotes: any = { my_votes: {}, tally: {}, votes_by_voter: {} };
  liveStateError = '';
  private pollTimer: any = null;

  constructor(private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}
  ngOnInit() {
    if (!this.authService.getSession()()) {
      this.router.navigate(['/login']);
      return;
    }
    this.route.paramMap.subscribe(params => {
      const eventId = params.get('id');
      this.currentEventID = eventId
      this.currentUser = this.authService.getSession()();
      console.log("current User ", this.currentUser)
      console.log('Loaded event with ID:', eventId);
      this.getEventDetails();
      this.getBaseRules();
      this.getLocationRules();
      this.loadLiveState();
    });

    this.pollTimer = setInterval(() => {
      if (this.currentEventID) {
        this.loadLiveState();
      }
    }, 4000);
  }

  ngOnDestroy() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  getEventDetails(){
    console.log(this.currentEventID)
    const event = {event_id : this.currentEventID}
    this.http.post('/api/get-event-details',event).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("event error");
        }else{
          this.userDetails = response.received.users
          this.teams = response.received.teams
          this.getPoints();

          console.log("Event got",response.received)}
      }
    })
  }
  baseRules : any[] = [];
  locationsRules : any[] = [];

  getBaseRules(){

    const data = {event_id : this.currentEventID}
    this.http.post('/api/get-base-rules',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("rule error");
        }else{
          console.log("base rules got",response.received)
          this.baseRules = response.received
          this.cdr.detectChanges();

        }
      }
    })
  }

  getLocationRules(){

    const data = {event_id : this.currentEventID}
    this.http.post('/api/get-locations-rules',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("locations error");
        }else{
          console.log("locations rules got",response.received)
          this.locationsRules = response.received
          this.syncCurrentPub();
          this.cdr.detectChanges();

        }
      }
    })
  }


  // Mobile: filter players by team / name, and show the tap straight away (the server confirms after)
  teamFilter = '';
  playerSearch = '';
  bumped: any = null;
  shownPlayers() {
    const q = this.playerSearch.trim().toLowerCase();
    return (this.userDetails || []).filter((u: any) =>
      (!this.teamFilter || u.teamID === this.teamFilter) && (!q || String(u.name).toLowerCase().includes(q)));
  }
  trackUser(_: number, u: any) { return u.userID; }

  givePoint(n: any,id : String){
    const row = (this.userDetails || []).find((u: any) => u.userID === id);
    if (row) { row.points = (row.points || 0) + n; }
    this.bumped = id;
    setTimeout(() => { if (this.bumped === id) { this.bumped = null; this.cdr.detectChanges(); } }, 350);
    try { navigator.vibrate?.(15); } catch {}
    const data = {event_id : this.currentEventID, points : n, user_id :id}
    this.http.post('/api/give-user-points',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("give points error");
        }else{
          console.log("points given ",response.received)
          this.getPoints()

        }
      }
    })
  }
  points  : any = []
  getPoints(){
    const data = {event_id : this.currentEventID}
    this.http.post('/api/get-user-points',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("got points error");
        }else{
          console.log("points got ",response.received)
          this.points = response.received || [];
          this.syncUserPoints();
          console.log(this.userDetails)
          this.cdr.detectChanges();
        }
      }
    })
  }

  private syncUserPoints() {
    if (!this.userDetails) return;
    for (let i = 0; i < this.userDetails.length; i++) {
      let total = 0;
      for (let j = 0; j < this.points.length; j++) {
        if (this.points[j].userID == this.userDetails[i].userID) {
          total = this.points[j].total_points;
          break;
        }
      }
      this.userDetails[i].points = total;
    }
  }

  loadLiveState() {
    if (!this.currentEventID) return;
    this.http.post('/api/ref-live-state', { event_id: this.currentEventID }).subscribe({
      next: (response: any) => {
        if (response.status !== 'success' || !response.received) {
          this.liveStateError = response.received || 'Could not load mini events.';
          this.cdr.detectChanges();
          return;
        }
        this.liveStateError = '';
        const r = response.received;
        this.tasks = r.tasks || [];
        this.wheels = r.wheels || [];
        this.points = r.points || [];
        this.teamAdjustments = r.team_adjustments || [];
        this.awards = r.awards || [];
        this.awardsSettings = r.awards_settings || { voting_open: true, results_visible: false };
        this.awardsVotes = r.awards_votes || { my_votes: {}, tally: {}, votes_by_voter: {} };
        this.syncUserPoints();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.liveStateError = err?.status === 500
          ? 'Mini-events database tables are not created yet. Run the DB migration script on the server.'
          : (err?.error?.received || 'Could not load mini events.');
        this.cdr.detectChanges();
      }
    });
  }

  openPlayerModal(user: any) {
    this.selectedPlayer = user;
  }

  teamColour(teamId: string): string {
    const t = (this.teams || []).find((x: any) => x.id === teamId);
    return t?.colour || '#fbbf24';
  }

  playerStatusBadge(userId: string): { label: string; urgent: boolean } | null {
    const mine = (this.tasks || []).filter(
      (t) => t.user_id === userId && (t.status === 'pending' || t.status === 'ready_to_spin' || t.status === 'awaiting_target')
    );
    if (!mine.length) return null;
    if (mine.some((t) => t.player_claimed_done && t.status === 'pending')) {
      return { label: '✋ Done!', urgent: true };
    }
    if (mine.some((t) => t.status === 'ready_to_spin')) {
      return { label: '🎡 Spin Ready', urgent: true };
    }
    if (mine.some((t) => t.status === 'awaiting_target')) {
      return { label: '🎯 Pick Team', urgent: true };
    }
    return { label: `⏳ ${mine.length} task`, urgent: false };
  }


  currentPubIndex = 0
  movePub(n : any){
    this.currentPubIndex += n;
    this.saveCurrentPub();
  }

  // Players' pages read the current pub from the server, so tell it whenever the ref moves on
  saveCurrentPub(){
    const stop = this.locationsRules[this.currentPubIndex];
    if (!stop) return;
    this.http.post('/api/set-current-pub', {event_id: this.currentEventID, pub_id: stop.id}).subscribe({
      next: (response: any) => {
        if (response.status !== 'success') console.log("set current pub error", response.received);
      },
      error: (err) => console.log("set current pub error", err)
    });
  }

  // On load, start where the crawl actually is instead of at the first pub
  syncCurrentPub(){
    this.http.post('/api/get-current-pub', {event_id: this.currentEventID}).subscribe({
      next: (response: any) => {
        if (response.status !== 'success') return;
        const i = this.locationsRules.findIndex((l: any) => l.id === response.received.pub_id);
        if (i >= 0) {
          this.currentPubIndex = i;
          this.cdr.detectChanges();
        }
      }
    });
  }

}
