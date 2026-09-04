from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.gemini_client import GeminiClient
from app.pipeline import run_pipeline
from app.schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(title="Smart Inbox AI Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
gemini = GeminiClient()


@app.get("/health")
def health():
    return {"status": "ok", "gemini": gemini.enabled, "model": gemini.model_name}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    return run_pipeline(req, gemini)
