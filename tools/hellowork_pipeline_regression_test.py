#!/usr/bin/env python3
"""Offline integration checks for discovery/diff/recheck/merge boundaries."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import requests
import hellowork_closure_recheck_test as recheck


def run_tool(name, *args):
    subprocess.check_call([sys.executable, f'tools/{name}.py', *map(str,args)], stdout=subprocess.DEVNULL)


with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    def write(name, value):
        p=root/name
        p.write_text(json.dumps(value), encoding='utf-8')
        return p
    def read(p):
        return json.loads(p.read_text(encoding='utf-8'))
    for count in (0,30,31,34,100):
        previous=[{'job_number':str(i),'status':'test_candidate','lifecycle_status':'active',
                   'source_url':f'https://example.invalid/{i}'} for i in range(count)]
        previous.append({'job_number':'closed','status':'test_candidate','lifecycle_status':'closed'})
        prev=write('prev.json',{'results':previous})
        cur=write('cur.json',{'results':[{'job_number':'new','status':'test_candidate'}]})
        diff=root/'diff.json'; close=root/'close.json'; merged=root/'merged.json'
        run_tool('hellowork_diff_test','--previous',prev,'--current',cur,'--output',diff)
        assert len(read(diff)['ended_candidate']) == count
        def check(url, session):
            return {'closure_status':'still_active','job_number':url.rsplit('/',1)[-1]}
        argv=['recheck','--diff',str(diff),'--output',str(close)]
        with patch.object(sys,'argv',argv), patch.object(recheck,'check_url',side_effect=check) as mock, patch.object(recheck.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
            recheck.main()
        assert mock.call_count == count
        assert read(close)['unchecked_count'] == 0
        run_tool('hellowork_state_merge_test','--previous',prev,'--current',cur,'--closure',close,'--output',merged)
        assert read(merged)['summary'] == {'active':count+1,'closed':1,'review_required':0,'total':count+2}
    # A timeout is recorded per job, and later jobs still get checked.
    with patch.object(sys,'argv',argv), patch.object(recheck,'check_url',side_effect=[requests.Timeout('test')]+[{'closure_status':'still_active'} for _ in range(99)]), patch.object(recheck.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
        recheck.main()
    assert read(close)['summary']['review_required'] == 1
    run_tool('hellowork_state_merge_test','--previous',prev,'--current',cur,'--closure',close,'--output',merged)
    assert read(merged)['summary']['review_required'] == 1
    # Explicit diagnostic limits remain visible as incomplete coverage.
    with patch.object(sys,'argv',argv+['--max','30']), patch.object(recheck,'check_url',side_effect=check), patch.object(recheck.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
        recheck.main()
    assert read(close)['unchecked_count'] == 70
    run_tool('hellowork_state_merge_test','--previous',prev,'--current',cur,'--closure',close,'--output',merged)
    assert read(merged)['summary']['review_required'] == 70

# Reuse the same HTTP response for closure classification and detail parsing.
from unittest.mock import Mock
response=Mock(status_code=200, apparent_encoding='utf-8', text='<html>public job</html>')
session=Mock(); session.get.return_value=response
with patch.object(recheck,'extract_job',return_value={'status':'test_candidate','job_number':'A'}) as extract:
    assert recheck.check_url('https://example.invalid/A',session)['closure_status']=='still_active'
    session.get.assert_called_once()
    assert extract.call_args.kwargs['response'] is response
print('PASS pipeline: 0/30/31/34/100 candidates, terminal states, request failure, incomplete coverage, single fetch')
