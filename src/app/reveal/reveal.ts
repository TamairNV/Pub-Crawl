import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';

// Big-screen team reveal for announcing teams in person, plus a shareable PNG of the line-up.
@Component({
  selector: 'app-team-reveal',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './reveal.html',
  styleUrls: ['./reveal.css'],
})
export class TeamRevealComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private cdr = inject(ChangeDetectorRef);

  eventId = '';
  crawlName = '';
  teams: { id: string; name: string; colour: string; members: string[] }[] = [];
  shown = 0;          // teams revealed so far (tap to reveal the next)
  sharing = false;
  note = '';

  ngOnInit() {
    this.eventId = this.route.snapshot.paramMap.get('id') || '';
    this.http.post('/api/get-event-details', { event_id: this.eventId }).subscribe({
      next: (res: any) => {
        const users = res.received?.users || [];
        this.crawlName = res.received?.event?.name || '';
        this.teams = (res.received?.teams || []).map((t: any) => ({
          id: t.id, name: t.name, colour: t.colour || '#fbbf24',
          members: users.filter((u: any) => u.teamID === t.id).map((u: any) => u.name),
        }));
        this.cdr.detectChanges();
      },
    });
  }

  revealNext() { if (this.shown < this.teams.length) this.shown++; }
  revealAll() { this.shown = this.teams.length; }

  private draw(): HTMLCanvasElement {
    const W = 1080, pad = 60, colW = (W - pad * 3) / 2;
    const rows = Math.ceil(this.teams.length / 2);
    const maxMembers = Math.max(1, ...this.teams.map(t => t.members.length));
    const blockH = 120 + maxMembers * 52;
    const H = Math.max(1350, 330 + rows * (blockH + 40) + 80);
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const g = c.getContext('2d')!;
    g.fillStyle = '#1f2937'; g.fillRect(0, 0, W, H);
    g.textAlign = 'center';
    g.font = '900 120px Nunito, Arial Black, sans-serif';
    g.lineWidth = 10; g.strokeStyle = '#111827'; g.fillStyle = '#f0f8ff';
    g.strokeText('TEAMS', W / 2, 170); g.fillText('TEAMS', W / 2, 170);
    g.font = '800 48px Nunito, Arial, sans-serif'; g.fillStyle = '#fbbf24';
    g.fillText(this.crawlName.slice(0, 40), W / 2, 250);
    this.teams.forEach((t, i) => {
      const x = pad + (i % 2) * (colW + pad), y = 310 + Math.floor(i / 2) * (blockH + 40);
      g.fillStyle = '#fbbf24'; this.round(g, x + 12, y + 12, colW, blockH, 28); g.fill();
      g.fillStyle = '#f0f8ff'; this.round(g, x, y, colW, blockH, 28); g.fill();
      g.lineWidth = 6; g.strokeStyle = '#111827'; g.stroke();
      g.fillStyle = t.colour; this.round(g, x, y, colW, 100, 28); g.fill(); g.stroke();
      g.fillStyle = '#ffffff'; g.font = '900 52px Nunito, Arial Black, sans-serif'; g.lineWidth = 8;
      g.strokeText(t.name.slice(0, 18), x + colW / 2, y + 68); g.fillText(t.name.slice(0, 18), x + colW / 2, y + 68);
      g.fillStyle = '#111827'; g.font = '800 40px Nunito, Arial, sans-serif';
      t.members.forEach((m, j) => g.fillText(m.slice(0, 22), x + colW / 2, y + 160 + j * 52));
    });
    g.font = '900 36px Nunito, Arial, sans-serif'; g.fillStyle = '#bfdbfe';
    g.fillText('CRAWLR', W / 2, H - 40);
    return c;
  }

  private round(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
    g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }

  async share() {
    this.sharing = true; this.note = '';
    try {
      const blob: Blob = await new Promise((res, rej) => this.draw().toBlob(b => b ? res(b) : rej(), 'image/png'));
      const file = new File([blob], 'teams.png', { type: 'image/png' });
      const nav: any = navigator;
      if (nav.canShare?.({ files: [file] })) {
        await nav.share({ files: [file], title: `${this.crawlName}: teams` });
      } else {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = 'teams.png'; a.click();
        setTimeout(() => URL.revokeObjectURL(a.href), 5000);
        this.note = 'Saved teams.png';
      }
    } catch { /* share sheet closed */ }
    this.sharing = false; this.cdr.detectChanges();
  }
}
