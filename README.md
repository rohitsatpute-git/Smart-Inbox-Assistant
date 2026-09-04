# Smart Inbox Assistant

Working prototype for the Clinevo assignment: read a mailbox, understand email + PDF attachments, classify into ICSR / PQC / MI / IRRELEVANT (multi-label), extract sourced facts, and let a human reviewer accept or override.

**All sample content is synthetic. Do not send real patient data to Gemini or this app.**

## Architecture

Angular (reviewer UI) → Spring Boot (IMAP, queue, Oracle, REST) → Python FastAPI (Gemini / heuristics) → Oracle Database Free.

Jobs are rows in `processing_job` (`PENDING` → `PROCESSING` → `DONE`/`FAILED`), drained by a Spring scheduler.

## Prerequisites

- Docker Desktop
- A Google Gemini API key (optional but recommended)
- Gmail with IMAP + App Password (optional if you use **Load synthetic samples**)

JDK, Python, and Node are only needed if you run services on the host instead of Docker.

## Environment

```bash
copy .env.example .env
```

Fill in placeholders only — never commit real keys. Compose reads `.env` automatically.

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Python AI service |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | IMAP poller + SMTP send script |
| `ORACLE_*` | Host JDBC URL if you run Spring locally against Docker Oracle |
| `REVIEWER_USER` / `REVIEWER_PASSWORD` | UI basic auth (default `reviewer` / `reviewer123`) |

## Run with Docker

From the repo root (quote the path if it contains spaces):

```bash
docker compose up --build
```

First start pulls Oracle and builds the AI, backend, and frontend images. Oracle can take several minutes to become healthy; Compose waits before starting Spring Boot.

| Service | Container | Port |
|---|---|---|
| Angular UI (nginx) | `smart-inbox-frontend` | http://localhost:4200 |
| Spring Boot | `smart-inbox-backend` | http://localhost:8080 |
| Python AI | `smart-inbox-ai` | http://localhost:8000 |
| Oracle Free | `smart-inbox-oracle` | localhost:1521 |
| Synthetic PDFs | `smart-inbox-testdata` | one-shot generator |

Open http://localhost:4200 — sign in as `reviewer` / `reviewer123`.

Click **Load synthetic samples** (ingests `testdata/manifest.json` without Gmail). Wait until statuses become `DONE`, then open an item, inspect sourced fields, **Accept** or **Override**.

Without `GEMINI_API_KEY`, classification/extraction fall back to heuristics so the demo still runs.

```bash
docker compose down
```

Add `-v` only if you also want to drop the Oracle data volume.

## Run locally (without app containers)

1. **Oracle only**

   ```bash
   docker compose up -d oracle
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

6. Use the same UI steps as above (login, **Load synthetic samples**, review).

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
