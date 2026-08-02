#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, urllib.request
baseline=os.getenv('BASELINE_TAG','v1.19.29'); revision=os.getenv('RELEASE_REVISION','r1')
def api(path):
    req=urllib.request.Request('https://api.github.com'+path,headers={'Accept':'application/vnd.github+json','User-Agent':'mihomo-hybrid-auto-builder','Authorization':f"Bearer {os.getenv('GITHUB_TOKEN','')}"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def ver(t): return tuple(map(int,t.removeprefix('v').split('.')))
rel=api('/repos/MetaCubeX/mihomo/releases/latest')
tag=rel.get('tag_name','')
stable=bool(re.fullmatch(r'v\d+\.\d+\.\d+',tag)) and not rel.get('draft') and not rel.get('prerelease')
release_tag=f'hybrid-{tag}-{revision}'
exists=False
try: api(f'/repos/{os.environ["GITHUB_REPOSITORY"]}/releases/tags/{release_tag}'); exists=True
except Exception: pass
blocked=False
try:
    issues=api(f'/repos/{os.environ["GITHUB_REPOSITORY"]}/issues?state=open&labels=auto-build-failed&per_page=100')
    marker=f'<!-- mihomo-upstream-tag:{tag} -->'
    blocked=any(marker in (i.get('body') or '') for i in issues)
except Exception: pass
should=stable and ver(tag)>ver(baseline) and not exists and not blocked
out={'latest_tag':tag,'stable':stable,'release_tag':release_tag,'release_exists':exists,'blocked_by_issue':blocked,'should_build':should}
print(json.dumps(out,indent=2))
if os.getenv('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:
        for k,v in out.items(): f.write(f'{k}={str(v).lower() if isinstance(v,bool) else v}\n')
