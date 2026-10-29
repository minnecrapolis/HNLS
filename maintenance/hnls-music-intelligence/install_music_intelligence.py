#!/usr/bin/env python3
"""Install scoped HNLS song preparation and playlist shuffle on LED03."""
import argparse,ast,hashlib,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path

LIB='server/libs/'
COPIES=['song_analysis.py','hnls_playlist.py','effects/effect_song_show.py','app/static/assets/js/hnls_playlist.js']
CHANGED=[LIB+n for n in COPIES]+[LIB+'audio_process_service.py',LIB+'webserver/blueprints/music_library_api.py',LIB+'app/templates/home/music.html']

def replace_method(source,reference):
    def method(text):
        cls=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='AudioProcessService')
        return next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_advance_music')
    old,new=method(source),method(reference);lines=source.splitlines(True)
    lines[old.lineno-1:old.end_lineno]=reference.splitlines(True)[new.lineno-1:new.end_lineno]
    result=''.join(lines);ast.parse(result);return result

def updates(root,package):
    result={LIB+n:(package/'files'/LIB/n).read_bytes() for n in COPIES}
    audio=(root/LIB/'audio_process_service.py').read_text()
    result[LIB+'audio_process_service.py']=replace_method(audio,(package/'advance_music.py').read_text()).encode()
    path=LIB+'webserver/blueprints/music_library_api.py';api=(root/path).read_text()
    extra=(package/'api_additions.py').read_text()
    # Replace only our own endpoints on a repeat install.
    names={'hnls_show_preparation','hnls_prepare_library','hnls_playlist_settings'}
    nodes=[n for n in ast.parse(api).body if isinstance(n,ast.FunctionDef) and n.name in names]
    lines=api.splitlines(True)
    for node in sorted(nodes,key=lambda n:n.lineno,reverse=True):
        start=min([node.lineno]+[d.lineno for d in node.decorator_list]);lines[start-1:node.end_lineno]=[]
    api=''.join(lines).rstrip()+'\n\n\n'+extra
    if '# HNLS prepare uploaded song' not in api:
        anchor='    upload.save(destination)\n'
        if api.count(anchor)!=1:raise ValueError('Unexpected upload route; nothing changed')
        api=api.replace(anchor,anchor+'''    # HNLS prepare uploaded song without blocking the upload response.
    try:
        from libs.hnls_playlist import start_preparation
        start_preparation()
    except OSError:
        pass
''',1)
    ast.parse(api);result[path]=api.encode()
    path=LIB+'app/templates/home/music.html';html=(root/path).read_text()
    begin='<!-- HNLS SONG INTELLIGENCE START -->';end='<!-- HNLS SONG INTELLIGENCE END -->'
    if begin in html:
        start=html.index(begin);stop=html.index(end,start)+len(end);html=html[:start]+html[stop:]
    anchor='<div class="hnls-music-workspace">'
    if html.count(anchor)!=1:raise ValueError('Install the new HNLS interface before this update; nothing changed')
    html=html.replace(anchor,begin+(package/'panel.html').read_text()+end+anchor,1)
    script='<script src="{{ url_for(\'static\',filename=\'assets/js/hnls_playlist.js\') }}?v=1"></script>'
    if 'assets/js/hnls_playlist.js' not in html:
        anchor='{% block javascripts %}'
        if html.count(anchor)!=1:raise ValueError('Unexpected music scripts block; nothing changed')
        html=html.replace(anchor,anchor+script,1)
    result[path]=html.encode()
    for name,data in result.items():
        if name.endswith('.py'):ast.parse(data.decode())
    return result

def service(action):subprocess.run(['systemctl',action,'mlsc'],check=True,timeout=90)

def restore(root,backup,check=False):
    manifest=json.loads((backup/'manifest.json').read_text())
    if set(manifest)!=set(CHANGED):raise ValueError('Invalid backup manifest')
    for name,existed in manifest.items():
        if type(existed) is not bool or (existed and not (backup/name).is_file()):raise ValueError('Incomplete backup')
    if check:return
    for name,existed in manifest.items():
        target=root/name
        if existed:shutil.copy2(backup/name,target)
        else:target.unlink(missing_ok=True)

def install(root,package,no_service=False):
    hashes=json.loads((package/'sha256.json').read_text())
    for name,digest in hashes.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('Invalid package path')
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=digest:raise ValueError('Checksum mismatch: '+name)
    candidate=updates(root,package)
    backup=root.parent/('hnls-music-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(mode=0o700)
    if not no_service:service('stop')
    manifest={}
    try:
        for name in CHANGED:
            target=root/name;manifest[name]=target.is_file()
            if target.is_file():
                saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
        for name,data in candidate.items():
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.hnls.tmp')
            try:
                if target.exists():
                    shutil.copy2(target,temporary)
                    if os.geteuid()==0:
                        s=target.stat();os.chown(temporary,s.st_uid,s.st_gid)
                temporary.write_bytes(data);temporary.chmod(0o644);temporary.replace(target)
            finally:temporary.unlink(missing_ok=True)
        if not no_service:
            service('start');subprocess.run(['systemctl','is-active','--quiet','mlsc'],check=True,timeout=15)
    except Exception:
        if not no_service:subprocess.run(['systemctl','stop','mlsc'],check=False)
        if (backup/'manifest.json').is_file():restore(root,backup)
        if not no_service:subprocess.run(['systemctl','start','mlsc'],check=False)
        raise
    return backup

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=Path('/share/music_led_strip_control'));parser.add_argument('--no-service',action='store_true');parser.add_argument('--restore',type=Path);args=parser.parse_args()
    if not args.no_service and os.geteuid()!=0:parser.error('Run with sudo /share/.venv/bin/python3')
    root=args.root.resolve()
    if args.restore:
        restore(root,args.restore,True)
        if not args.no_service:service('stop')
        restore(root,args.restore)
        if not args.no_service:service('start')
        print('Previous song analysis and playlist code restored.');return
    backup=install(root,Path(__file__).resolve().parent,args.no_service)
    print('HNLS song intelligence and Shuffle playlist installed. Refresh Music with Ctrl+F5.')
    print('Open Music to prepare existing songs. Uploads queue automatically. Analysis is cached.')
    print('Playback can continue while preparation runs. Best consistency comes after songs show Ready.')
    print('Songs, manual cues, GPIOs, remote pairing, audio and brightness settings were retained.')
    print('Shuffle preference survives reboot; the shuffle pass/history starts fresh on a service restart.')
    print('Rollback: sudo /share/.venv/bin/python3',Path(__file__).resolve(),'--restore',backup)

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,StopIteration,SyntaxError,subprocess.SubprocessError) as exc:raise SystemExit(str(exc)) from None
