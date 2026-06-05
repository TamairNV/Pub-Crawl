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
    const CHUNK_SIZE = 20 * 1024 * 1024; // 20MB chunks (well under Cloudflare's 100MB cap)

    for (let i = 0; i < this.selectedFiles.length; i++) {
      const file = this.selectedFiles[i];
      const fileUuid = crypto.randomUUID();
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

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
        formData.append('user_id', this.currentUser);
        // @ts-ignore
        formData.append('event_id', this.currentEventID);

        try {
          // Await each chunk sequentially so we don't flood the connection
          await this.http.post('/api/upload-footage', formData).toPromise();
          console.log(`Uploaded chunk ${chunkIndex + 1}/${totalChunks} for ${file.name}`);
        } catch (err) {
          console.error(`Upload failed at chunk ${chunkIndex}`, err);
          return; // Halt if a chunk fails
        }
      }
    }

    // Redirect after all files and chunks are successfully processed
    this.router.navigate(['/map-view', this.currentEventID]);
  }





}
