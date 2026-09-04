# Smart Inbox Assistant

Working prototype for the Clinevo assignment: read a mailbox, understand email + PDF attachments, classify into ICSR / PQC / MI / IRRELEVANT (multi-label), extract sourced facts, and let a human reviewer accept or override.

**All sample content is synthetic. Do not send real patient data to Gemini or this app.**

## Architecture

Angular (reviewer UI) → Spring Boot (IMAP, queue, Oracle, REST) → Python FastAPI (Gemini / heuristics) → Oracle Database Free.

Jobs are rows in `processing_job` (`PENDING` → `PROCESSING` → `DONE`/`FAILED`), drained by a Spring scheduler.

## Prerequisites

- Docker Desktop
- JDK 25 (or 21+)
- Python 3.11+
- Node.js 20+
- A Google Gemini API key (optional but recommended)
- Gmail with IMAP + App Password (optional if you use **Load synthetic samples**)

## Environment

```bash
copy .env.example .env
```

Fill in placeholders only — never commit real keys.

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Python AI service |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | IMAP poller + SMTP send script |
| `ORACLE_*` | Matches `docker-compose.yml` |
| `REVIEWER_USER` / `REVIEWER_PASSWORD` | UI basic auth (default `reviewer` / `reviewer123`) |

Load `.env` into your shells, or export the same names before starting Java/Python.

## Run locally

1. **Oracle**

   ```bash
   docker compose up -d
   ```

   First start can take several minutes. Wait until the container is healthy.

2. **Synthetic PDFs / emails** (once)

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r ai-service/requirements.txt
   python scripts/generate_testdata.py
   ```

3. **Python AI service** (port 8000)

   ```bash
   cd ai-service
   set GEMINI_API_KEY=your_gemini_api_key_here
   uvicorn app.main:app --reload --port 8000
   ```

   Without a key, classification/extraction fall back to heuristics so the demo still runs.

4. **Spring Boot** (port 8080)

   From `backend/`:

   ```bash
   mvnw.cmd spring-boot:run
   ```

   Working directory should be the repo root or `backend` with `inbox.testdata-dir=../testdata` (default in `application.properties`).

5. **Angular** (port 4200)

   ```bash
   cd frontend
   npm install
   npm start
   ```

6. Open http://localhost:4200 — sign in as `reviewer` / `reviewer123`.

7. Click **Load synthetic samples** (ingests `testdata/manifest.json` without Gmail). Wait until statuses become `DONE`, then open an item, inspect sourced fields, **Accept** or **Override**.

### Real Gmail inbox

Enable IMAP and a Google App Password. Set `GMAIL_USER` and `GMAIL_APP_PASSWORD`, then:

```bash
python scripts/send_samples.py
```

The poller marks messages seen after ingest.

## Sample JSON + timings

With the AI service running:

```bash
python scripts/dump_sample_outputs.py
```

Writes `docs/sample-outputs/*.json` and `docs/sample-outputs/timings.json`.

## API (basic auth)

- `GET /api/messages` — queue
- `GET /api/messages/{id}` — detail
- `POST /api/messages/{id}/review` — `{ "actionType": "ACCEPT"|"OVERRIDE", "reason": "...", "classifications": [...], "fields": [...] }`
- `POST /api/demo/load-samples`
- `GET /api/attachments/{id}/file`

## Write-up

See [docs/WRITEUP.md](docs/WRITEUP.md) for architecture, prompts, limitations, and production notes.
