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
  isUploading: boolean = false;
  uploadProgress: number = 0;
  uploadStatusText: string = '';
  currentUser: any;
  protected currentEventID: string | null = null;
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
    if (!this.selectedFiles || this.selectedFiles.length === 0) return;

    // Lock the UI and reset progress
    this.isUploading = true;
    this.uploadProgress = 0;

    const CHUNK_SIZE = 20 * 1024 * 1024; // 20MB chunks

    // Calculate total chunks across ALL selected files for a global progress bar
    let totalChunksAcrossAllFiles = 0;
    for (let i = 0; i < this.selectedFiles.length; i++) {
      totalChunksAcrossAllFiles += Math.ceil(this.selectedFiles[i].size / CHUNK_SIZE);
    }

    let chunksUploadedSoFar = 0;

    for (let i = 0; i < this.selectedFiles.length; i++) {
      const file = this.selectedFiles[i];
      const fileUuid = crypto.randomUUID();
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

      this.uploadStatusText = `Uploading: ${file.name} (${i + 1} of ${this.selectedFiles.length})`;

      for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
        const start = chunkIndex * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);

        const formData = new FormData();
        formData.append('file_chunk', chunk, file.name);
        formData.append('chunk_index', chunkIndex.toString());
        formData.append('total_chunks', totalChunks.toString());
        formData.append('file_uuid', fileUuid);
        formData.append('original_name', file.name);
        formData.append('user_id', typeof this.currentUser === 'string' ? this.currentUser : JSON.stringify(this.currentUser));
        // @ts-ignore
        formData.append('event_id', this.currentEventID);

        try {
          await this.http.post('/api/upload-footage', formData).toPromise();

          // Update the progress bar after every successful chunk
          chunksUploadedSoFar++;
          this.uploadProgress = Math.round((chunksUploadedSoFar / totalChunksAcrossAllFiles) * 100);
          this.cdr.detectChanges()
          // If we hit 100%, tell the user the server is stitching/compressing
          if (this.uploadProgress === 100) {
            this.uploadStatusText = "Processing media on server... this might take a minute ⏳";
          }

        } catch (err) {
          console.error(`Upload failed at chunk ${chunkIndex}`, err);
          this.isUploading = false;
          this.uploadStatusText = "Upload failed! ❌";
          return;
        }
      }
    }

    // Once everything is totally finished and processed
    this.isUploading = false;
    this.router.navigate(['/map-view', this.currentEventID]).then(r => {});
  }




}
