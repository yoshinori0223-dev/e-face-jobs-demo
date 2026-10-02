#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json,re,requests
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE="https://www.hellowork.mhlw.go.jp/kensaku/"
s=requests.Session()
s.headers.update({"User-Agent":"E-FACE-JOBS-research/0.1"})
s.get(BASE+"GECA110010.do?action=initDisp&screenId=GECA110010",timeout=30)

payload=[
 ("screenId","GECA110010"),
 ("action","searchBtn"),
 ("kjKbnRadioBtn","1"),
 ("ippanCKBox","1"),
 ("ippanCKBox","2"),
 ("todohukenHidden","401"),
 ("freeWordInput",""),
 ("freeWordRadioBtn","0"),
 ("searchInitDisp","0"),
]
r=s.post(BASE+"GECA110010.do",data=payload,timeout=30)
r.raise_for_status()
r.encoding=r.apparent_encoding or r.encoding
soup=BeautifulSoup(r.text,"html.parser")
text=" ".join(soup.stripped_strings)
links=[]
for a in soup.find_all("a",href=True):
    href=a["href"]
    if "dispDetailBtn" in href:
        links.append(urljoin(r.url,href))
for f in soup.find_all("form"):
    for btn in f.find_all(["button","input"]):
        onclick=btn.get("onclick") or ""
        if "dispDetailBtn" in onclick:
            m=re.search(r"kJNo[^0-9]*([0-9-]{8,})",onclick)
            if m:
                links.append(m.group(1))
# Also collect visible job-number patterns from first result page.
jobnos=[]
for m in re.finditer(r"\b\d{5}-\d{8}\b",text):
    if m.group(0) not in jobnos:
        jobnos.append(m.group(0))
out={
 "status":r.status_code,
 "url":r.url,
 "title":soup.title.get_text(" ",strip=True) if soup.title else None,
 "contains_fukuoka_city":"福岡市" in text,
 "contains_kitakyushu":"北九州市" in text,
 "job_numbers":jobnos[:30],
 "detail_links":links[:30],
 "text_excerpt":text[:12000],
}
Path("data").mkdir(parents=True,exist_ok=True)
Path("data/hellowork-search-post-test.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("jobnos",jobnos[:20])
print("detail_links",len(links))
print("contains_fukuoka_city",out["contains_fukuoka_city"])
