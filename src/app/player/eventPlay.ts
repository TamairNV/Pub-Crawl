import {Component, inject, OnInit, signal,ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {AuthService, UserProfile} from '../auth';

import { ActivatedRoute } from '@angular/router';


@Component({
  selector: 'app-ref',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './eventPlay.html',
  styleUrl: './eventPlay.css'
})



export class EventPlay implements OnInit {

  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);


  currentUser: any;
  private currentEventID: string | null | undefined;
  constructor(private route: ActivatedRoute,private cdr: ChangeDetectorRef) {}
  eventLoaded = false;
  pointsLoaded = false;

  ngOnInit() {
    this.currentUser = this.authService.getSession()();

    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      console.log('Loaded event with ID:', this.currentEventID);

      // Now that we HAVE the ID, fetch the data!
      this.getEventDetails();
      this.getPoints();
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
          this.points = response.received
          for (let i = 0; i < this.userDetails.length; i++) {
            for (let j = 0; j < this.points.length; j++) {
              if(this.points[j].userID == this.userDetails[i].userID){
                this.userDetails[i].points = this.points[j].total_points
                break
              }
            }
          }

          console.log(this.userDetails)
          this.pointsLoaded = true;
          this.checkAndBuildLeaderboard();
          this.cdr.detectChanges();
        }
      }
    })
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

      const totalPoints = mappedMembers.reduce((sum: number, member: any) => sum + member.points, 0);

      return {
        teamID: team.id,
        teamName: team.name,
        colour: team.colour,
        totalPoints: totalPoints,
        members: mappedMembers
      };
    });

    this.leaderboardData.sort((a, b) => b.totalPoints - a.totalPoints);

    console.log("Final Leaderboard:", this.leaderboardData);
  }

}
