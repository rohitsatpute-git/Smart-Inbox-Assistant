from __future__ import annotations

import json
import time

from app.gemini_client import GeminiClient
from app.heuristics import heuristic_classify, heuristic_fields
from app.pdf_pipeline import PdfWork, inspect_pdf, png_for_caption
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClassificationOut,
    FieldOut,
    ImageOut,
    PdfAnalysisOut,
    TableOut,
)

CLASSIFY_PROMPT = """Classify this inbound healthcare mailbox item into one or more of: ICSR, PQC, MI, IRRELEVANT.
Provide confidence 0-1 and a one-line reason for EACH label you assign.
JSON schema:
{{"classifications":[{{"category":"ICSR|PQC|MI|IRRELEVANT","confidence":0.0,"reason":"..."}}]}}

EMAIL SENDER: {sender}
SUBJECT: {subject}
BODY:
{body}

PDF TEXT (may be empty):
{pdf_text}
"""

EXTRACT_PROMPT = """Extract facts from this item. Use "Not stated" when missing. Never guess.
Include a source for every field: source_type=email|pdf, optional attachment_id, optional page_no, and a short quote_snippet copied from the input.
Only populate groups relevant to the labels {labels}.

ICSR groups: Patient (age, sex, weight_height, history), Reporter (who, role, country), Product (name, dose, route, start_stop), Reaction (what, onset, outcome), Severity (serious), Narrative (case_summary).
PQC groups: Quality (product, batch_lot, defect, photo_mentioned).
MI groups: Inquiry (questions, product_topic).

JSON:
{{"fields":[{{"group":"","name":"","value":"","confidence":0.0,"source_type":"email","attachment_id":null,"page_no":null,"quote_snippet":""}}]}}

EMAIL:
{email}

PDF:
{pdf_text}
"""

SUMMARY_PROMPT = """Write a 10-15 sentence summary of this PDF for a human safety reviewer.
Say whether it looks relevant to a safety report, quality complaint, or medical question, and why.
If scanned/handwritten, mention uncertainty.
JSON: {{"summary":"...","relevance_note":"...","ocr_confidence":0.0}}

Flavor: {flavor}
Language: {language}
Text:
{text}
"""

TRANSLATE_PROMPT = """Detect language and translate to English. Keep a short original excerpt.
JSON: {{"language":"xx","english_text":"...","original_excerpt":"..."}}

TEXT:
{text}
"""

VISION_OCR_PROMPT = """This is a scanned or handwritten form page (synthetic). Transcribe all readable text.
JSON: {{"text":"...","ocr_confidence":0.0}}
"""

IMAGE_CAPTION_PROMPT = """Describe this image in 1-3 sentences for a pharmacovigilance reviewer (rash, damaged pack, checkbox form, etc.).
Flag needs_review=true if it could be clinically or quality relevant.
JSON: {{"description":"...","needs_review":true}}
"""


def _safe_json_list(data: dict, key: str) -> list:
    v = data.get(key) or []
    return v if isinstance(v, list) else []


