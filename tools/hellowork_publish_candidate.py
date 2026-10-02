#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a public-display candidate from the merged Hello Work lifecycle snapshot.

DRY-RUN helper: by default writes a candidate JS file and does not replace
hellowork-live-test.js.
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

CATEGORY_RULES = [
    ("コール", "コールセンター"),
    ("営業", "営業・セールス"),
    ("販売", "販売・接客"),
    ("接客", "販売・接客"),
    ("倉庫", "軽作業・物流"),
    ("配送", "軽作業・物流"),
    ("運送", "軽作業・物流"),
    ("製造", "製造・工場"),
    ("工場", "製造・工場"),
    ("医療", "医療・介護"),
    ("介護", "医療・介護"),
    ("看護", "医療・介護"),
    ("受付", "事務・経理"),
    ("経理", "事務・経理"),
    ("事務", "事務・経理"),
]

def clean(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()

def category_of(row):
    text = " ".join([clean(row.get("title")), clean(row.get("job_category")), clean(row.get("description"))])
    for needle, cat in CATEGORY_RULES:
        if needle in text:
            return cat
    return "オフィスワーク"

def employment_of(row):
    raw = clean(row.get("employment_type"))
    if "正社員" in raw:
        return "正社員"
    if "パート" in raw:
        return "アルバイト・パート"
    if "契約" in raw:
        return "契約社員"
    if "派遣" in raw:
        return "派遣社員"
    return raw or "その他"

def pay_of(row):
    wage = clean(row.get("wage"))
    return wage or "給与はハローワークで確認"

def js_job(row):
    no = clean(row.get("job_number"))
    compact = re.sub(r"[^0-9A-Za-z]", "", no)
    return {
        "id": f"hw-{compact}",
        "source": "hellowork-live-test",
        "title": clean(row.get("title")) or "ハローワーク公開求人",
        "company": clean(row.get("company")) or "事業所名はハローワークで確認",
        "area": clean(row.get("location")) or "福岡市",
        "cat": category_of(row),
        "type": employment_of(row),
        "pay": pay_of(row),
        "tags": ["ハローワーク公開求人", employment_of(row)],
        "hwNo": no,
        "fetched": datetime.now(timezone.utc).strftime("%Y/%m/%d"),
        "received": clean(row.get("received_date")),
        "deadline": clean(row.get("deadline")),
        "sourceLabel": "ハローワーク公開求人・テスト表示",
        "description": clean(row.get("description")),
        "workingHours": clean(row.get("working_hours")),
        "holidays": clean(row.get("holidays")),
        "sourceUrl": clean(row.get("source_url")),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--output", default="data/hellowork-live-candidate.js")
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args()

    payload = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    rows = [
        r for r in payload.get("results", [])
        if r.get("lifecycle_status") == "active"
        and r.get("public_scope") != "excluded"
        and r.get("job_number")
        and r.get("source_url")
    ]

    # Stable display order: newest receipt date first, then job number.
    rows.sort(key=lambda r: (clean(r.get("received_date")), clean(r.get("job_number"))), reverse=True)
    jobs = [js_job(r) for r in rows[:max(1, min(args.max, 10))]]

    out = "const HELLOWORK_LIVE_TEST_JOBS=" + json.dumps(jobs, ensure_ascii=False, indent=2) + ";\n"
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding="utf-8")
    print(json.dumps({"candidate_jobs": len(jobs), "output": str(p)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
