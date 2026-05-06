import {Component, inject, OnInit, signal} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {Router, RouterLink} from '@angular/router';
import {UserProfile} from '../auth';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dashboard.html'
})
export class AdminDashboardComponent implements OnInit {
  ngOnInit() {
    this.getUsers()
  }
  isOpen = false;

  toggleMenu() {
    this.isOpen = !this.isOpen;
  }
  http = inject(HttpClient);
  router = inject(Router);

  event_name = '';
  people = '';

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

            let html = ''
            const data = response
            for (let i = 0; i < data.length; i++) {
              html += `<div>${data[i]['name']}</div>`;
            }
            this.people = html
          }
        },
        error: (err) => {
          this.isLoading = false;
          console.error('Flask request failed:', err);
        }
      });

  }
}


