#!/usr/bin/env python3
from __future__ import annotations
import json, os, urllib.error, urllib.request
repo=os.environ['GITHUB_REPOSITORY']; token=os.environ['GITHUB_TOKEN']; tag=os.environ['UPSTREAM_TAG']; outcome=os.environ.get('BUILD_OUTCOME','failure')
marker=f'<!-- mihomo-upstream-tag:{tag} -->'; base=f'https://api.github.com/repos/{repo}'
def request(path,method='GET',data=None):
    body=json.dumps(data).encode() if data is not None else None
    req=urllib.request.Request(base+path,data=body,method=method,headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','User-Agent':'mihomo-hybrid-auto-builder','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r) if r.length!=0 else {}
try: request('/labels', 'POST', {'name':'auto-build-failed','color':'d73a4a','description':'Automatic Mihomo tag build needs patch maintenance'})
except urllib.error.HTTPError as e:
    if e.code!=422: print(f'label warning: {e}')
issues=request('/issues?state=open&labels=auto-build-failed&per_page=100')
matched=[i for i in issues if marker in (i.get('body') or '')]
if outcome=='success':
    for i in matched: request(f"/issues/{i['number']}",'PATCH',{'state':'closed','state_reason':'completed'})
elif not matched:
    run=f"{os.getenv('GITHUB_SERVER_URL','https://github.com')}/{repo}/actions/runs/{os.getenv('GITHUB_RUN_ID','')}"
    body=f"{marker}\n\nAuto-build failed for `{tag}`.\n\nWorkflow: {run}\n\nDownload the `build-logs-*` artifact and inspect `summary.txt` plus `full-build.log`.\n\nThe scheduled checker will skip this tag until this issue is closed or a successful manual rebuild closes it."
    request('/issues','POST',{'title':f'[AUTO-BUILD FAILED] {tag}','body':body,'labels':['auto-build-failed']})
