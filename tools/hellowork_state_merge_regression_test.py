#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    prev={"results":[
      {"job_number":"A","status":"test_candidate","title":"A"},
      {"job_number":"B","status":"test_candidate","title":"B"},
      {"job_number":"C","status":"test_candidate","title":"C"},
      {"job_number":"D","status":"test_candidate","title":"D"},
    ]}
    cur={"results":[
      {"job_number":"A","status":"test_candidate","title":"A"},
      {"job_number":"E","status":"test_candidate","title":"E"},
    ]}
    closure={"results":[
      {"job_number":"B","closure_status":"closed","reason":"closed_marker"},
      {"job_number":"C","closure_status":"still_active","reason":"public_detail_still_available"},
      {"job_number":"D","closure_status":"review_required","reason":"ambiguous_detail_status"},
    ]}
    for name,obj in [("prev",prev),("cur",cur),("closure",closure)]:
        (td/f"{name}.json").write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")
    out=td/"out.json"
    subprocess.check_call([
      "python","tools/hellowork_state_merge_test.py",
      "--current",str(td/"cur.json"),
      "--previous",str(td/"prev.json"),
      "--closure",str(td/"closure.json"),
      "--output",str(out)
    ])
    got=json.loads(out.read_text(encoding="utf-8"))["summary"]
    assert got=={"active":3,"closed":1,"review_required":1,"total":5}, got
    print("PASS",got)
