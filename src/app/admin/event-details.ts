import {Component, inject, OnInit, signal,ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {UserProfile} from '../auth';
import { firstValueFrom } from 'rxjs'
import { ActivatedRoute } from '@angular/router';


@Component({
  selector: 'app-event-details',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './event-details.html',
  styleUrl: './event-details.css'
})

export class EventDetailsComponent implements OnInit {
  constructor(private route: ActivatedRoute,private cdr: ChangeDetectorRef) {}
  ngOnInit() {

    this.route.paramMap.subscribe(params => {
      const eventId = params.get('id');
      this.currentEventID = eventId
      console.log('Loaded event with ID:', eventId);
      this.getEventDetails();
      this.getLocationRules();
      this.getBaseRules();

    });

  }
  public newPlayerSelected: boolean[] = [];
  public newPlayerTeamIDs: any[] = [];
  currentEventID: string | null = ''
  http = inject(HttpClient);
  router = inject(Router);
  userDetails : any[] = [];
  teams: any[] = [];
  public selectedTeamIDs : any[] = [];
  public isEditing: boolean[] = [];
  showNewTeamForm = false
  newTeamName = ''
  newTeamColor = ''
  newLocationName = ''
  newBaseRuleLocation = ''
  newBaseRuleDescriptionLocation = ''

  newBaseRule = ''
  newBaseRuleDescription = ''

  currentlyEditing = 0

  toggleEdit(i: number) {
    this.isEditing.fill(false)
    this.isEditing[i] = !this.isEditing[i];
    this.currentlyEditing = i
    this.cdr.detectChanges();
  }

  getEventDetails(){
    console.log(this.currentEventID)
    const event = {event_id : this.currentEventID}
    this.http.post('/api/get-event-details',event).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("event error");
        }else{
          this.userDetails = response.received.users || [];

          this.teams = response.received.teams || [];
          console.log("FLASK SENT THESE TEAMS:", this.teams);
          if (this.isEditing.length === 0 || this.isEditing.length !== this.userDetails.length) {
            this.isEditing = new Array(this.userDetails.length).fill(false);
          }
          this.cdr.detectChanges();
          console.log("Event got",response.received)}
      }
    })
  }

  onTeamChange(event: any) {
    const value = event.target.value;

    if (value === 'new') {
      this.showNewTeamForm = true
    }
  }

  async saveTeam() {
    const new_team_ID = this.selectedTeamIDs[this.currentlyEditing];
    const user = this.userDetails[this.currentlyEditing];
    console.log(user)
    console.log(this.userDetails)

    const data = {user_id : user.userID,event_id: this.currentEventID,new_team_id: new_team_ID }
    this.http.post('/api/update-user-team',data).subscribe({
      next: (response: any) => {
        if (response.received == "fail") {
          console.log("event error");
        }else{
          console.log("Team Updated",response.received)}
        this.getEventDetails()
        this.isEditing.fill(false)

      }
    })

  }

  saveNewTeam(){
    const newTeam = {
      name: this.newTeamName,
      colour: this.newTeamColor,
      event_id : this.currentEventID
    };

    this.http.post('/api/save-new-team',newTeam).subscribe({
      next: (response: any) => {
        if (response.received != "failed") {
          this.showNewTeamForm = false;

          this.newTeamName = '';
          this.newTeamColor = '';


          this.getEventDetails();
          this.getLocationRules();
          this.getBaseRules();
        }
      }
    })
  }
  saveBaseRule(location_index : number){
    let data = {}
    if ( location_index === -1){
       data = {
        pub_id : null,
        name : this.newBaseRule,
        description : this.newBaseRuleDescription,
         event_id : this.currentEventID,
      }
    }else{
       data = {
        pub_id : location_index,
        name : this.newBaseRuleLocation,
        description : this.newBaseRuleDescriptionLocation,
         event_id : this.currentEventID,
      }
    }


    this.http.post('/api/add-new-rule',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("event error");
        }else{

          console.log("New Rule Created",response.received)
          this.newBaseRule = ''
          this.newBaseRuleDescription = ''
          this.getEventDetails()
          this.getLocationRules();
          this.getBaseRules();
          this.cdr.detectChanges();

        }
      }
    })
    this.cdr.detectChanges();
  }

  saveLocation(){

    const data = {
      event_id : this.currentEventID,
      name : this.newLocationName,
      index : this.locationsRules.length+1
    }
    this.http.post('/api/add-new-location',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("event error");
        }else{

          console.log("New location Created",response.received)
          this.saveBaseRule(response.received)
          this.newBaseRuleLocation = ''
          this.newBaseRuleDescriptionLocation = ''
          this.newLocationName = ''
          this.cdr.detectChanges();

        }
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
          this.cdr.detectChanges();

        }
      }
    })
  }

  addUserMenu = false
  selectedPeople : any = []
  toggleAddUserMenu(){
    this.addUserMenu = !this.addUserMenu
    this.getUsers()
  }
  people : any = []
  getUsers() {
    this.http.get('/api/get-users').subscribe({
      next: (response: any) => {
        if (response.received !== "Wrong") {
          this.people = [];
          for (let i = 0; i < response.length; i++) {
            let isAlreadyPicked = false;
            for (let j = 0; j < this.userDetails.length; j++) {
              if(response[i]['id'] == this.userDetails[j]['userID']){
                isAlreadyPicked = true;
                break;
              }
            }
            if(!isAlreadyPicked){
              this.people.push(response[i]);
            }
          }

          this.newPlayerSelected = new Array(this.people.length).fill(false);
          this.newPlayerTeamIDs = new Array(this.people.length).fill('');

          this.cdr.detectChanges();
        }
      }
    });
  }

  saveNewPlayers(){
    const finalData = this.people
      .map((person: any, index: number) => {
        return {
          userId: person.id,
          userName: person.name,
          isSelected: this.newPlayerSelected[index], // <-- Updated
          teamId: this.newPlayerTeamIDs[index],      // <-- Updated
          eventId : this.currentEventID
        };
      })
      .filter((entry: any) => entry.isSelected);

    this.http.post('/api/save-people-to-event',finalData).subscribe({
      next: (response: any) => {
        if (response.received != "False") {
          this.toggleAddUserMenu();
          this.getEventDetails();
        }
      }
    })
  }


  removeUser(id: string){
    const data = {user_id : id, event_id : this.currentEventID}
    this.http.post('/api/remove-user',data).subscribe({
      next: (response: any) => {
        if (response.status == "failed") {
          console.log("user remove error");
        }else{
          this.getEventDetails();
          this.cdr.detectChanges();
          console.log("user removed")}
      }
    })
  }

  removeLocation(id: string){
    const data = {pub_id : id}
    this.http.post('/api/remove-location',data).subscribe({
      next: (response: any) => {
        if (response.status == "failed") {
          console.log("pub remove error");
        }else{
          this.getLocationRules();

          this.cdr.detectChanges();
          console.log("pub removed")}
      }
    })
  }

  removeBaseRule(id: string){
    const data = {rule_id : id}
    this.http.post('/api/remove-base-rule',data).subscribe({
      next: (response: any) => {
        if (response.status == "failed") {
          console.log("rule remove error");
        }else{

          this.getBaseRules();

          console.log("rule removed")}
      }
    })
  }




}
