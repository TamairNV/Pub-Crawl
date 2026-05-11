import { Injectable, signal } from '@angular/core';

export interface UserProfile {
  id: string;
  name: string;
  role: string;
}

@Injectable({
  providedIn: 'root'
})

export class AuthService {


  private savedUser = localStorage.getItem('user_data');
  currentUser = signal<UserProfile | null>(this.savedUser ? JSON.parse(this.savedUser) : null);

  setSession(user: UserProfile) {
    localStorage.setItem('user_data', JSON.stringify(user));
    this.currentUser.set(user);
  }

  logout() {
    localStorage.removeItem('user_data');
    this.currentUser.set(null);
  }
  getSession() {
    return this.currentUser;
  }

}