def run_pipeline(req: AnalyzeRequest, gemini: GeminiClient) -> AnalyzeResponse:
    t0 = time.perf_counter()
    works: list[PdfWork] = []
    pdf_analyses: list[PdfAnalysisOut] = []

    for att in req.attachments:
        t_pdf = time.perf_counter()
        work = inspect_pdf(att.id, att.filename, att.path)
        english = work.combined_text
        original = work.original_excerpt
        language = work.language
        ocr = work.ocr_confidence

        if gemini.enabled and work.flavor == "scanned" and work.page_images:
            chunks = []
            confs = []
            for page_no, png in work.page_images:
                try:
                    data = gemini.generate_json(VISION_OCR_PROMPT, images=[(png, "image/png")])
                    chunks.append(f"[page {page_no}]\n{data.get('text','')}")
                    if data.get("ocr_confidence") is not None:
                        confs.append(float(data["ocr_confidence"]))
                except Exception:
                    chunks.append(f"[page {page_no}]\n{work.page_texts[page_no-1] if page_no-1 < len(work.page_texts) else ''}")
            english = "\n".join(chunks)
            original = english[:4000]
            ocr = sum(confs) / len(confs) if confs else 0.5
            work.combined_text = english

        if gemini.enabled and language not in ("en", "unknown") and (work.combined_text or "").strip():
            try:
                tr = gemini.generate_json(TRANSLATE_PROMPT.format(text=work.combined_text[:12000]))
                language = tr.get("language") or language
                english = tr.get("english_text") or english
                original = tr.get("original_excerpt") or original
                work.english_text = english
                if work.flavor == "digital":
                    work.flavor = "non_english"
            except Exception:
                pass

        images_out: list[ImageOut] = []
        if gemini.enabled:
            for img in work.extra_images[:3]:
                try:
                    cap = gemini.generate_json(IMAGE_CAPTION_PROMPT, images=[(png_for_caption(img["png"]), "image/png")])
                    images_out.append(
                        ImageOut(
                            page_no=img.get("page_no"),
                            description=str(cap.get("description") or "Image present; needs human review"),
                            needs_review=bool(cap.get("needs_review", True)),
                        )
                    )
                except Exception:
                    images_out.append(ImageOut(page_no=img.get("page_no"), description="Embedded image; needs human review", needs_review=True))
        else:
            for img in work.extra_images[:3]:
                images_out.append(ImageOut(page_no=img.get("page_no"), description="Embedded image (Gemini off); needs human review", needs_review=True))

        summary = None
        relevance = None
        if gemini.enabled:
            try:
                sm = gemini.generate_json(
                    SUMMARY_PROMPT.format(
                        flavor=work.flavor,
                        language=language,
                        text=(english or original or "")[:14000],
                    )
                )
                summary = sm.get("summary")
                relevance = sm.get("relevance_note")
                if sm.get("ocr_confidence") is not None:
                    ocr = float(sm["ocr_confidence"])
            except Exception:
                summary = (english or original or "Not stated")[:1500]
                relevance = "Summary fallback because Gemini summary call failed."
        else:
            blob = (english or original or "").strip()
            summary = (blob[:1500] + ("…" if len(blob) > 1500 else "")) or "Not stated — no extractable text."
            relevance = f"Heuristic flavor={work.flavor}; set GEMINI_API_KEY for a 10–15 sentence reviewer summary."

        pdf_analyses.append(
            PdfAnalysisOut(
                attachment_id=att.id,
                flavor=work.flavor,
                language=language,
                original_excerpt=original,
                english_text=english,
                summary_text=summary,
                relevance_note=relevance,
                ocr_confidence=ocr,
                duration_ms=int((time.perf_counter() - t_pdf) * 1000),
                tables=[TableOut(page_no=t.get("page_no"), table_json=t.get("table_json")) for t in work.tables],
                images=images_out,
            )
        )
        work.english_text = english
        works.append(work)

    pdf_blob = "\n\n".join(f"[attachment {w.attachment_id} {w.filename}]\n{w.english_text}" for w in works)
    used = False
    classifications: list[ClassificationOut]
    fields: list[FieldOut]

    if gemini.enabled:
        try:
            raw = gemini.generate_json(
                CLASSIFY_PROMPT.format(
                    sender=req.sender or "",
                    subject=req.subject or "",
                    body=req.body or "",
                    pdf_text=pdf_blob[:16000],
                )
            )
            classifications = [
                ClassificationOut(
                    category=str(c.get("category", "IRRELEVANT")).upper(),
                    confidence=float(c.get("confidence") or 0.5),
                    reason=str(c.get("reason") or "No reason provided"),
                )
                for c in _safe_json_list(raw, "classifications")
            ]
            used = True
        except Exception:
            classifications = heuristic_classify(req.subject or "", req.body or "", pdf_blob)
    else:
        classifications = heuristic_classify(req.subject or "", req.body or "", pdf_blob)

    if not classifications:
        classifications = [ClassificationOut(category="IRRELEVANT", confidence=0.4, reason="No labels produced")]

    labels = [c.category for c in classifications]
    if gemini.enabled:
        try:
            raw_f = gemini.generate_json(
                EXTRACT_PROMPT.format(
                    labels=json.dumps(labels),
                    email=f"FROM: {req.sender}\nSUBJECT: {req.subject}\n\n{req.body}",
                    pdf_text=pdf_blob[:18000],
                )
            )
            fields = []
            for f in _safe_json_list(raw_f, "fields"):
                val = f.get("value")
                if val is None or str(val).strip() == "":
                    val = "Not stated"
                fields.append(
                    FieldOut(
                        group=str(f.get("group") or "Unknown"),
                        name=str(f.get("name") or "unknown"),
                        value=str(val),
                        confidence=float(f.get("confidence") or 0.5),
                        source_type=f.get("source_type") or "email",
                        attachment_id=f.get("attachment_id"),
                        page_no=f.get("page_no"),
                        quote_snippet=f.get("quote_snippet"),
                    )
                )
            used = True
        except Exception:
            fields = heuristic_fields(req.subject or "", req.body or "", pdf_blob, labels)
    else:
        fields = heuristic_fields(req.subject or "", req.body or "", pdf_blob, labels)

    return AnalyzeResponse(
        message_id=req.message_id,
        classifications=classifications,
        fields=fields,
        pdf_analyses=pdf_analyses,
        duration_ms=int((time.perf_counter() - t0) * 1000),
        model=gemini.model_name if gemini.enabled else "heuristic",
        used_gemini=used,
    )
