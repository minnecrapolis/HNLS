#!/usr/bin/env python3
"""Offline release checks; no hardware/dependency readiness claim."""
import ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def validate():
    paths=list(ROOT.rglob('*.py'))
    for p in paths:
        if 'dist' not in p.relative_to(ROOT).parts:
            ast.parse(p.read_text(encoding='utf-8'),filename=str(p),feature_version=(3,9) if 'receiver' in p.relative_to(ROOT).parts else (3,11))
            compile(p.read_text(encoding='utf-8'),str(p),'exec')
    for name in ['README.md','VERSION','THIRD_PARTY.md','docs/RELEASE_STATUS.md','src/controller/server/main.py','src/receiver/receiver.py']:
        assert (ROOT/name).is_file(),name
    for p in ROOT.rglob('*'):
        if p.is_file() and not any(x in p.parts for x in ['dist','__pycache__','.git']):
            assert p.name not in {'config.json','song_moments.json','remote_pis.json','bridge-config.json','pc_stream.json','connection.json'},str(p)
            assert p.suffix.lower() not in {'.mp3','.wav','.pem','.key'},str(p)
    driver=(ROOT/'src/controller/server/libs/outputs/output_raspi.py').read_text()
    assert 'r = np.left_shift(output_array[0][:].astype(int), 16)' in driver
    music=(ROOT/'src/controller/server/libs/app/templates/home/music.html').read_text()
    assert 'hnls_playlist.js' in music
    sys_path = str(ROOT)
    import sys
    sys.path.insert(0, sys_path)
    from install import check_payload
    check_payload()
    print('PASS:',len(paths),'Python sources parsed; release structure, payload hashes, exclusions and merged fixes checked.')
if __name__=='__main__':validate()
