#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-FACE JOBS / Hello Work closure recheck test

Rechecks ended_candidate jobs by their original detail URL.

Outcome:
- closed: page clearly indicates unavailable / expired / deleted
- still_active: public detail still resolves and parser accepts it
- review_required: ambiguous response, parsing issue, or no clear status

TEST ONLY. No public Pages update.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

from hellowork_fetch_test import extract_job

USER_AGENT="E-FACE-JOBS-research/0.3 (closure verification; e-face group)"

CLOSED_MARKERS=(
    "この求人情報は現在公開されていません",
    "該当する求人情報がありません",
    "求人情報が見つかりません",
    "紹介期限日を過ぎています",
    "この求人は掲載を終了しています",
)

def clean(s:str)->str:
    return re.sub(r"\s+"," ",s or "").strip()

def check_url(url:str, session:requests.Session)->dict:
    r=session.get(url,timeout=30)
    status_code=r.status_code

    if status_code in (404,410):
        return {"closure_status":"closed","reason":f"http_{status_code}","source_url":url}

    if status_code>=500:
        return {"closure_status":"review_required","reason":f"http_{status_code}","source_url":url}

    r.raise_for_status()
    r.encoding=r.apparent_encoding or r.encoding
    soup=BeautifulSoup(r.text,"html.parser")
    txt=clean(soup.get_text(" ",strip=True))

    for marker in CLOSED_MARKERS:
        if marker in txt:
            return {"closure_status":"closed","reason":"closed_marker","marker":marker,"source_url":url}

    try:
        item=extract_job(url,session)
    except Exception as e:
        return {
            "closure_status":"review_required",
            "reason":"detail_parse_error",
            "error":type(e).__name__,
            "message":str(e)[:300],
            "source_url":url,
        }

    if item.get("status")=="test_candidate":
        return {
            "closure_status":"still_active",
            "reason":"public_detail_still_available",
            "source_url":url,
            "job_number":item.get("job_number"),
            "company":item.get("company"),
            "title":item.get("title"),
        }

    if item.get("status")=="excluded_non_public":
        return {
            "closure_status":"review_required",
            "reason":"now_non_public",
            "source_url":url,
            "job_number":item.get("job_number"),
        }

    return {
        "closure_status":"review_required",
        "reason":"ambiguous_detail_status",
        "source_url":url,
        "parser_status":item.get("status"),
        "job_number":item.get("job_number"),
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--diff",required=True)
    ap.add_argument("--output",default="data/hellowork-closure-recheck.json")
    ap.add_argument("--delay",type=float,default=4.0)
    ap.add_argument("--max",type=int,default=10)
    args=ap.parse_args()

    payload=json.loads(Path(args.diff).read_text(encoding="utf-8"))
    rows=payload.get("ended_candidate",[])[:max(1,min(args.max,10))]

    session=requests.Session()
    session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ja,en;q=0.5"})

    checked=[]
    for i,row in enumerate(rows):
        url=row.get("source_url")
        if not url:
            checked.append({
                "job_number":row.get("job_number"),
                "closure_status":"review_required",
                "reason":"source_url_missing",
            })
        else:
            result=check_url(url,session)
            result["job_number"]=result.get("job_number") or row.get("job_number")
            checked.append(result)
        if i<len(rows)-1:
            time.sleep(max(args.delay,3.0))

    summary={
        "closed":sum(x["closure_status"]=="closed" for x in checked),
        "still_active":sum(x["closure_status"]=="still_active" for x in checked),
        "review_required":sum(x["closure_status"]=="review_required" for x in checked),
    }

    out={
        "test_only":True,
        "checked_count":len(checked),
        "summary":summary,
        "results":checked,
        "rule":"Missing from search is not enough for closure; close only on explicit recheck evidence."
    }
    p=Path(args.output)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
