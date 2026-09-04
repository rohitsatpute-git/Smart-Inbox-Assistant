#!/usr/bin/env python3
"""Call the Python AI service on testdata and dump JSON + timings."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "sample-outputs"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    manifest = json.loads((ROOT / "testdata" / "manifest.json").read_text(encoding="utf-8"))
    timings = []
    for i, item in enumerate(manifest["messages"], start=1):
        atts = []
        for j, rel in enumerate(item.get("pdfRelativePaths") or [], start=1):
            path = ROOT / "testdata" / rel
            atts.append({"id": j, "filename": path.name, "path": str(path), "mime": "application/pdf"})
        payload = {
            "message_id": i,
            "sender": item.get("sender"),
            "subject": item.get("subject"),
            "body": item.get("body"),
            "attachments": atts,
        }
        req = urllib.request.Request(
            "http://localhost:8000/v1/analyze",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            ms = int((time.perf_counter() - t0) * 1000)
            body["_wall_ms"] = ms
            (OUT / f"message_{i:02d}.json").write_text(json.dumps(body, indent=2), encoding="utf-8")
            timings.append({"id": i, "subject": item["subject"], "duration_ms": body.get("duration_ms", ms), "wall_ms": ms})
            print(i, ms, "ms", item["subject"])
        except Exception as e:
            timings.append({"id": i, "subject": item["subject"], "error": str(e)})
            print("FAIL", i, e)
    (OUT / "timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
