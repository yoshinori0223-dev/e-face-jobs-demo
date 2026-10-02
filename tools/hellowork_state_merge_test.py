#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E-FACE JOBS / Hello Work state merge test

Combines:
- current discovery results
- previous snapshot
- closure recheck results

Rules:
- new/current rows remain active candidates
- still_active ended candidates are restored
- closed ended candidates become closed
- review_required remain review_required and are not silently deleted

TEST ONLY. No public Pages update.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def job_no(row):
    return row.get("job_number") or row.get("_discovery",{}).get("job_number")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--current",required=True)
    ap.add_argument("--previous",required=True)
    ap.add_argument("--closure",required=True)
    ap.add_argument("--output",default="data/hellowork-merged-snapshot.json")
    args=ap.parse_args()

    current=load(args.current)
    previous=load(args.previous)
    closure=load(args.closure)

    cur_map={job_no(x):dict(x) for x in current.get("results",[]) if job_no(x)}
    prev_map={job_no(x):dict(x) for x in previous.get("results",[]) if job_no(x)}
    close_map={x.get("job_number"):x for x in closure.get("results",[]) if x.get("job_number")}

    merged={}
    # Current search presence wins.
    for k,row in cur_map.items():
        row["lifecycle_status"]="active"
        merged[k]=row

    # Previous rows absent from current require closure evidence.
    for k,row in prev_map.items():
        if k in merged:
            continue
        check=close_map.get(k)
        if not check:
            row["lifecycle_status"]="review_required"
            row["lifecycle_reason"]="missing_closure_recheck"
        elif check.get("closure_status")=="closed":
            row["lifecycle_status"]="closed"
            row["lifecycle_reason"]=check.get("reason")
        elif check.get("closure_status")=="still_active":
            row["lifecycle_status"]="active"
            row["lifecycle_reason"]="closure_recheck_still_active"
        else:
            row["lifecycle_status"]="review_required"
            row["lifecycle_reason"]=check.get("reason","closure_recheck_ambiguous")
        merged[k]=row

    rows=list(merged.values())
    summary={
        "active":sum(x.get("lifecycle_status")=="active" for x in rows),
        "closed":sum(x.get("lifecycle_status")=="closed" for x in rows),
        "review_required":sum(x.get("lifecycle_status")=="review_required" for x in rows),
        "total":len(rows),
    }
    payload={"test_only":True,"summary":summary,"results":rows}
    p=Path(args.output); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))

if __name__=="__main__":
    main()
