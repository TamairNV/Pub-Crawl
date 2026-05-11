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
  templateUrl: './ref.html',
  styleUrl: './ref.css'
})



export class RefComponent implements OnInit {
  protected currentEventID: string | null | undefined;
  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);
  protected userDetails: any;
  private teams: any;
  currentUser: any;
  constructor(private route: ActivatedRoute,private cdr: ChangeDetectorRef) {}
  ngOnInit() {
    this.route.paramMap.subscribe(params => {
      const eventId = params.get('id');
      this.currentEventID = eventId
      this.currentUser = this.authService.getSession()();
      console.log("current User ", this.currentUser)
      console.log('Loaded event with ID:', eventId);
    });
    this.getEventDetails();
    this.getBaseRules();

    this.getLocationRules();
  }

  getEventDetails(){
    console.log(this.currentEventID)
    const event = {event_id : this.currentEventID}
    this.http.post('http://localhost:5002/api/get-event-details',event).subscribe({
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
    this.http.post('http://localhost:5002/api/get-base-rules',data).subscribe({
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
    this.http.post('http://localhost:5002/api/get-locations-rules',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("locations error");
        }else{
          console.log("locations rules got",response.received)
          this.locationsRules = response.received
          this.cdr.detectChanges();

        }
      }
    })
  }


  givePoint(n: any,id : String){
    console.log(this.currentUser.id)
    const data = {event_id : this.currentEventID, points : n, user_id :id,ref_id : this.currentUser.id}
    this.http.post('http://localhost:5002/api/give-user-points',data).subscribe({
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
    this.http.post('http://localhost:5002/api/get-user-points',data).subscribe({
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
          this.cdr.detectChanges();
        }
      }
    })
  }


  currentPubIndex = 0
  movePub(n : any){
    this.currentPubIndex += n;
  }

}
