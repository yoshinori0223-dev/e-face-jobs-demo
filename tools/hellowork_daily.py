#!/usr/bin/env python3
"""Bounded daily verification with a durable oldest-attempt-first queue.

Search presence never substitutes for fresh detail verification. Only jobs verified
in this execution may enter the public display. Unprocessed records stay pending.
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from hellowork_discovery_test import discover, USER_AGENT
from hellowork_closure_recheck_test import check_url
from hellowork_publish_candidate import clean, js_job


def now():
    return datetime.now(timezone.utc).isoformat()


def priority(rows, discovered, published):
    # Bound high-priority traffic; the remaining budget always advances the queue.
    front=list(dict.fromkeys(published[:3]+discovered[:5]))
    eligible={k:r for k,r in rows.items() if r.get('lifecycle_status')!='closed' or k in discovered}
    rest=sorted((k for k in eligible if k not in front),
                key=lambda k:(eligible[k].get('last_attempt_at',''),k))
    return [k for k in front if k in eligible]+rest


def verify(rows, order, session, max_checks=20, budget=240, delay=4,
           checker=check_url, clock=time.monotonic, sleeper=time.sleep):
    started=clock(); checked=[]; fresh=[]
    for key in order:
        if len(checked)>=max_checks or clock()-started>=budget:
            break
        if checked:
            sleeper(delay)
        if clock()-started>=budget:
            break
        row=rows[key]
        try:
            result=checker(row.get('source_url',''),session) if row.get('source_url') else {
                'closure_status':'review_required','reason':'source_url_missing'}
        except requests.RequestException as exc:
            result={'closure_status':'review_required','reason':'request_error',
                    'error':type(exc).__name__}
        stamp=now(); row['last_attempt_at']=stamp
        row['lifecycle_reason']=result.get('reason')
        status=result.get('closure_status')
        if status=='still_active' and result.get('job_number')==key:
            row.update(result.get('detail',{}))
            row['lifecycle_status']='active'
            row['last_verified_at']=stamp
            if row.get('public_scope')!='excluded' and row.get('source_url'):
                fresh.append(dict(row))
        elif status=='closed':
            row['lifecycle_status']='closed'
            row['closed_at']=stamp
        else:
            row['lifecycle_status']='review_required'
            if status=='still_active':
                row['lifecycle_reason']='job_number_mismatch'
        checked.append(key)
    # Deferred is scheduling state, not evidence of closure or active status.
    pending=[k for k in order if k not in checked]
    for key in pending:
        rows[key]['lifecycle_status']='pending'
        rows[key]['lifecycle_reason']='deferred_by_budget'
    return fresh, {'checked':len(checked),'pending':len(pending),
                   'review_required':sum(rows[k]['lifecycle_status']=='review_required' for k in checked),
                   'closed':sum(rows[k]['lifecycle_status']=='closed' for k in checked)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--state',default='data/hellowork-auto-state.json')
    ap.add_argument('--output',default='hellowork-live-test.js')
    ap.add_argument('--audit',default='data/hellowork-daily-audit.json')
    args=ap.parse_args()
    state_path=Path(args.state)
    old=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {'results':[]}
    rows={r['job_number']:dict(r) for r in old['results'] if r.get('job_number')}
    session=requests.Session()
    session.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ja,en;q=0.5'})
    candidates=discover(session,5)  # Two search requests, no detail fetches here.
    keys=[]
    for c in candidates:
        key=c['job_number']; keys.append(key)
        rows.setdefault(key,{'job_number':key,'status':'test_candidate','lifecycle_status':'pending'})
        rows[key]['source_url']=c['detail_url']
    published=old.get('published_job_numbers',[])
    if not published and Path(args.output).exists():
        published=re.findall(r'"hwNo":\s*"([^"]+)"',Path(args.output).read_text(encoding='utf-8'))
    fresh,summary=verify(rows,priority(rows,keys,published),session)
    fresh.sort(key=lambda r:(clean(r.get('received_date')),r['job_number']),reverse=True)
    selected=fresh[:3]
    # Publication evidence must be from this execution, never a carried active flag.
    assert all(r.get('last_verified_at') for r in selected)
    summary.update(total=len(rows),published=len(selected),discovered=len(keys))
    state={'schema_version':2,'generated_at':now(),'summary':summary,
           'published_job_numbers':[r['job_number'] for r in selected],
           'results':list(rows.values())}
    audit={'limits':{'detail_requests':20,'verification_seconds':240,'delay_seconds':4},
           'summary':summary,'published_job_numbers':state['published_job_numbers'],
           'review':[{'job_number':r['job_number'],'reason':r.get('lifecycle_reason')}
                     for r in rows.values() if r.get('lifecycle_status')=='review_required']}
    js='const HELLOWORK_LIVE_TEST_JOBS='+json.dumps([js_job(r) for r in selected],ensure_ascii=False,indent=2)+';\n'
    # Prepare both outputs before replacing either. Git commits them together.
    for path,payload in [(state_path,json.dumps(state,ensure_ascii=False,indent=2)),
                         (Path(args.output),js),(Path(args.audit),json.dumps(audit,ensure_ascii=False,indent=2))]:
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(payload,encoding='utf-8');temp.replace(path)
    print(json.dumps(audit,ensure_ascii=False))
    if audit['review']:
        print('::warning::Some jobs require review; excluded from publication, queue saved.')


if __name__=='__main__':
    main()
