#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-FACE JOBS / Hello Work small-scale acquisition test

Safety design:
- Test only. Does not update public Pages data.
- Reads only explicitly listed public-detail URLs.
- Maximum 10 URLs per run.
- Sleeps between requests.
- Rejects pages indicating non-public employer information.
- Does not download images or map data.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_DELAY = 4.0
MAX_JOBS = 10
USER_AGENT = (
    "E-FACE-JOBS-research/0.1 "
    "(small-scale public-job verification; e-face group)"
)

NON_PUBLIC_MARKERS = (
    "事業所の意向により公開していません",
    "求職者マイページにログイン",
    "ハローワークの求職者に限定",
)

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def text_of(soup: BeautifulSoup) -> str:
    return clean(soup.get_text(" ", strip=True))

def normalize_title(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    value = re.sub(r"^職種解説\s*", "", value)
    return clean(value)

def extract_wage(text: str, current: Optional[str]) -> Optional[str]:
    # Prefer an actual yen range over a bare wage type such as "月給".
    ranges = re.findall(r"(\d{1,3}(?:,\d{3})+\s*円)\s*[〜～~-]\s*(\d{1,3}(?:,\d{3})+\s*円)", text)
    if ranges:
        lo, hi = ranges[0]
        wage_type = current if current in ("月給", "日給", "時給", "年俸制") else ""
        return clean(f"{wage_type} {lo}〜{hi}")
    return current

def table_value(soup: BeautifulSoup, labels: list[str]) -> Optional[str]:
    for cell in soup.find_all(["th", "td", "dt"]):
        label = clean(cell.get_text(" ", strip=True))
        if any(label == x or label.startswith(x) for x in labels):
            if cell.name == "dt":
                dd = cell.find_next_sibling("dd")
                if dd:
                    return clean(dd.get_text(" ", strip=True))
            row = cell.find_parent("tr")
            if row:
                cells = row.find_all(["th", "td"])
                try:
                    idx = cells.index(cell)
                except ValueError:
                    idx = -1
                if 0 <= idx < len(cells) - 1:
                    value = clean(cells[idx + 1].get_text(" ", strip=True))
                    if value:
                        return value
    return None

def regex_value(text: str, label: str, next_labels: list[str]) -> Optional[str]:
    stops = "|".join(re.escape(x) for x in next_labels)
    m = re.search(re.escape(label) + r"\s*(.+?)(?=\s*(?:" + stops + r")\s*|$)", text)
    return clean(m.group(1)) if m else None

def extract_job(url: str, session: requests.Session) -> dict:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or r.encoding
    soup = BeautifulSoup(r.text, "html.parser")
    page_text = text_of(soup)

    if any(marker in page_text for marker in NON_PUBLIC_MARKERS):
        return {
            "source_url": url,
            "status": "excluded_non_public",
            "reason": "non_public_marker",
        }

    job_no = table_value(soup, ["求人番号"])
    company = table_value(soup, ["事業所名"])
    title = table_value(soup, ["職種"])
    location = table_value(soup, ["就業場所"])
    employment = table_value(soup, ["雇用形態"])
    description = table_value(soup, ["仕事内容"])
    received = table_value(soup, ["受付年月日"])
    deadline = table_value(soup, ["紹介期限日"])
    office = table_value(soup, ["受理安定所"])
    category = table_value(soup, ["求人区分"])
    hours = table_value(soup, ["就業時間"])
    holidays = table_value(soup, ["休日等", "休日"])
    wage = table_value(soup, ["賃金・手当", "賃金"])

    # Fallbacks for the site's nested markup.
    next_labels = [
        "受付年月日", "紹介期限日", "受理安定所", "求人区分", "仕事内容",
        "雇用形態", "就業場所", "賃金・手当", "労働時間", "休日等",
        "求人事業所", "会社の情報", "選考等"
    ]
    job_no = job_no or regex_value(page_text, "求人番号", next_labels)
    title = title or regex_value(page_text, "職種", ["仕事内容", "雇用形態"])
    title = normalize_title(title)
    description = description or regex_value(page_text, "仕事内容", ["雇用形態", "雇用期間"])
    location = location or regex_value(page_text, "就業場所", ["マイカー通勤", "転勤"])
    employment = employment or regex_value(page_text, "雇用形態", ["雇用期間", "就業場所"])
    received = received or regex_value(page_text, "受付年月日", ["紹介期限日"])
    deadline = deadline or regex_value(page_text, "紹介期限日", ["受理安定所"])
    wage = extract_wage(page_text, wage)

    # Employer name is required for this test. Missing/hidden names are excluded.
    if not company:
        return {
            "source_url": url,
            "job_number": job_no,
            "status": "review_required",
            "reason": "company_name_missing_or_unparseable",
        }

    return {
        "id": f"hw-{re.sub(r'[^0-9A-Za-z]', '', job_no or '')}" if job_no else None,
        "source_type": "hellowork",
        "source_name": "ハローワークインターネットサービス",
        "source_url": url,
        "job_number": job_no,
        "title": title,
        "company": company,
        "location": location,
        "employment_type": employment,
        "description": description,
        "wage": wage,
        "working_hours": hours,
        "holidays": holidays,
        "received_date": received,
        "deadline": deadline,
        "accepting_office": office,
        "job_category": category,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "test_candidate",
        "public_scope": "public_candidate",
        "images_imported": False,
        "map_imported": False,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="tools/hellowork_test_seeds.txt")
    ap.add_argument("--output", default="data/hellowork-test-output.json")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    ap.add_argument("--max", type=int, default=5)
    args = ap.parse_args()

    limit = max(1, min(args.max, MAX_JOBS))
    urls = [
        line.strip() for line in Path(args.seeds).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ][:limit]

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "ja,en;q=0.5",
    })

    results = []
    for i, url in enumerate(urls):
        try:
            results.append(extract_job(url, session))
        except Exception as e:
            results.append({
                "source_url": url,
                "status": "fetch_error",
                "error": type(e).__name__,
                "message": str(e)[:300],
            })
        if i < len(urls) - 1:
            time.sleep(max(args.delay, 3.0))

    payload = {
        "test_only": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested": len(urls),
        "results": results,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(results)} result(s) to {out}")
    for row in results:
        print(row.get("job_number"), row.get("status"), row.get("company"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
