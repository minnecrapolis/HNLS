#!/usr/bin/env python3
"""Build deterministic source archive with fixed timestamps and checksums."""
from pathlib import Path
import hashlib,zipfile
from validate import ROOT,validate

def build():
    validate();version=(ROOT/'VERSION').read_text().strip();dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    target=dist/('HNLS-'+version+'-source.zip')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob('*')):
            rel=p.relative_to(ROOT)
            if not p.is_file() or any(s in {'dist','.git','__pycache__','.venv'} for s in rel.parts) or p.suffix=='.pyc':continue
            info=zipfile.ZipInfo('HNLS/'+rel.as_posix(),(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes())
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    sums=[digest+'  '+target.name]
    for folder,name,top in [('show-hours','hnls-show-hours-update.zip','hnls-show-hours-update'),('designer-effects','hnls-designer-effects-update.zip','hnls-designer-effects-update'),('two-color','hnls-two-color-update.zip','hnls-two-color-update'),('moment-edit','hnls-moment-edit-update.zip','hnls-moment-edit-update')]:
        update=dist/name
        with zipfile.ZipFile(update,'w',compression=zipfile.ZIP_DEFLATED) as z:
            source=ROOT/'updates'/folder
            for p in sorted(source.rglob('*')):
                if not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
                info=zipfile.ZipInfo(top+'/'+p.relative_to(source).as_posix(),(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
                z.writestr(info,p.read_bytes())
        sums.append(hashlib.sha256(update.read_bytes()).hexdigest()+'  '+update.name)
    (dist/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
    print(target)
if __name__=='__main__':build()
