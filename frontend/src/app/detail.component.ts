import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ApiService, MessageDetail } from './api.service';

@Component({
  selector: 'app-detail',
  imports: [FormsModule, RouterLink],
  template: `
    <a routerLink="/">← Queue</a>
    @if (msg) {
      <div class="detail-grid">
        <section>
          <h2>{{ msg.subject }}</h2>
          <p class="muted">{{ msg.sender }} · {{ msg.receivedAt }} · {{ msg.status }}
            @if (msg.durationMs) { · processed in {{ msg.durationMs }} ms }</p>
          <h3>Email body</h3>
          <pre class="body">{{ msg.bodyText }}</pre>
          <h3>Classifications</h3>
          @for (c of msg.classifications; track c.id) {
            <div class="cls">
              <span class="chip cat">{{ c.category }}</span>
              {{ pct(c.confidence) }} — {{ c.reason }}
              <span class="muted">({{ c.source }})</span>
            </div>
          }
          <h3>PDF viewer</h3>
          @for (a of msg.attachments; track a.id) {
            @if (a.pdf) {
              <button class="ghost" (click)="openPdf(a.id)">View {{ a.filename }}</button>
            } @else {
              <p class="muted">Logged non-PDF: {{ a.filename }}</p>
            }
          }
          @if (pdfUrl) {
            <iframe [src]="pdfUrl" title="PDF"></iframe>
          }
          @for (p of msg.pdfAnalyses; track p.id) {
            <article class="pdf-meta">
              <h4>{{ p.flavor }} · {{ p.language }} @if (p.ocrConfidence != null) { · OCR {{ pct(p.ocrConfidence) }} }</h4>
              <p>{{ p.relevanceNote }}</p>
              <p>{{ p.summaryText }}</p>
              @if (p.originalExcerpt && p.flavor === 'non_english') {
                <details><summary>Original language excerpt</summary><pre>{{ p.originalExcerpt }}</pre></details>
              }
              @for (t of p.tables; track t.id) {
                <details><summary>Table page {{ t.pageNo }}</summary><pre>{{ t.tableJson }}</pre></details>
              }
              @for (im of p.images; track im.id) {
                <p class="warn">Image p.{{ im.pageNo }} (review={{ im.needsReview }}): {{ im.description }}</p>
              }
            </article>
          }
        </section>
        <section>
          <h3>Extracted facts</h3>
          <p class="muted">Edit values then Override (reason required) or Accept as-is. Missing facts stay “Not stated”.</p>
          @for (f of msg.fields; track f.id) {
            <div class="field">
              <label>{{ f.group }} / {{ f.name }}
                <textarea rows="2" [(ngModel)]="f.value"></textarea>
              </label>
              <div class="src">
                conf {{ pct(f.confidence) }} · {{ f.sourceType }}
                @if (f.pageNo != null) { · PDF page {{ f.pageNo }} }
                @if (f.quoteSnippet) { · “{{ f.quoteSnippet }}” }
              </div>
            </div>
          }
          <label>Override reason
            <input [(ngModel)]="reason" placeholder="Required when overriding" />
          </label>
          <div class="row">
            <button (click)="accept()">Accept</button>
            <button class="ghost" (click)="override()">Override</button>
          </div>
          @if (notice) { <p>{{ notice }}</p> }
          <h3>Audit</h3>
          @for (r of msg.reviews; track r.id) {
            <p>{{ r.createdAt }} · {{ r.reviewer }} · {{ r.actionType }} · {{ r.reason }}</p>
          }
        </section>
      </div>
    }
  `,
})
export class DetailComponent implements OnInit, OnDestroy {
  msg: MessageDetail | null = null;
  reason = '';
  notice = '';
  pdfUrl: SafeResourceUrl | null = null;
  private objectUrl: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.get(id).subscribe((m) => {
      this.msg = m;
      const pdf = m.attachments.find((a) => a.pdf);
      if (pdf) this.openPdf(pdf.id);
    });
  }

  ngOnDestroy(): void {
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
  }

  openPdf(id: number): void {
    this.api.pdfBlob(id).subscribe((blob) => {
      if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
      this.objectUrl = URL.createObjectURL(blob);
      this.pdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.objectUrl);
    });
  }

  pct(c: number | null): string {
    if (c == null) return '—';
    return Math.round(c * 100) + '%';
  }

  accept(): void {
    if (!this.msg) return;
    this.api.review(this.msg.id, { actionType: 'ACCEPT', reason: this.reason || 'Accepted AI output' }).subscribe({
      next: (m) => {
        this.msg = m;
        this.notice = 'Accepted and logged.';
      },
    });
  }

  override(): void {
    if (!this.msg) return;
    if (!this.reason.trim()) {
      this.notice = 'Override requires a reason.';
      return;
    }
    this.api.review(this.msg.id, {
      actionType: 'OVERRIDE',
      reason: this.reason,
      classifications: this.msg.classifications,
      fields: this.msg.fields,
    }).subscribe({
      next: (m) => {
        this.msg = m;
        this.notice = 'Override saved.';
      },
    });
  }
}
