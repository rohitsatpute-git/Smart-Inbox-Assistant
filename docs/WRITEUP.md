# Smart Inbox Assistant — technical write-up

Clinevo live assignment prototype. **No real patient or client data was used.** Sample emails and PDFs are labelled fictional throughout.

## 1. What the system does

A shared mailbox (or a local synthetic ingest) receives emails with PDF attachments. The app:

1. Stores sender, subject, date, body, and files (PDFs processed; other types logged).
2. Detects PDF “flavor” (digital / scanned / article / non-English), pulls tables, captions images, and writes a reviewer summary.
3. Assigns one or more of ICSR, PQC, MI, IRRELEVANT with confidence and a one-line reason.
4. Extracts structured facts with **source type, PDF page, and quote** — or `Not stated`.
5. Lets a reviewer **accept** or **override** (override requires a reason). Every AI job and review is timestamped in Oracle.

## 2. Architecture

```
Gmail IMAP ──► Spring Boot ──► PROCESSING_JOB queue (Oracle)
                     │
                     ▼
              Python FastAPI ──► Gemini 2.0 Flash (JSON + vision)
                     │
Angular 4200 ◄── REST + Basic auth
                     │
                   Oracle Free 23c (Docker)
```

**Why this split.** It matches Clinevo’s production shape: Java for orchestration and audit, Python for PDF/LLM libraries, Angular for the reviewer. The queue is in-process + database rather than Kafka — enough for a prototype, and it survives a UI refresh while OCR runs.

**Oracle** is `gvenzl/oracle-free` with JDBC from Spring. Schema lives in `db/00-schema-sys.sql` (init as SYS into the `SMARTINBOX` schema) plus `db/schema.sql` for the app user.

## 3. Model choice

**Google Gemini 2.0 Flash** (`GEMINI_MODEL` overrideable): cheap/fast enough for 10–15 documents, native vision for scans and product photos, and `response_mime_type=application/json` for structured classification and extraction.

**Data-handling trade-off:** prompts and PDF page images go to Google’s cloud API. That is unacceptable for real ICSRs without a BAA/DPA, regional residency, and redaction. This prototype only sends **synthetic** text. Production options: Vertex AI in a locked project, on-prem OCR (e.g. Tesseract + a private LLM), or a vendor with a pharmacovigilance-ready contract.

If `GEMINI_API_KEY` is missing, the Python service still classifies/extracts with **transparent heuristics** so the stack is demoable offline. Confidence scores are lower and summaries are truncated extracts, not 10–15 generated sentences.

## 4. Prompting approach

A shared system preamble encodes Section 2 of the assignment:

- Multi-label is allowed (defective product that also caused a reaction).
- Four buckets with plain-English tests (four ICSR elements even loosely; PQC = physical product; MI = questions without AE/defect).
- **Never guess**; use `Not stated`.

Separate calls keep failure domains small:

| Call | Output |
|---|---|
| Classify | `{category, confidence, reason}[]` |
| Extract | Field list with `source_type`, `attachment_id`, `page_no`, `quote_snippet` |
| PDF summary | 10–15 sentences + relevance |
| Scan OCR | Per-page transcription + `ocr_confidence` |
| Translate | English text + original excerpt |
| Image caption | Short description + `needs_review` |

Temperature is 0.1. JSON is parsed with a fenced-block fallback. Failures fall back to heuristics rather than inventing facts.

## 5. PDF handling

| Flavor | Detection | Handling |
|---|---|---|
| Digital | Enough extractable characters | PyMuPDF text + pdfplumber tables |
| Scanned / handwritten | Sparse text | Render pages → Gemini vision; show OCR confidence |
| Article | `abstract` / `references` / multi-page | Keep full text; summary should prefer the case narrative over references (prompted) |
| Non-English | `langdetect` | Translate to English for the reviewer; store original excerpt |

Embedded images above a size threshold are captioned and flagged for humans. Deep image diagnosis is out of scope.

## 6. Traceability and audit

- `extracted_field` stores source + snippet.
- `ai_audit_log` + PL/SQL `log_ai_event` record ingest, job start/done/fail, reviews.
- `review_action` stores old/new JSON payloads and reviewer identity from HTTP Basic.

## 7. Known limitations

- IMAP uniqueness is not Gmail’s true UID (JavaMail folder + message number); a Graph/Gmail API integration would be better in production.
- Article “ignore references” is prompt-level, not a layout parser (no GROBID).
- Handwriting OCR quality depends entirely on Gemini; confidence is model-reported, not calibrated.
- No MedDRA coding, duplicate detection, or E2B(R3) export.
- Basic auth is a walkthrough convenience, not SSO.
- Oracle Simple JDBC inserts + CLOBs are adequate for demo volume, not a 100k/day mailbox.
- Literature screening (assignment §4) is **not** implemented as a separate upload workflow; article PDFs in the mailbox still go through the same pipeline.

## 8. What I would change for production

- Replace the DB job table with a durable broker, idempotent consumers, and poison-message handling.
- Calibrate confidence (reviewer agree/disagree as labels) and force low-confidence items to the top of the queue.
- Keep originals in object storage; store hashes; encrypt at rest.
- Human-in-the-loop SLAs, four-eye review for death/life-threatening.
- On-prem or VPC-only models; strip identifiers before any cloud call if policy requires it.
- Automated evaluation set (the synthetic corpus in `testdata/`) as a regression suite for prompts.

## 9. How to demo

Generate testdata, start Oracle + Python + Java + Angular, click **Load synthetic samples**, process ~18 messages, open a complete ICSR, an incomplete one (`Not stated`), a PQC, an MI, the marketing email, a scan, and a Spanish/French PDF. Accept one, override another with a reason, show `review_action` / audit.
