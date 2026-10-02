#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-FACE JOBS / Hello Work discovery test

Flow:
1) Search the official Hello Work site for the official "北九州市～福岡市" area group.
2) Parse only the first result page.
3) Keep only rows whose work location starts with 福岡県福岡市 and public scope is 1.
4) Fetch details only for those candidates, max 10, with delay.
5) Reuse the safe detail normalizer from hellowork_fetch_test.py.

TEST ONLY: output is an artifact JSON and is not published to GitHub Pages.
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from hellowork_fetch_test import extract_job

BASE="https://www.hellowork.mhlw.go.jp/kensaku/"
SEARCH_URL=BASE+"GECA110010.do"
INIT_URL=SEARCH_URL+"?action=initDisp&screenId=GECA110010"
USER_AGENT="E-FACE-JOBS-research/0.2 (small-scale public-job verification; e-face group)"

def clean(s:str)->str:
    return re.sub(r"\s+"," ",s or "").strip()

def result_blocks(soup:BeautifulSoup):
    # Result cards contain both a detail link and a job number.
    for a in soup.find_all("a", href=True):
        if "action=dispDetailBtn" not in a["href"]:
            continue
        node=a
        for _ in range(8):
            if not node.parent:
                break
            node=node.parent
            txt=clean(node.get_text(" ",strip=True))
            if re.search(r"求人番号\s*\d{5}-\d{8}",txt) and "公開範囲" in txt:
                yield node,a
                break

def discover(session:requests.Session, limit:int):
    session.get(INIT_URL,timeout=30).raise_for_status()
    payload=[
        ("screenId","GECA110010"),
        ("action","searchBtn"),
        ("kjKbnRadioBtn","1"),
        ("ippanCKBox","1"),
        ("ippanCKBox","2"),
        # Official area-group code shown by the Hello Work selector:
        # 401 = 北九州市～福岡市
        ("todohukenHidden","401"),
        ("freeWordInput",""),
        ("freeWordRadioBtn","0"),
        ("searchInitDisp","0"),
    ]
    r=session.post(SEARCH_URL,data=payload,timeout=30)
    r.raise_for_status()
    r.encoding=r.apparent_encoding or r.encoding
    soup=BeautifulSoup(r.text,"html.parser")

    found=[]
    seen=set()
    for block,a in result_blocks(soup):
        txt=clean(block.get_text(" ",strip=True))
        m=re.search(r"求人番号\s*(\d{5}-\d{8})",txt)
        if not m:
            continue
        job_no=m.group(1)
        if job_no in seen:
            continue

        # Search-result prefilter: exact city prefix + public scope 1.
        loc_m=re.search(r"就業場所\s*(福岡県福岡市[^\s]*)",txt)
        public_ok=bool(re.search(r"公開範囲\s*[１1][\.．、\s]",txt))
        if not loc_m or not public_ok:
            continue

        href=urljoin(r.url,a["href"])
        found.append({
            "job_number":job_no,
            "search_location":loc_m.group(1),
            "public_scope_search":"1",
            "detail_url":href,
        })
        seen.add(job_no)
        if len(found)>=limit:
            break
    return found

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max",type=int,default=5)
    ap.add_argument("--delay",type=float,default=4.0)
    ap.add_argument("--output",default="data/hellowork-discovery-test-output.json")
    ap.add_argument("--previous",default=None,
                    help="Optional previous discovery snapshot. Existing job numbers are reused without detail fetch.")
    args=ap.parse_args()
    limit=max(1,min(args.max,10))
    delay=max(args.delay,3.0)

    session=requests.Session()
    session.headers.update({"User-Agent":USER_AGENT,"Accept-Language":"ja,en;q=0.5"})

    previous_map={}
    if args.previous and Path(args.previous).exists():
        try:
            prev_payload=json.loads(Path(args.previous).read_text(encoding="utf-8"))
            for row in prev_payload.get("results",[]):
                job_no=row.get("job_number") or row.get("_discovery",{}).get("job_number")
                if job_no and row.get("status") in ("test_candidate","active","new","changed"):
                    previous_map[job_no]=row
        except Exception:
            previous_map={}

    candidates=discover(session,limit)
    results=[]
    detail_fetches=0
    reused_existing=0

    new_candidates=[c for c in candidates if c["job_number"] not in previous_map]

    for c in candidates:
        job_no=c["job_number"]
        if job_no in previous_map:
            item=dict(previous_map[job_no])
            item["_discovery"]={
                "job_number":job_no,
                "search_location":c["search_location"],
                "public_scope_search":c["public_scope_search"],
                "reused_previous_detail":True,
            }
            item["last_seen_in_search"]=True
            results.append(item)
            reused_existing+=1
            continue

        try:
            item=extract_job(c["detail_url"],session)
            detail_fetches+=1
            item["_discovery"]={
                "job_number":job_no,
                "search_location":c["search_location"],
                "public_scope_search":c["public_scope_search"],
                "reused_previous_detail":False,
            }
            item["last_seen_in_search"]=True
            if item.get("status")=="test_candidate" and "福岡県福岡市" not in (item.get("location") or ""):
                item["status"]="excluded_location_mismatch"
            results.append(item)
        except Exception as e:
            results.append({
                "source_url":c["detail_url"],
                "job_number":job_no,
                "status":"fetch_error",
                "error":type(e).__name__,
                "message":str(e)[:300],
            })

        # Delay only between actual detail requests, not reused records.
        if detail_fetches < len(new_candidates):
            time.sleep(delay)

    payload={
        "test_only":True,
        "search_area_group":"401 / 北九州市～福岡市",
        "city_filter":"福岡県福岡市",
        "first_page_only":True,
        "max_detail_fetches":limit,
        "discovered":len(candidates),
        "detail_fetches":detail_fetches,
        "reused_existing":reused_existing,
        "results":results,
    }
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print("discovered",len(candidates),"detail_fetches",detail_fetches,"reused_existing",reused_existing)
    for x in results:
        print(x.get("job_number"),x.get("status"),x.get("company"),x.get("location"))

if __name__=="__main__":
    main()
