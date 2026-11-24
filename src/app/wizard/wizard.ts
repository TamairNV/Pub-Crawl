import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

// New crawl in a few taps: name → what you want → teams + pubs → rule pack → go.
@Component({
  selector: 'app-new-crawl',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './wizard.html',
  styleUrls: ['./wizard.css'],
})
export class NewCrawlWizardComponent implements OnInit {
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private cdr = inject(ChangeDetectorRef);

  step = 1;
  name = '';
  features: Record<string, boolean> = { teams: true, general_rules: true, pub_rules: true, wheel: true, awards: false, photos: true, qr_join: true };
  featureList = [
    { key: 'teams', label: 'Teams', hint: 'Players split into teams' },
    { key: 'general_rules', label: 'Crawl rules', hint: 'e.g. "drink with your left hand"' },
    { key: 'pub_rules', label: 'A rule per pub', hint: 'e.g. "accents only in here"' },
    { key: 'wheel', label: 'Spin the wheel', hint: 'Dares and point swings' },
    { key: 'awards', label: 'Awards', hint: 'Vote for "Legend of the night"' },
    { key: 'photos', label: 'Photos', hint: 'Everyone shares pics on a map' },
    { key: 'qr_join', label: 'QR join', hint: 'Scan, type a name, play' },
  ];
  teamCount = 4;
  pubsText = '';
  packs: any[] = [];
  packId = 'classic';
  busy = false;
  error = '';

  ngOnInit() {
    this.name = this.route.snapshot.queryParamMap.get('name') || '';
    this.http.post('/api/rule-packs', {}).subscribe({
      next: (res: any) => { this.packs = res.received || []; this.cdr.detectChanges(); },
      error: () => {},
    });
  }

  get wantsRules() { return this.features['general_rules'] || this.features['pub_rules']; }
  get pubs() { return this.pubsText.split('\n').map(p => p.trim()).filter(Boolean); }
  get lastStep() { return this.wantsRules ? 4 : 3; }

  next() {
    this.error = '';
    if (this.step === 1 && !this.name.trim()) { this.error = 'Give it a name first.'; return; }
    if (this.step < this.lastStep) { this.step++; window.scrollTo({ top: 0 }); } else { this.create(); }
  }
  back() { if (this.step > 1) this.step--; }

  async create() {
    if (this.busy) return;
    this.busy = true;
    this.error = '';
    try {
      const made: any = await firstValueFrom(this.http.post('/api/create-crawl', { name: this.name.trim() }));
      if (made.status !== 'success') throw { error: made };
      const eventId = made.received;
      await firstValueFrom(this.http.post('/api/quick-setup', {
        event_id: eventId,
        teams: this.features['teams'] ? this.teamCount : 0,
        pubs: this.pubs,
        pack_id: this.wantsRules ? this.packId : null,
        wheel: this.features['wheel'],
        awards: this.features['awards'],
        features: this.features,
      }));
      this.router.navigate(['/event-details', eventId]);
    } catch (err: any) {
      this.busy = false;
      this.error = err?.error?.received || "Couldn't create the crawl. Try again.";
      this.cdr.detectChanges();
    }
  }
}
