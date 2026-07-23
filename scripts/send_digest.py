#!/usr/bin/env python3
"""
Energy Pulse — digest builder + sender.

Builds a digest of the newest items per category from docs/data/articles.json,
saves it to docs/digests/<date>.md (so past digests stay browsable on the
site), and optionally delivers it:

  - Email: set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, DIGEST_TO as
    GitHub Actions secrets (any SMTP provider works — Gmail app password,
    SendGrid, etc).
  - Slack: set SLACK_WEBHOOK_URL as a secret (Slack incoming webhook).

Either, both, or neither can be configured — the script skips whatever
isn't set up rather than failing.
"""
import json
import os
import smtplib
import ssl
from collections import defaultdict
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "feeds.yaml"
DATA_PATH = ROOT / "docs" / "data" / "articles.json"
DIGEST_DIR = ROOT / "docs" / "digests"


def build_digest_markdown():
    config = yaml.safe_load(CONFIG_PATH.read_text())
    per_category = config.get("digest_items_per_category", 5)

    data = json.loads(DATA_PATH.read_text())
    articles = data["articles"]

    by_category = defaultdict(list)
    for a in articles:
        by_category[a["category"]].append(a)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Energy Pulse Digest — {today}", ""]
    lines.append(f"_{data['count']} tracked articles across {len(by_category)} categories. "
                  f"Generated {data['generated_at']}._")
    lines.append("")

    # Keep a stable, sensible category order
    order = ["ISO/RTO", "Regulatory", "Trade Press", "Data Centers & Load Growth",
             "DER & Grid Modernization"]
    categories = sorted(by_category.keys(), key=lambda c: order.index(c) if c in order else 99)

    for cat in categories:
        items = by_category[cat][:per_category]
        if not items:
            continue
        lines.append(f"## {cat}")
        lines.append("")
        for item in items:
            lines.append(f"- **[{item['title']}]({item['link']})** — _{item['source']}_")
        lines.append("")

    return "\n".join(lines), today


def send_email(subject, markdown_body):
    host = os.environ.get("SMTP_HOST")
    if not host:
        print("SMTP not configured — skipping email.")
        return
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    to_addr = os.environ["DIGEST_TO"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr
    msg.attach(MIMEText(markdown_body, "plain"))

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.sendmail(user, to_addr, msg.as_string())
    print(f"Email sent to {to_addr}")


def send_slack(markdown_body):
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print("Slack webhook not configured — skipping Slack post.")
        return
    # Slack doesn't render Markdown links the same as email; keep it simple.
    resp = requests.post(webhook, json={"text": markdown_body[:39000]})
    resp.raise_for_status()
    print("Posted digest to Slack.")


def main():
    markdown_body, today = build_digest_markdown()

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    (DIGEST_DIR / f"{today}.md").write_text(markdown_body)
    print(f"Digest saved to docs/digests/{today}.md")

    index_path = ROOT / "docs" / "data" / "digest_index.json"
    dates = sorted({p.stem for p in DIGEST_DIR.glob("*.md")}, reverse=True)
    index_path.write_text(json.dumps(dates, indent=2))

    send_email(f"Energy Pulse Digest — {today}", markdown_body)
    send_slack(markdown_body)


if __name__ == "__main__":
    main()
