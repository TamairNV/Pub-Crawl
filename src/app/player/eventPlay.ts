import { Component, inject, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../auth';
import { PlayerMiniEventsComponent } from './player-mini-events';
import { EventAward, MiniWheel, PlayerTask } from '../shared/mini-events.types';


@Component({
  selector: 'app-ref',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PlayerMiniEventsComponent],
  templateUrl: './eventPlay.html',
  styleUrl: './eventPlay.css'
})



export class EventPlay implements OnInit, OnDestroy {

  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);


  currentUser: any;
  protected currentEventID: string | null | undefined;
  constructor(private route: ActivatedRoute,private cdr: ChangeDetectorRef) {}
  eventLoaded = false;
  pointsLoaded = false;

  teamAdjustments: any[] = [];
  wheels: MiniWheel[] = [];
  myTasks: PlayerTask[] = [];
  awards: EventAward[] = [];
  awardsSettings = { voting_open: true, results_visible: false };
  awardsVotes: any = { my_votes: {}, tally: {} };

  ngOnInit() {
    this.currentUser = this.authService.getSession()();

    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      console.log('Loaded event with ID:', this.currentEventID);

      // Now that we HAVE the ID, fetch the data!
      this.getEventDetails();
      this.getPoints();
      this.getBaseRules();
      this.getLocationRules();
      this.startLocationPolling();
    });
  }
  checkAndBuildLeaderboard() {
    if (this.eventLoaded && this.pointsLoaded) {
      this.generateLeaderboard();
      this.cdr.detectChanges(); // Update the screen once everything is ready
    }
  }

  userDetails : any = []
  teams : any = []
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
          this.eventLoaded = true;
          this.syncPointsToUsers();
          console.log("Event got",response.received)}
          this.checkAndBuildLeaderboard();

          this.cdr.detectChanges();

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
          this.syncPointsToUsers();

          console.log(this.userDetails)
          this.pointsLoaded = true;
          this.checkAndBuildLeaderboard();
          this.cdr.detectChanges();
        }
      }
    })
  }

  private syncPointsToUsers() {
    if (!Array.isArray(this.userDetails) || !Array.isArray(this.points)) return;
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
  leaderboardData: any[] = [];

  generateLeaderboard() {
    this.leaderboardData = this.teams.map((team: any) => {

      const teamMembers = this.userDetails.filter((user: any) => user.teamID === team.id);
      const mappedMembers = teamMembers.map((m: any) => {
        const scoreRecord = this.points.find((p: any) => p.userID === m.userID);

        const pts = scoreRecord ? (parseInt(scoreRecord.total_points) || 0) : 0;

        return {
          name: m.name,
          userID: m.userID,
          points: pts
        };
      });

      const adjRecord = (this.teamAdjustments || []).find((a: any) => a.team_id === team.id);
      const adjustment = adjRecord ? (parseInt(adjRecord.adjustment) || 0) : 0;
      const totalPoints = mappedMembers.reduce((sum: number, member: any) => sum + member.points, 0) + adjustment;

      return {
        teamID: team.id,
        teamName: team.name,
        colour: team.colour,
        adjustment: adjustment,
        totalPoints: totalPoints,
        members: mappedMembers
      };
    });

    this.leaderboardData.sort((a, b) => a.totalPoints - b.totalPoints);

    console.log("Final Leaderboard:", this.leaderboardData);
  }


  // ---- Rules & current location ----
  // General rules apply all night; location rules belong to one pub.
  // The ref moves the crawl on, so the current pub, tasks, scores, and awards sync every 4s.
  baseRules: any[] = [];
  locationsRules: any[] = [];
  currentPubId: string | null = null;
  currentStop: { pubName: string; order_index: number; rules: any[] } | null = null;
  private pollTimer: any = null;

  getBaseRules() {
    this.http.post('/api/get-base-rules', {event_id: this.currentEventID}).subscribe({
      next: (response: any) => {
        this.baseRules = Array.isArray(response.received) ? response.received : [];
        this.cdr.detectChanges();
      }
    });
  }

  getLocationRules() {
    this.http.post('/api/get-locations-rules', {event_id: this.currentEventID}).subscribe({
      next: (response: any) => {
        this.locationsRules = Array.isArray(response.received) ? response.received : [];
        this.updateCurrentStop();
      }
    });
  }

  loadLiveState() {
    if (!this.currentEventID) return;
    this.http.post('/api/player-live-state', {event_id: this.currentEventID}).subscribe({
      next: (response: any) => {
        if (response.status !== 'success' || !response.received) return;
        const r = response.received;
        const pubId = r.current_pub_id ?? null;
        if (pubId !== this.currentPubId) {
          this.currentPubId = pubId;
          this.updateCurrentStop();
        }
        this.myTasks = r.my_tasks || [];
        this.wheels = r.wheels || [];
        this.awards = r.awards || [];
        this.awardsSettings = r.awards_settings || { voting_open: true, results_visible: false };
        this.awardsVotes = r.awards_votes || { my_votes: {}, tally: {} };
        this.teamAdjustments = r.team_adjustments || [];
        if (Array.isArray(r.points)) {
          this.points = r.points;
          this.pointsLoaded = true;
          this.syncPointsToUsers();
          this.checkAndBuildLeaderboard();
        }
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  startLocationPolling() {
    this.stopLocationPolling();
    this.loadLiveState();
    this.pollTimer = setInterval(() => this.loadLiveState(), 4000);
  }

  stopLocationPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  ngOnDestroy() {
    this.stopLocationPolling();
  }

  // locationsRules has one row per rule, so a pub with two rules shows up twice: group them
  updateCurrentStop() {
    if (this.locationsRules.length === 0) {
      this.currentStop = null;
    } else {
      // No stop set yet (or that pub was deleted): show the first pub, same as the ref page starts on
      const known = this.locationsRules.some((l: any) => l.id === this.currentPubId);
      const pubId = known ? this.currentPubId : this.locationsRules[0].id;
      const rows = this.locationsRules.filter((l: any) => l.id === pubId);
      this.currentStop = { pubName: rows[0].pubName, order_index: rows[0].order_index, rules: rows };
    }
    this.cdr.detectChanges();
  }

}
