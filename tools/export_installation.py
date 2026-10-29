#!/usr/bin/env python3
"""Collect application source for private reconciliation; excludes runtime state."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path
ALLOWED={'.py','.html','.css','.js','.svg','.png','.jpg','.jpeg','.ico','.woff','.woff2','.ttf','.eot','.txt','.md','.rst','.toml','.ini','.cfg','.sh'}
BAD={'__pycache__','.git','.venv','venv','node_modules','music','logs','backups'}
SECRET=re.compile(r'-----BEGIN (?:OPENSSH|RSA|EC|ENCRYPTED) PRIVATE KEY-----|sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}',re.I)
def collect(root):
    approved=[];skipped=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if p.is_symlink():skipped.append(str(rel));continue
        if not p.is_file():continue
        if any(x.lower() in BAD for x in rel.parts) or any(x in p.name.lower() for x in ('backup','before-','secret','credential','.env','authorized_keys')) or p.suffix.lower() not in ALLOWED or p.stat().st_size>8*1024*1024:
            skipped.append(str(rel));continue
        data=p.read_bytes()
        if SECRET.search(data.decode('utf-8',errors='ignore')):skipped.append(str(rel));continue
        approved.append((rel.as_posix(),data))
    return approved,skipped

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--role',required=True,choices=['controller','receiver']);a.add_argument('--root',type=Path);a.add_argument('--output',required=True,type=Path);x=a.parse_args()
    root=(x.root or Path('/share/music_led_strip_control' if x.role=='controller' else '/opt/mlsc-receiver')).resolve()
    if not root.is_dir():raise SystemExit('Application directory not found: '+str(root))
    if x.output.exists():raise SystemExit('Output exists; choose a new filename.')
    if root==x.output.resolve() or root in x.output.resolve().parents:raise SystemExit('Choose an output outside the application directory.')
    files,skipped=collect(root);service='mlsc' if x.role=='controller' else 'mlsc-receiver'
    # Only installed package names/versions, never pip direct-URL credentials.
    py=Path('/share/.venv/bin/python3' if x.role=='controller' else '/opt/mlsc-receiver/venv/bin/python3')
    metadata={};manifest={n:hashlib.sha256(b).hexdigest() for n,b in files}
    for name,cmd in [('packages',[str(py),'-m','pip','list','--format=json']),('service',['systemctl','cat',service])]:
        try:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=45)
            value=p.stdout
            if SECRET.search(value) or (name=='service' and re.search(r'(?im)^\s*(Environment|EnvironmentFile|SetCredential|LoadCredential)',value)):
                value='OMITTED: review service unit locally; may contain credentials.'
            metadata[name]={'exit_code':p.returncode,'output':value}
        except (OSError,subprocess.TimeoutExpired) as e:metadata[name]={'error':type(e).__name__}
    with x.output.open('xb') as stream:
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for n,b in files:z.writestr('application/'+n,b)
            z.writestr('capture-report.json',json.dumps({'role':x.role,'files':manifest,'skipped':skipped,'metadata':metadata},indent=2))
    x.output.chmod(0o600)
    print('Private capture written:',x.output,'Files:',len(files),'Skipped:',len(skipped))
    print('Review privately before sharing. No music or runtime JSON configuration was collected.')
if __name__=='__main__':main()
