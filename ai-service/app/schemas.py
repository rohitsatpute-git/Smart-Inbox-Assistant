from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AttachmentIn(BaseModel):
    id: int
    filename: str
    path: str
    mime: Optional[str] = None


class AnalyzeRequest(BaseModel):
    message_id: int
    sender: Optional[str] = ""
    subject: Optional[str] = ""
    body: Optional[str] = ""
    received_at: Optional[str] = ""
    attachments: list[AttachmentIn] = Field(default_factory=list)


class ClassificationOut(BaseModel):
    category: str
    confidence: float
    reason: str


class FieldOut(BaseModel):
    group: str
    name: str
    value: str
    confidence: float
    source_type: Optional[str] = "email"
    attachment_id: Optional[int] = None
    page_no: Optional[int] = None
    quote_snippet: Optional[str] = None


class TableOut(BaseModel):
    page_no: Optional[int] = None
    table_json: Any = None


class ImageOut(BaseModel):
    page_no: Optional[int] = None
    description: str
    needs_review: bool = True


class PdfAnalysisOut(BaseModel):
    attachment_id: int
    flavor: str
    language: str
    original_excerpt: Optional[str] = None
    english_text: Optional[str] = None
    summary_text: Optional[str] = None
    relevance_note: Optional[str] = None
    ocr_confidence: Optional[float] = None
    duration_ms: Optional[int] = None
    tables: list[TableOut] = Field(default_factory=list)
    images: list[ImageOut] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    message_id: int
    classifications: list[ClassificationOut]
    fields: list[FieldOut]
    pdf_analyses: list[PdfAnalysisOut]
    duration_ms: int
    model: str
    used_gemini: bool
