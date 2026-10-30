#!/usr/bin/env python3
"""Explicitly refresh reviewed release payload hashes after source changes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def payload():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['src','requirements'] for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
if __name__=='__main__':
    (ROOT/'release-manifest.json').write_text(json.dumps(payload(),indent=2)+'\n')
    print('Manifest updated. Review and commit the source/hash diff together.')
