#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-FACE JOBS / Hello Work diff test

Compares a current discovery JSON with a previous snapshot JSON by job number.

Statuses:
- new: appears only in current
- active: appears in both
- ended_candidate: appears only in previous (not immediately deleted)
- changed: appears in both but selected fields differ

TEST ONLY. No public Pages update.
"""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path

COMPARE_FIELDS = [
    "title","company","location","employment_type","wage",
    "working_hours","holidays","deadline","description"
]

def load(path: str):
    p=Path(path)
    if not p.exists():
        return {"results":[]}
    return json.loads(p.read_text(encoding="utf-8"))

def key_of(row):
    return row.get("job_number") or row.get("_discovery",{}).get("job_number")

def canon(row):
    return {k:(row.get(k) or "") for k in COMPARE_FIELDS}

def digest(row):
    raw=json.dumps(canon(row),ensure_ascii=False,sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def eligible(rows):
    out=[]
    for r in rows:
        if r.get("status") in ("test_candidate","active","changed","new"):
            k=key_of(r)
            if k:
                out.append(r)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--current",required=True)
    ap.add_argument("--previous",required=True)
    ap.add_argument("--output",default="data/hellowork-diff-output.json")
    args=ap.parse_args()

    cur=eligible(load(args.current).get("results",[]))
    prev=eligible(load(args.previous).get("results",[]))

    cm={key_of(x):x for x in cur}
    pm={key_of(x):x for x in prev}

    new=[]
    active=[]
    changed=[]
    ended=[]

    for k,row in cm.items():
        if k not in pm:
            x=dict(row); x["diff_status"]="new"; new.append(x)
        elif digest(row)!=digest(pm[k]):
            x=dict(row); x["diff_status"]="changed"; x["previous_hash"]=digest(pm[k]); x["current_hash"]=digest(row); changed.append(x)
        else:
            x=dict(row); x["diff_status"]="active"; active.append(x)

    for k,row in pm.items():
        if k not in cm:
            x=dict(row)
            x["diff_status"]="ended_candidate"
            x["end_reason"]="missing_from_current_first_page_snapshot"
            ended.append(x)

    payload={
        "test_only":True,
        "current_count":len(cm),
        "previous_count":len(pm),
        "summary":{
            "new":len(new),
            "active":len(active),
            "changed":len(changed),
            "ended_candidate":len(ended),
        },
        "new":new,
        "active":active,
        "changed":changed,
        "ended_candidate":ended,
        "notes":[
            "ended_candidate is not an immediate deletion signal.",
            "Current discovery is first-page-only, so missing jobs require recheck before closure."
        ]
    }
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(payload["summary"],ensure_ascii=False))

if __name__=="__main__":
    main()
