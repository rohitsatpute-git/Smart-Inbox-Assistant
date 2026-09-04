import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, MessageSummary } from './api.service';

@Component({
  selector: 'app-queue',
  imports: [RouterLink],
  template: `
    <div class="toolbar">
      <h2>Review queue</h2>
      <div class="row">
        <button (click)="loadSamples()" [disabled]="busy">Load synthetic samples</button>
        <button class="ghost" (click)="refresh()">Refresh</button>
      </div>
    </div>
    @if (error) {
      <p class="error">{{ error }}</p>
    }
    <table class="queue">
      <thead>
        <tr>
          <th>ID</th>
          <th>Subject</th>
          <th>From</th>
          <th>Status</th>
          <th>AI labels</th>
          <th>Confidence</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody>
        @for (m of messages; track m.id) {
          <tr [routerLink]="['/messages', m.id]">
            <td>{{ m.id }}</td>
            <td>
              <strong>{{ m.subject }}</strong>
              <div class="preview">{{ m.summaryPreview }}</div>
            </td>
            <td>{{ m.sender }}</td>
            <td><span class="chip">{{ m.status }}</span></td>
            <td>
              @for (c of m.classifications; track c.id) {
                <span class="chip cat">{{ c.category }}</span>
              }
            </td>
            <td>
              @for (c of m.classifications; track c.id) {
                <div>{{ pct(c.confidence) }} — {{ c.reason }}</div>
              }
            </td>
            <td>{{ m.durationMs ? m.durationMs + ' ms' : '—' }}</td>
          </tr>
        }
      </tbody>
    </table>
    @if (!messages.length && !error) {
      <p class="muted">No messages yet. Use Load synthetic samples (needs testdata) or wait for IMAP.</p>
    }
  `,
})
export class QueueComponent implements OnInit {
  messages: MessageSummary[] = [];
  error = '';
  busy = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.refresh();
  }

  refresh(): void {
    this.error = '';
    this.api.list().subscribe({
      next: (rows) => (this.messages = rows),
      error: (e) => (this.error = e.message || 'Failed to load queue. Is the API running?'),
    });
  }

  loadSamples(): void {
    this.busy = true;
    this.api.loadSamples().subscribe({
      next: () => {
        this.busy = false;
        this.refresh();
      },
      error: (e) => {
        this.busy = false;
        this.error = e.message || 'Load failed';
      },
    });
  }

  pct(c: number | null): string {
    if (c == null) return '—';
    return Math.round(c * 100) + '%';
  }
}
