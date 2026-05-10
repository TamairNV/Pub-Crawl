import {Component, inject, OnInit, signal,ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {UserProfile} from '../auth';
import { firstValueFrom } from 'rxjs';


@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dashboard.html'
})
export class AdminDashboardComponent implements OnInit {
  constructor(private cdr: ChangeDetectorRef) {}
  ngOnInit() {
    this.getUsers()
  }
  isOpen = false;
  showNewTeamForm = false;

  newTeamColor = ""
  newTeamName = ""
  currentEventID = 0
  eventCreated = signal(false);
  eventID = crypto.randomUUID();
  public selectedTeamIDs : any[] = [];
  toggleMenu() {
    this.isOpen = !this.isOpen;
  }
  http = inject(HttpClient);
  router = inject(Router);

  event_name = '';
  people : any[] = [];
  selectedPeople : boolean[] = [];
  teams   : any[] = [];
  isLoading = false;

  getUsers() {
    if (this.isLoading) {
      return;

    }
    this.isLoading = true;
    this.http.get('http://localhost:5002/api/get-users')
      .subscribe({
        next: (response: any) => {
          this.isLoading = false;
          console.log(response,response.received)
          if (response.received == "Wrong") {
          } else {
            console.log('Users retrieved successfully!', response);

            this.people = response
          }
        },
        error: (err) => {
          this.isLoading = false;
          console.error('Flask request failed:', err);
        }
      });

  }

  getTeams(){
    const data = {event_id :this.currentEventID}
    this.http.post('http://localhost:5002/api/get-teams',data)
      .subscribe({
        next: (response: any) => {
          console.log(response,response.received)
          if (response.status == "failed" || response.received == undefined) {
            console.log('getting teams fail!', response);
          } else {
            console.log('Teams retrieved successfully!', response);
            this.teams = response.received
            this.cdr.detectChanges();

          }
        },
        error: (err) => {
          console.error('Flask request failed:', err);
        }
      });

  }

  async createCrawl() {
    if (this.event_name && !this.eventCreated()) {
      const data = { name: this.event_name, id: this.eventID };
      try {
        const response: any = await firstValueFrom(
          this.http.post('http://localhost:5002/api/create-crawl', data)
        );

        if (response.status === "failed") {
          console.log('getting teams fail!', response);
        } else {
          console.log('Crawl Created successfully!', response.received);
          this.currentEventID = response.received;

          this.eventCreated.set(true);
        }
      } catch (error) {
        console.error("The server crashed or the network failed:", error);
      }
    }
  }

  onTeamChange(event: any) {
    const value = event.target.value;

    if (value === 'new') {
      this.showNewTeamForm = true;
    }
  }

  async saveTeam(){

    if(!this.eventCreated){
      await this.createCrawl()
      console.log("crawl Created")
    }


    const newTeam = {
      name: this.newTeamName,
      colour: this.newTeamColor,
      event_id : this.eventID
    };
    this.http.post('http://localhost:5002/api/save-new-team',newTeam).subscribe({
      next: (response: any) => {
        if (response.received == "Wrong") {
          console.log("Team adding error");
        }else{

          this.getTeams()

          console.log("New Team Added")}
      }
    })
    this.showNewTeamForm = false;
    this.cdr.detectChanges();

  }

  savePlayers(){
    const finalData = this.people
      .map((person, index) => {
        return {
          userId: person.id,
          userName: person.name,
          isSelected: this.selectedPeople[index],
          teamId: this.selectedTeamIDs[index],
          eventId : this.currentEventID
        };
      })
      .filter(entry => entry.isSelected);

    console.log("Final payload:", finalData);

    this.http.post('http://localhost:5002/api/save-people-to-event',finalData).subscribe({
      next: (response: any) => {
        if (response.received == "False") {
          console.log("People added error");
        }else{
          this.toggleMenu();
          console.log("Full Event Created")}
      }
    })
  }
}


