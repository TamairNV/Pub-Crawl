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
import exifr from 'exifr';
@Component({
  selector: 'app-map-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './upload.html',
  styleUrl: './upload.css'
})
export class UploadComponent implements OnInit {

  authService = inject(AuthService);
  http = inject(HttpClient);
  router = inject(Router);

  currentUser: any;
  protected currentEventID: string | null | undefined;
  constructor(private route: ActivatedRoute, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    this.currentUser = this.authService.getSession()();

    this.route.paramMap.subscribe(params => {
      this.currentEventID = params.get('id');
      console.log('Loaded event with ID:', this.currentEventID);
    });
  }
  selectedFiles: File[] = [];


  onFilesSelected(event: any) {
    const files: FileList = event.target.files;
    if (files) {
      // Convert the FileList into a standard array
      this.selectedFiles = Array.from(files);
    }
  }

  async upload() {
    const formData = new FormData();
    const metadata = [];

    for (let i = 0; i < this.selectedFiles.length; i++) {
      const file = this.selectedFiles[i];
      const uuid = crypto.randomUUID();

      formData.append('photos', file, file.name);


      metadata.push({
        id: uuid,
        original_name: file.name,
        user_id: this.currentUser,
        event_id: this.currentEventID
      });
    }

    formData.append('metadata', JSON.stringify(metadata));

    this.http.post('/api/upload-footage', formData)
      .subscribe({
        next: (response: any) => {
          console.log(response);
          if (response.received == "Uploaded") {
            console.log("Uploaded");
          } else {
            console.log("UH OH");
          }
        },
        error: (err) => console.error("Upload failed", err)
      });
  }





}
