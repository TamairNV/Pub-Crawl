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

@Component({
  selector: 'app-map-view',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './upload.html',
  //styleUrl: './dashboard.css'
})
export class UploadComponent implements OnInit {

  authService = inject(AuthService);
  http = inject(HttpClient);
  router = inject(Router);

  currentUser: any;
  private currentEventID: string | null | undefined;
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

  upload(){
    console.log("upload")
  }





}
