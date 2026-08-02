#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, pathlib, shutil, time, zipfile
root=pathlib.Path(os.environ.get('LOG_ROOT','ci-logs')); root.mkdir(parents=True,exist_ok=True)
status_dir=root/'status'
order=['clone-upstream','setup-go','go-environment','apply-core-patch','prepare-modules','source-verify','vendor','apply-vendor-patch','gofmt','verify-patch','tests','compile','wintun','linux-smoke','package','windows-smoke','release']
code={'clone-upstream':'E03_CHECKOUT','setup-go':'E04_GO_SETUP','go-environment':'E04_GO_ENV','apply-core-patch':'E10_CORE_PATCH','prepare-modules':'E11_MODULE_PREP','source-verify':'E12_PATCH_VERIFY','vendor':'E20_DEPENDENCY','apply-vendor-patch':'E21_VENDOR_PATCH','gofmt':'E22_GOFMT','verify-patch':'E23_PATCH_VERIFY','tests':'E24_TEST','compile':'E30_COMPILE','wintun':'E42_WINTUN_DLL','package':'E50_PACKAGE','linux-smoke':'E40_SMOKE','windows-smoke':'E41_WINDOWS_SMOKE','release':'E60_RELEASE_UPLOAD'}
steps={}
for s in order:
    p=status_dir/f'{s}.exit'
    steps[s]=int(p.read_text().strip()) if p.exists() and p.read_text().strip().lstrip('-').isdigit() else None
failed=next((s for s in order if steps[s] not in (None,0)),None)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
summary={
 'upstream_tag':os.getenv('UPSTREAM_TAG','unknown'), 'upstream_commit':os.getenv('UPSTREAM_COMMIT','unknown'),
 'baseline_tag':os.getenv('BASELINE_TAG','v1.19.29'),'patch_revision':os.getenv('PATCH_REVISION','unknown'),
 'workflow_run_id':os.getenv('GITHUB_RUN_ID','local'),'workflow_run_attempt':os.getenv('GITHUB_RUN_ATTEMPT','local'),
 'workflow_run_url':f"{os.getenv('GITHUB_SERVER_URL','https://github.com')}/{os.getenv('GITHUB_REPOSITORY','unknown')}/actions/runs/{os.getenv('GITHUB_RUN_ID','unknown')}",
 'generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), 'first_failed_step':failed,
 'failure_code':code.get(failed) if failed else None, 'steps':steps,
}
for p in [pathlib.Path('source/go.mod'),pathlib.Path('source/go.sum'),pathlib.Path('source/dist/verge-mihomo.exe'),pathlib.Path('source/dist/wintun.dll')]:
    if p.exists(): summary[p.name+'_sha256']=sha(p)
(root/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
lines=['Mihomo hybrid auto-build summary']+[f'{k}={v}' for k,v in summary.items() if k!='steps']+['','Step results:']
for s in order:
    v=steps[s]; lines.append(f'{s:24} '+('SKIPPED' if v is None else ('PASS' if v==0 else f'FAILED({v})')))
(root/'summary.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# Always produce one downloadable archive, even when compile/package failed.
with zipfile.ZipFile(root/'downloadable-logs.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.name!='downloadable-logs.zip': z.write(p,p.relative_to(root))
print(root/'summary.txt')
