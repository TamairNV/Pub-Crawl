import {
  Component,
  inject,
  OnInit,
  signal,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  AfterViewInit
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService, UserProfile } from '../auth';
import { firstValueFrom } from 'rxjs';
import { AppComponent } from '../app';

declare var mapkit: any;

@Component({
  selector: 'app-map-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './map.html',
  //styleUrl: './dashboard.css'
})
export class MapComponent implements OnInit, AfterViewInit {

  authService = inject(AuthService);
  http = inject(HttpClient);
  router = inject(Router);

  currentUser: any;
  public currentEventID: string | null | undefined;

  @ViewChild('mapContainer') mapContainer!: ElementRef;
  private map: any;

  constructor(private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.currentUser = this.authService.getSession()();

    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      console.log('Loaded event with ID:', this.currentEventID);
    });
  }

  ngAfterViewInit(): void {
    // Check if the script is ready right now
    if (typeof mapkit !== 'undefined') {
      this.initializeMap();
    } else {
      console.log("loading map")
      // If the script is still downloading, wait a moment and try again
      const interval = setInterval(() => {
        if (typeof mapkit !== 'undefined') {
          this.initializeMap();
          clearInterval(interval);
        }
      }, 100);
    }
  }

  private initializeMap(): void {
    // 1. Initialize MapKit with your token
    mapkit.init({
      authorizationCallback: (done: any) => {
        done('eyJraWQiOiI4UkdKNUJVWjVEIiwidHlwIjoiSldUIiwiYWxnIjoiRVMyNTYifQ.eyJpc3MiOiJNUDlSTVhVWjdNIiwiaWF0IjoxNzgwMDE2NTM4LCJzY29wZSI6Im1hcGtpdF9qcyIsImV4cCI6MTc4MDY0Mjc5OX0.TAVu_CsJU3wS9que6IOyB-C4YSVsoa6umyZR9lgCx1zumYPW2UHx1WfYNjaDeptcQS2wHBqDzjxE0qWaOjRZFw');
      }
    });

    // 2. Render the map inside your HTML div
    this.map = new mapkit.Map(this.mapContainer.nativeElement, {
      center: new mapkit.Coordinate(37.7749, -122.4194), // San Francisco
      showsMapTypeControl: true
    });

    // 3. Add your lines and waypoints
    this.addWaypointsAndLines();
  }

  private addWaypointsAndLines(): void {
    // Example Coordinates
    const startPoint = new mapkit.Coordinate(37.7749, -122.4194);
    const endPoint = new mapkit.Coordinate(37.8080, -122.4177);

    // Create Pin Waypoints
    const startPin = new mapkit.MarkerAnnotation(startPoint, { title: "Start", color: "#007AFF" });
    const endPin = new mapkit.MarkerAnnotation(endPoint, { title: "End", color: "#FF3B30" });

    // Add pins to map
    this.map.showItems([startPin, endPin]);

    // Create Connecting Line
    const line = new mapkit.PolylineOverlay([startPoint, endPoint], {
      style: new mapkit.Style({
        strokeColor: "#5AC8FA",
        strokeWidth: 5,
        lineJoin: "round"
      })
    });

    // Add line overlay to map
    this.map.addOverlay(line);
  }
}
