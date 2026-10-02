#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import json
import requests
from bs4 import BeautifulSoup

URL="https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do?action=initDisp&screenId=GECA110010"
r=requests.get(URL, timeout=30, headers={"User-Agent":"E-FACE-JOBS-research/0.1"})
r.raise_for_status()
r.encoding=r.apparent_encoding or r.encoding
soup=BeautifulSoup(r.text,"html.parser")

forms=[]
for i,f in enumerate(soup.find_all("form")):
    fields=[]
    for x in f.find_all(["input","select","textarea","button"]):
        item={
            "tag":x.name,
            "name":x.get("name"),
            "type":x.get("type"),
            "value":x.get("value"),
            "id":x.get("id"),
        }
        if x.name=="select":
            item["options"]=[
                {"value":o.get("value"),"text":" ".join(o.stripped_strings)}
                for o in x.find_all("option")[:30]
            ]
        fields.append(item)
    forms.append({
        "index":i,
        "method":f.get("method"),
        "action":f.get("action"),
        "fields":fields,
    })

snippets={}
raw=r.text
for key in ["todohukenHidden","siku","市区町村","codeAssist"]:
    hits=[]
    pos=0
    while True:
        i=raw.find(key,pos)
        if i<0 or len(hits)>=20:
            break
        hits.append(raw[max(0,i-500):min(len(raw),i+1000)])
        pos=i+len(key)
    snippets[key]=hits

scripts=[x.get("src") for x in soup.find_all("script") if x.get("src")]
out={"url":URL,"forms":forms,"scripts":scripts,"snippets":snippets}
Path("data/hellowork-search-form-probe.json").parent.mkdir(parents=True,exist_ok=True)
Path("data/hellowork-search-form-probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("forms",len(forms))
for f in forms:
    print("FORM",f["index"],f["method"],f["action"])
    for x in f["fields"]:
        if x.get("name"):
            print(x["tag"],x.get("name"),x.get("value"),x.get("id"))
