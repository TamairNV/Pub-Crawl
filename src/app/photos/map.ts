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
  styleUrl: './map.css'
})
export class MapComponent implements OnInit, AfterViewInit {

  authService = inject(AuthService);
  http = inject(HttpClient);
  router = inject(Router);
  media_data : any[] = []
  currentUser: any;
  public currentEventID: string | null | undefined;

  @ViewChild('mapContainer') mapContainer!: ElementRef;
  private map: any;

  constructor(private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}

  ngAfterViewInit(): void {
    }

  ngOnInit() {
    this.currentUser = this.authService.getSession()();

    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      console.log('Loaded event with ID:', this.currentEventID);
    });
    this.get_footage();
  }
  /**
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

    this.map = new mapkit.Map(this.mapContainer.nativeElement, {
      center: new mapkit.Coordinate(37.7749, -122.4194), // San Francisco
      showsMapTypeControl: true
    });
  }
    **/

  private get_footage(): void {
    const data = {event_id : this.currentEventID}
    this.http.post('/api/get-footage',data).subscribe({
      next: (response: any) => {
        if (response.received == "failed") {
          console.log("got footage error");
        }else{
          console.log("footage got ",response.received)
          this.media_data = response.received
          // Ascending order
          this.media_data.sort((a, b) => new Date(a.time_taken).getTime() - new Date(b.time_taken).getTime());
          this.cdr.detectChanges();
        }
      }
    })
  }

  isVideo(filename: string): boolean {
    // Add other video extensions here if you use things like .webm
    return filename.toLowerCase().endsWith('.mp4');
  }
  downloadAll(): void {
    this.media_data.forEach((file, index) => {
      setTimeout(() => {
        fetch(file.id)
          .then(response => response.blob())
          .then(blob => {
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = index.toString();
            link.click();
            URL.revokeObjectURL(blobUrl); // Clean up memory
          });
      }, index * 300); // Slightly longer delay for fetches
    });
  }



}
