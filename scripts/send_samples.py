#!/usr/bin/env python3
"""SMTP-send synthetic samples into the Gmail test inbox."""
from __future__ import annotations

import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "testdata" / "manifest.json"


def main() -> None:
    user = os.environ.get("GMAIL_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    if not user or not password:
        raise SystemExit("Set GMAIL_USER and GMAIL_APP_PASSWORD")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        for item in data["messages"]:
            msg = EmailMessage()
            msg["From"] = item.get("sender") or user
            msg["To"] = user
            msg["Subject"] = item["subject"]
            msg.set_content(item.get("body") or "")
            for rel in item.get("pdfRelativePaths") or []:
                path = ROOT / "testdata" / rel
                if path.exists():
                    msg.add_attachment(
                        path.read_bytes(),
                        maintype="application",
                        subtype="pdf",
                        filename=path.name,
                    )
            smtp.send_message(msg)
            print("sent", item["subject"])
    print("done")


if __name__ == "__main__":
    main()
