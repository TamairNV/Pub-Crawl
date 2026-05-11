import {Component, inject, OnInit, signal,ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {AuthService, UserProfile} from '../auth';
import { firstValueFrom } from 'rxjs'
import { ActivatedRoute } from '@angular/router';


@Component({
  selector: 'app-ref',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './ref.html'
})



export class RefComponent implements OnInit {
  private currentEventID: string | null | undefined;
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
      this.currentUser = this.authService.getSession();
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
          this.cdr.detectChanges();
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


  givePoint(n: any){

  }
}
