#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, requests
from bs4 import BeautifulSoup
from pathlib import Path

BASE="https://www.hellowork.mhlw.go.jp/kensaku/"
s=requests.Session()
s.headers.update({"User-Agent":"E-FACE-JOBS-research/0.1"})
s.get(BASE+"GECA110010.do?action=initDisp&screenId=GECA110010",timeout=30)

data={
 "screenId":"GECZTDFMDL",
 "action":"initDisp",
 "codeAssistType":"3",
 "codeAssistItemCode":"todohukenHidden",
 "codeAssistItemName":"todohukenNameLbl",
 "onModal":"true",
 "codeAssistModalTitle":"都道府県から選択",
 "codeAssistText":"都道府県、市区町村を選択してください。",
 "codeAssistSelectableOne":"false",
 "codeAssistSelectableTwo":"true",
 "codeAssistSelectableThree":"true",
 "codeAssistSelectableFour":"true",
 "codeAssistSelectLimitOne":"3",
 "codeAssistSelectLimitTwo":"3",
 "codeAssistSelectLimitThree":"5",
 "codeAssistSelectLimitFour":"5",
 "codeAssistLimitTotalTwo":"false",
 "codeAssistLimitTotalThree":"false",
 "codeAssistLimitTotalFour":"true",
 "codeAssistMapKey":"todoufukenMap",
 "codeAssistCode":"ID_todohukenHidden",
 "codeAssistCodeName":"ID_todohukenNameLbl",
 "codeAssistFunc":"TODOUFUKEN_FUNC",
 "codeAssistDelimitTwo":"false",
 "codeAssistDelimitThree":"true",
 "codeAssistDelimitFour":"false",
}
r=s.post(BASE+"ECZTDFMDL.do",data=data,timeout=30)
r.raise_for_status()
r.encoding=r.apparent_encoding or r.encoding
soup=BeautifulSoup(r.text,"html.parser")
rows=[]
for x in soup.find_all(["input","button","label","option"]):
    txt=" ".join(x.stripped_strings)
    attrs={k:x.get(k) for k in ["name","id","value","onclick","data-code","data-value"] if x.get(k) is not None}
    if "福岡" in txt or "福岡" in str(attrs) or "40" in str(attrs):
        rows.append({"tag":x.name,"text":txt,"attrs":attrs})
payload={"status":r.status_code,"rows":rows,"html_excerpt":r.text[:30000]}
Path("data").mkdir(parents=True, exist_ok=True)
Path("data/hellowork-location-modal-probe.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
print("matches",len(rows))
for row in rows[:100]:
    print(row)
