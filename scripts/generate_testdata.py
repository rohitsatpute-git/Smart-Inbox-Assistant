#!/usr/bin/env python3
"""Generate synthetic emails + PDFs. No real patient data."""
from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdfcanvas

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "testdata" / "pdfs"
PDF.mkdir(parents=True, exist_ok=True)


def write_form(path: Path, title: str, rows: list[tuple[str, str]], extra: str = "") -> None:
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    data = [["Field", "Value"]] + [[k, v] for k, v in rows]
    t = Table(data, colWidths=[2.4 * inch, 4.6 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4f8fb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(t)
    if extra:
        story.append(Spacer(1, 16))
        story.append(Paragraph(extra, styles["BodyText"]))
    doc.build(story)


def write_article(path: Path, title: str, case: str, discussion: str, lang: str = "en") -> None:
    c = pdfcanvas.Canvas(str(path), pagesize=letter)
    w, h = letter
    c.setFont("Times-Bold", 16)
    c.drawString(54, h - 54, title)
    c.setFont("Times-Italic", 9)
    c.drawString(54, h - 70, "Fictional journal — synthetic case for software testing. DOI: 10.0000/fake.case")
    y = h - 100
    c.setFont("Times-Bold", 11)
    c.drawString(54, y, "Abstract")
    y -= 16
    c.setFont("Times-Roman", 9)
    for line in _wrap(case, 95)[:8]:
        c.drawString(54, y, line)
        y -= 12
    y -= 8
    c.setFont("Times-Bold", 11)
    c.drawString(54, y, "Case report")
    y -= 16
    # two columns
    left_x, right_x = 54, 318
    col_w = 240
    body = _wrap(case + " " + discussion, 48)
    mid = max(1, len(body) // 2)
    ly, ry = y, y
    c.setFont("Times-Roman", 9)
    for i, line in enumerate(body):
        if i < mid:
            c.drawString(left_x, ly, line)
            ly -= 11
        else:
            c.drawString(right_x, ry, line)
            ry -= 11
    c.showPage()
    c.setFont("Times-Bold", 12)
    c.drawString(54, h - 54, "References (ignore for case extraction)")
    c.setFont("Times-Roman", 9)
    refs = [
        "1. Smith J. Made-up review of widget tablets. Fake J Med. 2019;1:1-9.",
        "2. Doe A. Unrelated mechanism paper. Imaginary Pharmacol. 2020;2:10-20.",
        "3. Lee B. General discussion of nausea. Placeholder Clin. 2021;3:30-40.",
    ]
    y = h - 80
    for r in refs:
        c.drawString(54, y, r)
        y -= 14
    c.setFont("Times-Italic", 8)
    c.drawString(54, 40, f"Language tag: {lang}. All patients are fictional.")
    c.save()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def write_scanned(path: Path, lines: list[str]) -> None:
    img = Image.new("RGB", (1275, 1650), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        font_b = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
        font_b = font
    d.text((80, 60), "HANDWRITTEN MOCK AE FORM (SYNTHETIC)", fill="#222", font=font_b)
    y = 160
    for line in lines:
        # slightly uneven "handwriting"
        d.text((90, y), line, fill="#1a1a1a", font=font)
        y += 48
    d.rectangle((80, 1400, 400, 1520), outline="#333", width=2)
    d.text((100, 1440), "[x] Photo of pack attached", fill="#333", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    pdf = fitz_image_pdf(buf.getvalue())
    path.write_bytes(pdf)


def fitz_image_pdf(png: bytes) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    img = pymupdf.open("png", png)
    rect = img[0].rect
    page = doc.new_page(width=rect.width, height=rect.height)
    page.insert_image(rect, stream=png)
    out = doc.tobytes()
    doc.close()
    img.close()
    return out


def main() -> None:
    # 5 digital CIOMS-like forms
    write_form(
        PDF / "digital_icsr_01.pdf",
        "CIOMS-like Safety Report (FICTIONAL)",
        [
            ("Patient age", "67"),
            ("Sex", "Female"),
            ("Weight", "72 kg"),
            ("History", "Hypertension (fictional)"),
            ("Reporter", "Dr. Priya Nair, physician, India"),
            ("Product", "Zentaril 10 mg tablet"),
            ("Dose / route", "10 mg oral daily"),
            ("Start / stop", "2025-01-04 / 2025-01-12"),
            ("Reaction", "Generalized urticaria starting day 3"),
            ("Outcome", "Recovered after drug stopped"),
            ("Serious", "No — not hospitalized"),
        ],
        extra="Narrative: Fictional patient developed hives three days after starting Zentaril. No real person.",
    )
    write_form(
        PDF / "digital_icsr_02.pdf",
        "Follow-up AE Form (FICTIONAL)",
        [
            ("Patient age", "41"),
            ("Sex", "Male"),
            ("Product", "Helioxa inhalation"),
            ("Reaction", "Wheezing and ER visit"),
            ("Outcome", "Not stated"),
            ("Lot", "HX-4411"),
        ],
    )
    write_form(
        PDF / "digital_icsr_03.pdf",
        "Incomplete reporter form (FICTIONAL)",
        [
            ("Patient", "Adult, age not written"),
            ("Product", "Not stated"),
            ("Reaction", "Severe headache after first dose of unnamed trial drug"),
            ("Reporter", "Pharmacist, country not stated"),
        ],
    )
    write_form(
        PDF / "digital_pqc_01.pdf",
        "Product Quality Complaint Form (FICTIONAL)",
        [
            ("Product", "Zentaril 10 mg"),
            ("Batch / Lot", "ZT-9B17"),
            ("Defect", "Broken tamper-evident seal and brown discoloration of tablets"),
            ("Photo", "Yes — blister photo attached in email"),
        ],
        extra="No adverse reaction described. Packaging integrity only.",
    )
    write_form(
        PDF / "digital_mi_01.pdf",
        "Medical Information Request Log (FICTIONAL)",
        [
            ("Product", "Zentaril"),
            ("Question 1", "Can it be crushed and mixed with applesauce?"),
            ("Question 2", "Renal dose adjustment if eGFR 40?"),
            ("AE present", "No"),
        ],
    )

    write_scanned(
        PDF / "scanned_handwritten_01.pdf",
        [
            "Name: (illegible fictional)",
            "Age: 54   Sex: M",
            "Drug: Helioxa  inhaler",
            "What happened: rash on arms day 2",
            "Hospital? yes overnight",
            "Reporter: nurse  UK",
        ],
    )
    write_scanned(
        PDF / "scanned_handwritten_02.pdf",
        [
            "Complaint not AE",
            "Lot QK-220 cracked vial",
            "liquid leaking in box",
            "photo taken of carton",
        ],
    )

    cases = [
        (
            "article_case_01.pdf",
            "Fictional case: Zentaril and acute liver injury",
            "A 58-year-old fictional woman developed jaundice six weeks after Zentaril 20 mg daily. Bilirubin peaked at 4.1 mg/dL. The drug was stopped and enzymes improved. Identifiable as a single patient case.",
            "Discussion of DILI mechanisms in general should be ignored. This paragraph is filler about hepatic metabolism.",
        ),
        (
            "article_case_02.pdf",
            "Two fictional patients with Helioxa cough",
            "Patient A, 12-year-old fictional child, cough after Helioxa. Patient B, 33-year-old fictional man, same product, hemoptysis one episode. Two distinct cases in one article.",
            "Literature review of cough reflex is not a case.",
        ),
        (
            "article_case_03.pdf",
            "Unrelated review article (should be low relevance)",
            "This paper reviews market size of inhalers and does not describe any identifiable patient. No age, no drug exposure narrative, no outcome.",
            "References discuss conferences and sales.",
        ),
        (
            "article_case_04.pdf",
            "Fictional pregnancy exposure without reaction",
            "A fictional 29-year-old took Zentaril in first trimester. No malformation reported at birth in this made-up vignette. Still an identifiable pregnancy case of interest for screening.",
            "General teratology discussion follows.",
        ),
        (
            "article_case_05.pdf",
            "Fictional anaphylaxis to Helioxa",
            "Emergency department of a fictional hospital: 22-year-old received Helioxa and developed anaphylaxis, epinephrine given, recovered.",
            "Ignore the methods section about device engineering.",
        ),
    ]
    for name, title, case, disc in cases:
        write_article(PDF / name, title, case, disc)

    write_article(
        PDF / "spanish_case_01.pdf",
        "Informe ficticio: urticaria por Zentaril",
        "Una mujer ficticia de 45 anos presento urticaria y edema palpebral dos dias despues de Zentaril 10 mg. No se hospitalizo. Reportero: medico en Espana.",
        "Disusion general sobre histamina. Datos sintetico solamente.",
        lang="es",
    )
    write_article(
        PDF / "french_case_01.pdf",
        "Cas fictif: nausees sous Helioxa",
        "Un homme fictif de 70 ans a presente des nausees persistantes une semaine apres Helioxa. Le traitement a ete arrete. Issue: retablissement. Reporter: pharmacien, France.",
        "Discussion generale sans patient.",
        lang="fr",
    )

    messages = [
        {
            "sender": "dr.nair@example.clinic",
            "subject": "Possible Zentaril rash — fictional patient",
            "body": "Hello PV team. I am Dr. Priya Nair (physician, India). A 67-year-old woman developed generalized urticaria after Zentaril 10 mg oral. Started 4 Jan, reaction day 3, recovered after stopping. Weight 72 kg, hypertension history. Fictional case only.",
            "pdfRelativePaths": ["pdfs/digital_icsr_01.pdf"],
        },
        {
            "sender": "er.night@example.hospital",
            "subject": "Helioxa wheeze, incomplete follow-up",
            "body": "41-year-old man, Helioxa inhalation, wheezing, ER visit. Outcome not known yet. Reporter is ER physician, country not stated.",
            "pdfRelativePaths": ["pdfs/digital_icsr_02.pdf"],
        },
        {
            "sender": "pharmacy@example.org",
            "subject": "Headache after first dose — drug name missing",
            "body": "Pharmacist reporting severe headache after first dose. Patient adult, age not written. Product name missing on the form.",
            "pdfRelativePaths": ["pdfs/digital_icsr_03.pdf"],
        },
        {
            "sender": "qc@example.wholesaler",
            "subject": "Broken seal / brown tablets lot ZT-9B17",
            "body": "Quality complaint only. Zentaril 10 mg lot ZT-9B17: broken tamper-evident seal and wrong color (brown) tablets. Photo of blister mentioned. No patient reaction.",
            "pdfRelativePaths": ["pdfs/digital_pqc_01.pdf"],
        },
        {
            "sender": "mi.mailbox@example.org",
            "subject": "Can Zentaril be crushed?",
            "body": "Two questions: Can Zentaril be crushed into applesauce? Any renal adjustment at eGFR 40? No adverse event, no product defect.",
            "pdfRelativePaths": ["pdfs/digital_mi_01.pdf"],
        },
        {
            "sender": "ward.nurse@example.nhs",
            "subject": "Handwritten AE form scan",
            "body": "Please find a photographed handwritten form. Fictional 54-year-old male, Helioxa, rash, overnight hospital stay. Reporter nurse, UK.",
            "pdfRelativePaths": ["pdfs/scanned_handwritten_01.pdf"],
        },
        {
            "sender": "warehouse@example.com",
            "subject": "Cracked vial photo form",
            "body": "Scanned complaint: lot QK-220 cracked vial leaking. Not an adverse reaction.",
            "pdfRelativePaths": ["pdfs/scanned_handwritten_02.pdf"],
        },
        {
            "sender": "lit.watch@example.org",
            "subject": "Article: fictional DILI case",
            "body": "Please screen attached made-up journal PDF for a patient case.",
            "pdfRelativePaths": ["pdfs/article_case_01.pdf"],
        },
        {
            "sender": "lit.watch@example.org",
            "subject": "Article with two fictional patients",
            "body": "Literature PDF may contain two cases.",
            "pdfRelativePaths": ["pdfs/article_case_02.pdf"],
        },
        {
            "sender": "lit.watch@example.org",
            "subject": "Review article no patients",
            "body": "Probably not a case.",
            "pdfRelativePaths": ["pdfs/article_case_03.pdf"],
        },
        {
            "sender": "lit.watch@example.org",
            "subject": "Pregnancy vignette",
            "body": "Fictional pregnancy exposure article attached.",
            "pdfRelativePaths": ["pdfs/article_case_04.pdf"],
        },
        {
            "sender": "lit.watch@example.org",
            "subject": "Anaphylaxis case report",
            "body": "Fictional anaphylaxis write-up.",
            "pdfRelativePaths": ["pdfs/article_case_05.pdf"],
        },
        {
            "sender": "madrid.clinic@example.es",
            "subject": "Informe de seguridad (ES)",
            "body": "Adjunto un PDF en espanol sobre urticaria ficticia por Zentaril.",
            "pdfRelativePaths": ["pdfs/spanish_case_01.pdf"],
        },
        {
            "sender": "paris.pharma@example.fr",
            "subject": "Cas indesirable (FR)",
            "body": "PDF francais: nausees fictives sous Helioxa.",
            "pdfRelativePaths": ["pdfs/french_case_01.pdf"],
        },
        {
            "sender": "pqc.only@example.com",
            "subject": "Counterfeit carton spotted",
            "body": "We received a carton that looks counterfeit (misspelled logo) for Helioxa. Lot CF-0001. No patient used it.",
            "pdfRelativePaths": [],
        },
        {
            "sender": "mi.only@example.com",
            "subject": "Interaction question only",
            "body": "Does Zentaril interact with fictional drug Relorix? How should a patient take it with food? No reaction occurred.",
            "pdfRelativePaths": [],
        },
        {
            "sender": "mi.only2@example.com",
            "subject": "Dosing in hepatic impairment?",
            "body": "What is the recommended Helioxa dose in Child-Pugh B? Pure medical information request.",
            "pdfRelativePaths": [],
        },
        {
            "sender": "news@example.pharmamarketing",
            "subject": "Join our spring webinar + 20% off conference tickets",
            "body": "Unsubscribe here. Marketing newsletter about a scientific conference. No patient, no product complaint.",
            "pdfRelativePaths": [],
        },
        {
            "sender": "gp@example.clinic",
            "subject": "Death — fictional ICSR",
            "body": "Fictional 81-year-old male died in hospital after Zentaril. Reporter GP, Canada. Started 1 Feb, reaction GI bleed 8 Feb. Outcome death. This is synthetic.",
            "pdfRelativePaths": [],
        },
        {
            "sender": "combo@example.org",
            "subject": "Rash after using leaking inhaler",
            "body": "Patient (fictional, 30F) used Helioxa from a leaking canister (damaged packaging, lot LK-77) and developed facial swelling. Both quality defect and adverse reaction.",
            "pdfRelativePaths": [],
        },
    ]

    manifest = {
        "disclaimer": "All content is synthetic. No real patient data.",
        "messages": messages,
    }
    (ROOT / "testdata" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(messages)} messages and PDFs under {PDF}")


if __name__ == "__main__":
    main()
