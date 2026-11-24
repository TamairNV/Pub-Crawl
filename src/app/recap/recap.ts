import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';

// End-of-crawl recap + a shareable winners poster (PNG drawn in the browser).
@Component({
  selector: 'app-recap',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe],
  templateUrl: './recap.html',
  styleUrls: ['./recap.css'],
})
export class RecapComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private cdr = inject(ChangeDetectorRef);
  eventId = '';
  r: any = null;
  error = '';
  sharing = false;
  note = '';

  ngOnInit() {
    this.eventId = this.route.snapshot.paramMap.get('id') || '';
    this.http.post<any>('/api/recap', { event_id: this.eventId }).subscribe({
      next: (res) => { this.r = res.received; this.cdr.detectChanges(); },
      error: (err) => { this.error = err?.error?.received || "Couldn't load the recap."; this.cdr.detectChanges(); },
    });
  }

  medal(i: number) { return ['🥇', '🥈', '🥉'][i] || `#${i + 1}`; }

  private poster(): HTMLCanvasElement {
    const r = this.r, W = 1080, H = 1350;
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const g = c.getContext('2d')!;
    const text = (t: string, x: number, y: number, font: string, fill: string, stroke = 0) => {
      g.font = font; g.fillStyle = fill;
      if (stroke) { g.lineWidth = stroke; g.strokeStyle = '#111827'; g.strokeText(t, x, y); }
      g.fillText(t, x, y);
    };
    g.fillStyle = '#1f2937'; g.fillRect(0, 0, W, H);
    g.textAlign = 'center';
    text('CHAMPIONS', W / 2, 150, '900 110px Nunito, Arial Black, sans-serif', '#fbbf24', 12);
    text((r.event.name || '').slice(0, 38), W / 2, 225, '800 46px Nunito, Arial, sans-serif', '#f0f8ff');
    const win = r.teams[0];
    if (win) {
      g.fillStyle = '#fbbf24'; this.round(g, 112, 292, 856, 300, 36); g.fill();
      g.fillStyle = win.colour || '#ef4444'; this.round(g, 100, 280, 856, 300, 36); g.fill();
      g.lineWidth = 8; g.strokeStyle = '#111827'; g.stroke();
      text('🏆', W / 2, 390, '90px sans-serif', '#fff');
      text(win.name.slice(0, 20).toUpperCase(), W / 2, 485, '900 84px Nunito, Arial Black, sans-serif', '#ffffff', 10);
      text(`${win.points} points`, W / 2, 550, '900 44px Nunito, Arial, sans-serif', '#111827');
    }
    let y = 680;
    r.teams.slice(1, 4).forEach((t: any, i: number) => {
      text(`${i + 2}. ${t.name.slice(0, 22)}  ·  ${t.points}`, W / 2, y, '800 48px Nunito, Arial, sans-serif', '#f0f8ff'); y += 70;
    });
    y += 20;
    const mvp = r.top_players[0];
    if (mvp) { text('⭐ MVP', W / 2, y, '900 44px Nunito, Arial, sans-serif', '#fbbf24'); y += 60;
      text(`${mvp.name.slice(0, 24)} (${mvp.points})`, W / 2, y, '800 50px Nunito, Arial, sans-serif', '#ffffff'); y += 80; }
    (r.awards || []).filter((a: any) => a.winner).slice(0, 3).forEach((a: any) => {
      text(`${a.name}: ${a.winner.name}`.slice(0, 40), W / 2, y, '800 40px Nunito, Arial, sans-serif', '#bfdbfe'); y += 58;
    });
    text(`${r.stats.players} players · ${r.stats.pubs} pubs · ${r.stats.points} points`, W / 2, H - 100, '800 36px Nunito, Arial, sans-serif', '#9ca3af');
    text('CRAWLR', W / 2, H - 40, '900 38px Nunito, Arial, sans-serif', '#bfdbfe');
    return c;
  }

  private round(g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, rr: number) {
    g.beginPath(); g.moveTo(x + rr, y); g.arcTo(x + w, y, x + w, y + h, rr); g.arcTo(x + w, y + h, x, y + h, rr);
    g.arcTo(x, y + h, x, y, rr); g.arcTo(x, y, x + w, y, rr); g.closePath();
  }

  async share() {
    if (!this.r) return;
    this.sharing = true; this.note = '';
    try {
      const blob: Blob = await new Promise((res, rej) => this.poster().toBlob(b => b ? res(b) : rej(), 'image/png'));
      const file = new File([blob], 'winners.png', { type: 'image/png' });
      const nav: any = navigator;
      if (nav.canShare?.({ files: [file] })) await nav.share({ files: [file], title: `${this.r.event.name}: winners` });
      else { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'winners.png'; a.click();
             setTimeout(() => URL.revokeObjectURL(a.href), 5000); this.note = 'Saved winners.png'; }
    } catch { /* share sheet closed */ }
    this.sharing = false; this.cdr.detectChanges();
  }
}
