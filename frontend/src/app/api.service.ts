import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface ClassificationDto {
  id: number;
  category: string;
  confidence: number | null;
  reason: string;
  source: string;
}

export interface ExtractedFieldDto {
  id: number;
  group: string;
  name: string;
  value: string;
  confidence: number | null;
  sourceType: string | null;
  attachmentId: number | null;
  pageNo: number | null;
  quoteSnippet: string | null;
}

export interface AttachmentDto {
  id: number;
  filename: string;
  mimeType: string;
  pdf: boolean;
  processed: boolean;
}

export interface TableExtractDto {
  id: number;
  pageNo: number | null;
  tableJson: string | null;
}

export interface ImageFlagDto {
  id: number;
  pageNo: number | null;
  description: string;
  needsReview: boolean;
}

export interface PdfAnalysisDto {
  id: number;
  attachmentId: number;
  flavor: string;
  language: string;
  originalExcerpt: string | null;
  englishText: string | null;
  summaryText: string | null;
  relevanceNote: string | null;
  ocrConfidence: number | null;
  durationMs: number | null;
  tables: TableExtractDto[];
  images: ImageFlagDto[];
}

export interface ReviewActionDto {
  id: number;
  actionType: string;
  reviewer: string;
  reason: string;
  createdAt: string;
}

export interface MessageSummary {
  id: number;
  sender: string;
  subject: string;
  receivedAt: string;
  status: string;
  classifications: ClassificationDto[];
  summaryPreview: string | null;
  durationMs: number | null;
}

export interface MessageDetail {
  id: number;
  sender: string;
  subject: string;
  receivedAt: string;
  bodyText: string;
  status: string;
  attachments: AttachmentDto[];
  classifications: ClassificationDto[];
  fields: ExtractedFieldDto[];
  pdfAnalyses: PdfAnalysisDto[];
  reviews: ReviewActionDto[];
  durationMs: number | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  list(): Observable<MessageSummary[]> {
    return this.http.get<MessageSummary[]>('/api/messages');
  }

  get(id: number): Observable<MessageDetail> {
    return this.http.get<MessageDetail>(`/api/messages/${id}`);
  }

  review(id: number, body: unknown): Observable<MessageDetail> {
    return this.http.post<MessageDetail>(`/api/messages/${id}/review`, body);
  }

  loadSamples(): Observable<{ loaded: number }> {
    return this.http.post<{ loaded: number }>('/api/demo/load-samples', {});
  }

  pdfBlob(attachmentId: number): Observable<Blob> {
    return this.http.get(`/api/attachments/${attachmentId}/file`, { responseType: 'blob' });
  }
}
