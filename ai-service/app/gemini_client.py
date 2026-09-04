from __future__ import annotations

import json
import os
import re
from typing import Any

SYSTEM_RULES = """You are a pharmacovigilance intake assistant for SYNTHETIC / fictional data only.
Never invent facts. If a detail is not explicitly present, use the string "Not stated".
Do not guess ages, drugs, dates, or outcomes.
A message may belong to more than one category.

Categories:
- ICSR: Safety report. Needs (even loosely) a patient, a reporter, a product/drug, and a bad outcome/reaction.
- PQC: Quality complaint. Physical product problem (broken seal, wrong color, contamination, damaged packaging, counterfeit).
- MI: Medical information request. Questions about dosing, administration, interactions — no adverse reaction and no defect.
- IRRELEVANT: Marketing, spam, admin chatter, anything else.

Return ONLY valid JSON matching the requested schema.
"""


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self._client = None
        if self.api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def generate_json(self, prompt: str, images: list[tuple[bytes, str]] | None = None) -> dict[str, Any]:
        if not self._client:
            raise RuntimeError("Gemini is not configured")
        from google.genai import types

        parts: list[Any] = [types.Part.from_text(text=SYSTEM_RULES + "\n\n" + prompt)]
        for blob, mime in images or []:
            parts.append(types.Part.from_bytes(data=blob, mime_type=mime or "image/png"))
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=parts,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        text = response.text or "{}"
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            return {"value": parsed, "raw": text}
        parsed["_model"] = self.model_name
        return parsed
