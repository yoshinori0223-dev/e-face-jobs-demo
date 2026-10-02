#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synthetic regression test for Hello Work diff logic.
"""
import json, subprocess, tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    prev={
      "results":[
        {"job_number":"40010-00000001","status":"test_candidate","title":"A","company":"X","location":"福岡県福岡市","wage":"月給 200,000円"},
        {"job_number":"40010-00000002","status":"test_candidate","title":"B","company":"Y","location":"福岡県福岡市","wage":"月給 210,000円"},
        {"job_number":"40010-00000003","status":"test_candidate","title":"C","company":"Z","location":"福岡県福岡市","wage":"月給 220,000円"}
      ]
    }
    cur={
      "results":[
        {"job_number":"40010-00000001","status":"test_candidate","title":"A","company":"X","location":"福岡県福岡市","wage":"月給 200,000円"},
        {"job_number":"40010-00000002","status":"test_candidate","title":"B","company":"Y","location":"福岡県福岡市","wage":"月給 230,000円"},
        {"job_number":"40010-00000004","status":"test_candidate","title":"D","company":"W","location":"福岡県福岡市","wage":"月給 240,000円"}
      ]
    }
    (td/"prev.json").write_text(json.dumps(prev,ensure_ascii=False),encoding="utf-8")
    (td/"cur.json").write_text(json.dumps(cur,ensure_ascii=False),encoding="utf-8")
    out=td/"out.json"
    subprocess.check_call([
      "python","tools/hellowork_diff_test.py",
      "--current",str(td/"cur.json"),
      "--previous",str(td/"prev.json"),
      "--output",str(out)
    ])
    got=json.loads(out.read_text(encoding="utf-8"))["summary"]
    assert got=={"new":1,"active":1,"changed":1,"ended_candidate":1}, got
    print("PASS",got)
