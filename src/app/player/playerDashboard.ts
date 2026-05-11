import {Component, inject, OnInit, signal,ChangeDetectorRef} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {AuthService} from '../auth';

import { ActivatedRoute } from '@angular/router';


@Component({
  selector: 'app-ref',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './playerDashboard.html',
  styleUrl: './playerDashboard.css'
})



export class PlayerDashboard implements OnInit {

  http = inject(HttpClient);
  router = inject(Router);
  authService = inject(AuthService);


  currentUser: any;
  constructor(private route: ActivatedRoute,private cdr: ChangeDetectorRef) {}
  ngOnInit() {
    this.currentUser = this.authService.getSession()();
    this.getUserEvents();

  }
  events : any = []

  getUserEvents(){
    const data = {user_id : this.currentUser.id}
    this.http.post('http://localhost:5002/api/get-user-events',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("got events error");
        }else{
          console.log("events given ",response.received)
          this.events = response.received
          this.cdr.detectChanges();
        }
      }
    })
  }



}
