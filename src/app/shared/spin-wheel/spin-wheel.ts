import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
  AfterViewInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { WheelItem, formatRewardBadge } from '../mini-events.types';

export interface SpinCommand {
  seq: number;
  index: number;
  item: WheelItem;
}

@Component({
  selector: 'app-spin-wheel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './spin-wheel.html',
  styleUrl: './spin-wheel.css',
})
export class SpinWheelComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input() wheelName = 'Spin the Wheel';
  @Input() items: WheelItem[] = [];
  @Input() disabled = false;
  @Input() spinCommand: SpinCommand | null = null;

  @Output() spinRequested = new EventEmitter<void>();
  @Output() animationFinished = new EventEmitter<WheelItem>();

  @ViewChild('wheelCanvas') canvasRef?: ElementRef<HTMLCanvasElement>;

  rotationDeg = 0;
  isSpinning = false;
  landedItem: WheelItem | null = null;
  private lastSeq = -1;
  private finishTimer: any = null;

  ngAfterViewInit() {
    this.drawWheel();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['items']) {
      this.drawWheel();
    }
    if (changes['spinCommand'] && this.spinCommand && this.spinCommand.seq !== this.lastSeq) {
      this.lastSeq = this.spinCommand.seq;
      this.startAnimation(this.spinCommand.index, this.spinCommand.item);
    }
  }

  ngOnDestroy() {
    if (this.finishTimer) {
      clearTimeout(this.finishTimer);
    }
  }

  requestSpin() {
    if (this.disabled || this.isSpinning || !this.items.length) {
      return;
    }
    this.landedItem = null;
    this.spinRequested.emit();
  }

  describe(item: WheelItem): string {
    return formatRewardBadge(item.effect_type, item.points);
  }

  private startAnimation(index: number, item: WheelItem) {
    const count = this.items.length;
    if (!count) {
      this.animationFinished.emit(item);
      return;
    }
    if (this.finishTimer) {
      clearTimeout(this.finishTimer);
    }
    this.isSpinning = true;
    this.landedItem = null;

    const sliceDeg = 360 / count;
    const centerDeg = (index + 0.5) * sliceDeg;
    const targetMod = (360 - (centerDeg % 360) + 360) % 360;
    const currentMod = ((this.rotationDeg % 360) + 360) % 360;
    const delta = (targetMod - currentMod + 360) % 360;
    const jitter = (Math.random() - 0.5) * sliceDeg * 0.45;
    this.rotationDeg += 360 * 5 + delta + jitter;

    this.finishTimer = setTimeout(() => {
      this.isSpinning = false;
      this.landedItem = item;
      this.animationFinished.emit(item);
    }, 3900);
  }

  private drawWheel() {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    const size = canvas.width;
    const cx = size / 2;
    const cy = size / 2;
    const radius = size / 2 - 8;
    ctx.clearRect(0, 0, size, size);

    const items = this.items;
    if (!items || items.length === 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = '#e5e7eb';
      ctx.fill();
      ctx.lineWidth = 4;
      ctx.strokeStyle = '#111827';
      ctx.stroke();
      ctx.fillStyle = '#374151';
      ctx.font = '800 18px Nunito, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('No slices yet', cx, cy);
      return;
    }

    const count = items.length;
    const sliceRad = (Math.PI * 2) / count;
    const safeInnerR = 46;
    const safeOuterR = radius - 14;
    const maxRadialW = safeOuterR - safeInnerR;
    const midR = (safeInnerR + safeOuterR) / 2;

    const splitBalanced = (text: string): [string, string] | null => {
      const words = text.trim().split(/\s+/);
      if (words.length < 2) return null;
      let best: [string, string] | null = null;
      let bestDiff = Infinity;
      for (let splitAt = 1; splitAt < words.length; splitAt++) {
        const a = words.slice(0, splitAt).join(' ');
        const b = words.slice(splitAt).join(' ');
        const diff = Math.abs(a.length - b.length);
        if (diff < bestDiff) {
          bestDiff = diff;
          best = [a, b];
        }
      }
      return best;
    };

    const truncateToWidth = (text: string, maxW: number): string => {
      if (ctx.measureText(text).width <= maxW) return text;
      let s = text;
      while (s.length > 1 && ctx.measureText(s + '…').width > maxW) {
        s = s.slice(0, -1);
      }
      return s.trimEnd() + '…';
    };

    const layoutSliceText = (raw: string): { lines: string[]; fontSize: number } => {
      const clean = (raw || '').trim();
      if (!clean) return { lines: [''], fontSize: 12 };

      const singleSizes =
        count > 10 ? [11, 10, 9] : count > 6 ? [13, 12, 11, 10] : [15, 13, 12, 11, 10];
      for (const size of singleSizes) {
        ctx.font = `800 ${size}px Nunito, Segoe UI, sans-serif`;
        if (ctx.measureText(clean).width <= maxRadialW) {
          return { lines: [clean], fontSize: size };
        }
      }

      if (count <= 8) {
        const pair = splitBalanced(clean);
        if (pair) {
          const pairSizes = count <= 4 ? [13, 12, 11, 10] : [12, 11, 10];
          for (const size of pairSizes) {
            ctx.font = `800 ${size}px Nunito, Segoe UI, sans-serif`;
            const widest = Math.max(ctx.measureText(pair[0]).width, ctx.measureText(pair[1]).width);
            const innerX = midR - widest / 2;
            const reqHalfH = size * 1.15 + 3;
            const availHalfH = count <= 2 ? 999 : innerX * Math.tan(sliceRad / 2) - 4;
            if (widest <= maxRadialW && reqHalfH <= availHalfH) {
              return { lines: pair, fontSize: size };
            }
          }
          const fallbackSize = 10;
          ctx.font = `800 ${fallbackSize}px Nunito, Segoe UI, sans-serif`;
          return {
            lines: [truncateToWidth(pair[0], maxRadialW), truncateToWidth(pair[1], maxRadialW)],
            fontSize: fallbackSize,
          };
        }
      }

      const minSize = count > 10 ? 9 : 10;
      ctx.font = `800 ${minSize}px Nunito, Segoe UI, sans-serif`;
      return { lines: [truncateToWidth(clean, maxRadialW)], fontSize: minSize };
    };

    for (let i = 0; i < count; i++) {
      const startAngle = -Math.PI / 2 + i * sliceRad;
      const endAngle = startAngle + sliceRad;
      const midAngle = (startAngle + endAngle) / 2;

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fillStyle = items[i].colour || '#fbbf24';
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#111827';
      ctx.stroke();

      // Label inside slice strictly between center hub and outer rim
      const layout = layoutSliceText(items[i].label || '');
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(midAngle);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = '#111827';
      ctx.font = `800 ${layout.fontSize}px Nunito, Segoe UI, sans-serif`;

      if (layout.lines.length === 1) {
        ctx.fillText(layout.lines[0], midR, 0, maxRadialW);
      } else {
        const lineH = layout.fontSize * 1.15;
        ctx.fillText(layout.lines[0], midR, -lineH / 2, maxRadialW);
        ctx.fillText(layout.lines[1], midR, lineH / 2, maxRadialW);
      }
      ctx.restore();
    }

    // Outer rim
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = 5;
    ctx.strokeStyle = '#111827';
    ctx.stroke();
  }
}
