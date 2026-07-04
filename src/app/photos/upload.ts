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
      this.selectedFiles = Array.from(files);
    }
  }

  // Keep each request WELL under the Cloudflare 100 MB body cap
  private readonly CHUNK_SIZE     = 50 * 1024 * 1024; // 16 MB
  private readonly MAX_PARALLEL    = 3;                // concurrent chunks per file
  private readonly MAX_RETRIES     = 5;

  private sleep(ms: number) {
    return new Promise<void>(r => setTimeout(r, ms));
  }

  /** Send one chunk, retrying with exponential backoff on transient errors. */
  private async sendChunkWithRetry(
    file: File, fileUuid: string, totalChunks: number,
    chunkIndex: number, userBlob: string, eventId: string | null
  ): Promise<void> {
    const start = chunkIndex * this.CHUNK_SIZE;
    const end   = Math.min(start + this.CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const formData = new FormData();
    formData.append('file_chunk', chunk, file.name);
    formData.append('chunk_index', chunkIndex.toString());
    formData.append('total_chunks', totalChunks.toString());
    formData.append('file_uuid', fileUuid);
    formData.append('original_name', file.name);
    formData.append('user_id', userBlob);
    formData.append('event_id', eventId ?? '');

    let attempt = 0;
    while (true) {
      try {
        await firstValueFrom(this.http.post('/api/upload-footage', formData));
        return;
      } catch (err) {
        attempt++;
        if (attempt >= this.MAX_RETRIES) throw err;
        const backoff = Math.min(30000, 500 * 2 ** attempt);
        await this.sleep(backoff);
      }
    }
  }

  /** Wait until the server finishes assembling + transcoding a file. */
  private async pollStatus(fileUuid: string, timeoutMs = 15 * 60 * 1000): Promise<void> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      try {
        const res = await firstValueFrom(
          this.http.get<any>(`/api/upload-status?file_uuid=${encodeURIComponent(fileUuid)}`)
        );
        if (res.status === 'done') return;
        if (res.status === 'error') throw new Error(res.error || 'processing failed');
      } catch (e) {
        // transient network blip on the poll — keep going
      }
      await this.sleep(1500);
    }
    throw new Error('Processing timed out on the server');
  }

  async upload() {
    if (!this.selectedFiles || this.selectedFiles.length === 0) return;

    this.isUploading = true;
    this.uploadProgress = 0;
    this.cdr.detectChanges();

    const userBlob =
      typeof this.currentUser === 'string' ? this.currentUser : JSON.stringify(this.currentUser);

    // Build the full chunk list across every file for a single global progress bar
    type Work = { file: File; uuid: string; idx: number; total: number };
    const allWork: Work[] = [];
    let totalChunkCount = 0;
    for (const file of this.selectedFiles) {
      const total = Math.ceil(file.size / this.CHUNK_SIZE);
      const uuid  = crypto.randomUUID();
      for (let i = 0; i < total; i++) allWork.push({ file, uuid, idx: i, total });
      totalChunkCount += total;
    }

    // Group work by uuid so we can know when each file finishes
    const byFile = new Map<string, Work[]>();
    for (const w of allWork) {
      if (!byFile.has(w.uuid)) byFile.set(w.uuid, []);
      byFile.get(w.uuid)!.push(w);
    }

    let done = 0;
    const inline = (w: Work) => {
      this.uploadStatusText =
        `Uploading: ${w.file.name} · chunk ${w.idx + 1}/${w.total}`;
    };

    // Limited-concurrency pump so we don't fire hundreds of requests at once
    let cursor = 0;
    const queue = [...allWork];
    const worker = async () => {
      while (cursor < queue.length) {
        const my = queue[cursor++];
        inline(my);
        try {
          await this.sendChunkWithRetry(
            my.file, my.uuid, my.total, my.idx, userBlob, this.currentEventID
          );
        } catch (err) {
          console.error(`Chunk failed: ${my.file.name} #${my.idx}`, err);
          this.uploadStatusText = `Upload failed on ${my.file.name} ❌`;
          this.isUploading = false;
          this.cdr.detectChanges();
          return false;
        }
        done++;
        this.uploadProgress = Math.round((done / totalChunkCount) * 100);
        this.cdr.detectChanges();
      }
      return true;
    };

    const workers = Array.from({ length: this.MAX_PARALLEL }, worker);
    const results = await Promise.all(workers);
    if (!results.every(Boolean)) return; // a worker bailed out

    // All chunks delivered — now wait for each file's server-side transcoding
    this.uploadStatusText = 'Server is stitching & transcoding media… ⏳';
    this.cdr.detectChanges();
    for (const [uuid] of byFile) {
      await this.pollStatus(uuid);
    }

    this.isUploading = false;
    this.uploadProgress = 100;
    this.cdr.detectChanges();
    this.router.navigate(['/map-view', this.currentEventID]).then(r => {});
  }
}
