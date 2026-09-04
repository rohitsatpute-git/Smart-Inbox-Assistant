from __future__ import annotations

import re

from app.schemas import ClassificationOut, FieldOut

AE_WORDS = re.compile(
    r"adverse|rash|nausea|vomit|hospital|death|anaphyla|reaction|fever|dizziness|hives",
    re.I,
)
PQC_WORDS = re.compile(
    r"broken seal|wrong color|contaminat|damaged|counterfeit|leaking|particulate|packaging|cracked vial",
    re.I,
)
MI_WORDS = re.compile(r"\?|how (do|should)|dose|dosing|interact|take with|pregnancy", re.I)
IRREL = re.compile(r"unsubscribe|newsletter|webinar|conference|marketing|sale", re.I)


def heuristic_classify(subject: str, body: str, pdf_text: str) -> list[ClassificationOut]:
    text = f"{subject}\n{body}\n{pdf_text}"
    out: list[ClassificationOut] = []
    if AE_WORDS.search(text):
        out.append(ClassificationOut(category="ICSR", confidence=0.62, reason="Heuristic: adverse-event language present"))
    if PQC_WORDS.search(text):
        out.append(ClassificationOut(category="PQC", confidence=0.64, reason="Heuristic: product-quality defect language present"))
    if MI_WORDS.search(text) and not AE_WORDS.search(text) and not PQC_WORDS.search(text):
        out.append(ClassificationOut(category="MI", confidence=0.6, reason="Heuristic: question/dosing language without AE or defect"))
    if IRREL.search(text) and not out:
        out.append(ClassificationOut(category="IRRELEVANT", confidence=0.7, reason="Heuristic: marketing/admin language"))
    if not out:
        out.append(ClassificationOut(category="IRRELEVANT", confidence=0.4, reason="Heuristic: no ICSR/PQC/MI cues"))
    return out


def _grab(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else "Not stated"


def heuristic_fields(subject: str, body: str, pdf_text: str, labels: list[str]) -> list[FieldOut]:
    text = f"{subject}\n{body}\n{pdf_text}"
    fields: list[FieldOut] = []
    if "ICSR" in labels:
        pairs = [
            ("Patient", "age", r"age[:\s]+(\d{1,3})"),
            ("Patient", "sex", r"\b(male|female|man|woman)\b"),
            ("Patient", "weight_height", r"(?:weight|kg)[:\s]+([0-9.]+\s*kg)?"),
            ("Patient", "history", r"history[:\s]+([^\n]+)"),
            ("Reporter", "who", r"reporter[:\s]+([^\n]+)"),
            ("Reporter", "role", r"\b(physician|doctor|pharmacist|nurse|patient|consumer)\b"),
            ("Reporter", "country", r"country[:\s]+([A-Za-z ]+)"),
            ("Product", "name", r"(?:product|drug|medication)[:\s]+([A-Za-z0-9\- ]+)"),
            ("Product", "dose", r"dose[:\s]+([^\n]+)"),
            ("Product", "route", r"route[:\s]+([^\n]+)"),
            ("Product", "start_stop", r"(?:start|started)[:\s]+([^\n]+)"),
            ("Reaction", "what", r"(?:reaction|event)[:\s]+([^\n]+)"),
            ("Reaction", "onset", r"(?:onset|started)[:\s]+([^\n]+)"),
            ("Reaction", "outcome", r"outcome[:\s]+([^\n]+)"),
            ("Severity", "serious", r"\b(death|hospitali[sz]ed|life-threatening|serious)\b"),
        ]
        for group, name, pat in pairs:
            val = _grab(pat, text)
            fields.append(
                FieldOut(
                    group=group,
                    name=name,
                    value=val,
                    confidence=0.55 if val != "Not stated" else 0.9,
                    source_type="email" if val != "Not stated" and val.lower() in (body or "").lower() else "pdf",
                    quote_snippet=val if val != "Not stated" else None,
                )
            )
        fields.append(
            FieldOut(
                group="Narrative",
                name="case_summary",
                value=(body or pdf_text or "Not stated")[:1200],
                confidence=0.5,
                source_type="email",
            )
        )
    if "PQC" in labels:
        fields.extend(
            [
                FieldOut(group="Quality", name="product", value=_grab(r"(?:product|drug)[:\s]+([^\n]+)", text), confidence=0.55, source_type="email"),
                FieldOut(group="Quality", name="batch_lot", value=_grab(r"(?:batch|lot)[:\s#]*([A-Za-z0-9\-]+)", text), confidence=0.6, source_type="email"),
                FieldOut(group="Quality", name="defect", value=_grab(r"(broken seal|wrong color|contaminat\w*|damaged[^\n.]+|counterfeit|leaking[^\n.]+)", text), confidence=0.6, source_type="email"),
                FieldOut(
                    group="Quality",
                    name="photo_mentioned",
                    value="yes" if re.search(r"photo|picture|image|attached", text, re.I) else "Not stated",
                    confidence=0.7,
                    source_type="email",
                ),
            ]
        )
    if "MI" in labels:
        q = "Not stated"
        m = re.search(r"(.{10,180}\?)", text)
        if m:
            q = m.group(1).strip()
        fields.extend(
            [
                FieldOut(group="Inquiry", name="questions", value=q, confidence=0.55, source_type="email"),
                FieldOut(group="Inquiry", name="product_topic", value=_grab(r"(?:product|drug|about)[:\s]+([A-Za-z0-9\- ]+)", text), confidence=0.5, source_type="email"),
            ]
        )
    return fields
