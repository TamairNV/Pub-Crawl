import { Component } from '@angular/core';
import { RouterOutlet, RouterModule } from '@angular/router';
import { OfflineBadgeComponent } from './offline/offline-badge';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterModule, OfflineBadgeComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class AppComponent {

}
