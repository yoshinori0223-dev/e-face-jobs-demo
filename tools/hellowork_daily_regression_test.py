#!/usr/bin/env python3
"""Offline production scheduler and publication-evidence tests."""
import copy
import requests
from hellowork_daily import priority, verify


def row(k):
    return {'job_number':k,'source_url':'https://example.invalid/'+k,'lifecycle_status':'active'}

def good(url, session):
    k=url.rsplit('/',1)[-1]
    return {'job_number':k,'closure_status':'still_active','detail':{'title':'fresh '+k}}

# Queue survives reloads; even a large history advances behind priority jobs.
rows={str(i):row(str(i)) for i in range(1000)}
for run in range(84):
    fresh, summary=verify(rows,priority(rows,[str(i) for i in range(5)],[str(i) for i in range(5,8)]),None,
                          checker=good,sleeper=lambda _:None)
    assert summary['checked']==20
    assert len(fresh)==20
    rows=copy.deepcopy(rows)  # Saved lifecycle flags must not substitute for evidence.
assert all(r.get('last_attempt_at') for r in rows.values())
assert all(r.get('last_verified_at') for r in rows.values())

# Time budget halts requests and preserves the remainder.
rows={str(i):row(str(i)) for i in range(100)}
class Clock:
    value=0
    def __call__(self): return self.value
clock=Clock()
def slow(url,session):
    clock.value+=100
    return good(url,session)
fresh,s=verify(rows,list(rows),None,checker=slow,clock=clock,sleeper=lambda _:None)
assert s['checked']==3 and s['pending']==97
assert len(fresh)==3

# Ambiguous, expired, mismatched and deferred jobs never enter public candidates.
rows={str(i):row(str(i)) for i in range(5)}
def mixed(url,session):
    k=url.rsplit('/',1)[-1]
    if k=='0': raise requests.Timeout('offline')
    if k=='1': return {'closure_status':'closed','reason':'closed_marker'}
    if k=='2': return {'closure_status':'still_active','job_number':'wrong'}
    return good(url,session)
fresh,s=verify(rows,list(rows),None,max_checks=4,checker=mixed,sleeper=lambda _:None)
assert [r['job_number'] for r in fresh]==['3']
assert s=={'checked':4,'pending':1,'review_required':2,'closed':1}
assert rows['4']['lifecycle_status']=='pending'
assert '1' not in priority(rows,[],[])
assert '1' in priority(rows,['1'],[]) # Reappearance is reverified.
# Carrying an old active flag cannot bypass the execution's fresh set.
fresh,s=verify(rows,list(rows),None,budget=0,checker=good,sleeper=lambda _:None)
assert fresh==[]
print('PASS bounded daily: 1000-job fairness, durable queue, count/time budgets, fail-closed publication, terminal states')

# Full runner: save deferred queue, then reload and advance it; publish fresh only.
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import hellowork_daily as daily
with tempfile.TemporaryDirectory() as td:
    state=Path(td)/'state.json'; output=Path(td)/'jobs.js'; audit=Path(td)/'audit.json'
    state.write_text(json.dumps({'results':[row(str(i)) for i in range(40)]}))
    def offline(rows,order,session):
        return verify(rows,order,session,checker=good,sleeper=lambda _:None)
    argv=['daily','--state',str(state),'--output',str(output),'--audit',str(audit)]
    for attempt in range(2):
        with patch.object(sys,'argv',argv), patch.object(daily,'discover',return_value=[]), patch.object(daily,'verify',side_effect=offline):
            daily.main()
        saved=json.loads(state.read_text())
        assert saved['summary']['checked']==20 and saved['summary']['published']==3
        assert len(saved['results'])==40
        assert output.read_text().count('"source": "hellowork-live-test"')==3
    assert sum(bool(r.get('last_attempt_at')) for r in saved['results'])==37
print('PASS full runner persistence and publication across two executions')
