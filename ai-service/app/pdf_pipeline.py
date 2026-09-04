from __future__ import annotations

import io
from dataclasses import dataclass, field

import pymupdf
import pdfplumber
from langdetect import DetectorFactory, detect
from PIL import Image

DetectorFactory.seed = 0


@dataclass
class PdfWork:
    attachment_id: int
    filename: str
    path: str
    flavor: str
    language: str
    page_texts: list[str]
    combined_text: str
    original_excerpt: str
    english_text: str
    tables: list[dict]
    page_images: list[tuple[int, bytes]]
    ocr_confidence: float | None = None
    extra_images: list[dict] = field(default_factory=list)


def _is_sparse(text: str, pages: int) -> bool:
    chars = len((text or "").strip())
    return chars < max(80, pages * 40)


def _looks_article(text: str, page_count: int) -> bool:
    t = text.lower()
    return page_count >= 2 and ("references" in t or "abstract" in t or "doi:" in t)


def extract_tables(path: str) -> list[dict]:
    tables: list[dict] = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                for tbl in page.extract_tables() or []:
                    if not tbl:
                        continue
                    headers = [str(c or "").strip() for c in tbl[0]]
                    rows = []
                    for row in tbl[1:]:
                        rows.append({headers[j] if j < len(headers) else f"col{j}": (row[j] if row and j < len(row) else None) for j in range(len(headers) or len(row or []))})
                    tables.append({"page_no": i, "table_json": {"headers": headers, "rows": rows}})
    except Exception:
        pass
    return tables


def render_pages(path: str, max_pages: int = 4) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    doc = pymupdf.open(path)
    try:
        for i, page in enumerate(doc, start=1):
            if i > max_pages:
                break
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
            out.append((i, pix.tobytes("png")))
    finally:
        doc.close()
    return out


def extract_embedded_images(path: str, max_images: int = 3) -> list[dict]:
    flags: list[dict] = []
    doc = pymupdf.open(path)
    try:
        count = 0
        for i, page in enumerate(doc, start=1):
            for img in page.get_images(full=True):
                if count >= max_images:
                    return flags
                xref = img[0]
                try:
                    pix = pymupdf.Pixmap(doc, xref)
                    if pix.n - pix.alpha >= 4:
                        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                    if pix.width < 80 or pix.height < 80:
                        continue
                    flags.append({"page_no": i, "png": pix.tobytes("png")})
                    count += 1
                except Exception:
                    continue
    finally:
        doc.close()
    return flags


def inspect_pdf(attachment_id: int, filename: str, path: str) -> PdfWork:
    doc = pymupdf.open(path)
    page_texts: list[str] = []
    try:
        for page in doc:
            page_texts.append(page.get_text("text") or "")
        page_count = doc.page_count
    finally:
        doc.close()
    combined = "\n".join(page_texts)
    flavor = "digital"
    ocr_conf = None
    page_images: list[tuple[int, bytes]] = []
    if _is_sparse(combined, page_count):
        flavor = "scanned"
        page_images = render_pages(path)
        ocr_conf = 0.45
    elif _looks_article(combined, page_count):
        flavor = "article"
        # keep layout-ish text; PyMuPDF already handles many multi-column files
    language = "unknown"
    try:
        sample = combined.strip()[:4000] or "en"
        language = detect(sample) if sample.strip() else "en"
    except Exception:
        language = "en"
    if language not in ("en", "unknown") and len(combined.strip()) > 40:
        flavor = "non_english" if flavor == "digital" else flavor
    excerpt = combined[:4000]
    tables = extract_tables(path)
    extra = extract_embedded_images(path)
    return PdfWork(
        attachment_id=attachment_id,
        filename=filename,
        path=path,
        flavor=flavor,
        language=language,
        page_texts=page_texts,
        combined_text=combined,
        original_excerpt=excerpt,
        english_text=combined,
        tables=tables,
        page_images=page_images,
        ocr_confidence=ocr_conf,
        extra_images=extra,
    )


def png_for_caption(png_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(png_bytes))
    im.thumbnail((1024, 1024))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()
