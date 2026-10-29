#!/usr/bin/env python3
"""Repair the observed HNLS legacy configuration errors and disable cues safely."""
import argparse
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def load_schema(root):
    """Use the installed schema and venv dependencies, never a replacement schema."""
    sys.path.insert(0,str(root/'server'))
    from jsonschema import Draft202012Validator
    path=root/'server/libs/webserver/schemas/config_validator_service.py'
    spec=importlib.util.spec_from_file_location('_hnls_recovery_schema',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator=Draft202012Validator(module.schema,format_checker=Draft202012Validator.FORMAT_CHECKER)
    return module.schema,validator


def repair_config(original,schema):
    if not isinstance(original,dict) or not isinstance(original.get('device_configs'),dict):
        raise ValueError('Expected an HNLS configuration object; no files changed')
    candidate=deepcopy(original)
    changes=[]
    device_schema=schema['properties']['default_device']
    allowed_device=device_schema['properties']
    allowed_effects=allowed_device['effects']['properties']
    entries=[('default_device',candidate.get('default_device'))]+[(f'device_configs.{key}',d) for key,d in candidate.get('device_configs',{}).items()]
    for label,device in entries:
        if not isinstance(device,dict):continue
        effects=device.get('effects')
        if not isinstance(effects,dict):continue
        # The nested effect is canonical; never replace it with a stale outer value.
        if 'last_effect' in device and 'last_effect' not in allowed_device:
            if 'last_effect' not in effects:
                effects['last_effect']=device['last_effect']
                changes.append(label+': moved last_effect inside effects')
            else:
                changes.append(label+': removed stale outer last_effect; kept '+str(effects['last_effect']))
            device.pop('last_effect')
        for legacy in ('effect_music','effect_spectrum'):
            if legacy in effects and legacy not in allowed_effects:
                if effects.get('last_effect')==legacy:
                    raise ValueError(label+': '+legacy+' is active but unsupported; not choosing a replacement effect')
                effects.pop(legacy)
                changes.append(label+': archived unsupported '+legacy+' in original backup')
        vu=effects.get('effect_vu_meter',{})
        value=vu.get('use_gradient') if isinstance(vu,dict) else None
        if isinstance(value,str) and value.strip().lower() in ('true','false'):
            vu['use_gradient']=value.strip().lower()=='true'
            changes.append(label+': converted use_gradient to a boolean')
    return candidate,changes


def prepare(path,schema,validator):
    original=json.loads(path.read_text())
    candidate,changes=repair_config(original,schema)
    errors=list(validator.iter_errors(candidate))
    if errors:
        details='\n'.join(str(getattr(e,'json_path','config'))+': '+str(e.message)[:220] for e in errors[:12])
        raise ValueError('Other configuration errors remain; no repaired file written:\n'+details)
    return candidate,changes


def atomic_json(path,data):
    temporary=path.with_name(path.name+'.hnls-recovery.tmp')
    if path.exists():
        previous=path.stat()
        shutil.copy2(path,temporary)
        if hasattr(os,'chown') and os.geteuid()==0:os.chown(temporary,previous.st_uid,previous.st_gid)
    else:
        descriptor=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(descriptor)
    try:
        with temporary.open('w') as stream:
            json.dump(data,stream,indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def capture(backup):
    commands={
        'service-before.txt':['systemctl','status','mlsc','--no-pager','-l'],
        'journal-before.txt':['journalctl','-u','mlsc','-n','400','--no-pager','-o','short-iso'],
        'kernel-before.txt':['journalctl','-k','-b','-n','250','--no-pager'],
        'power-before.txt':['vcgencmd','get_throttled']}
    for name,command in commands.items():
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=10,check=False)
            (backup/name).write_text(result.stdout+result.stderr)
        except (OSError,subprocess.SubprocessError) as exc:
            (backup/name).write_text(str(exc))


def recover(root,path,schema,validator,no_service=False):
    # Verify the complete candidate against the INSTALLED schema before stopping.
    prepare(path,schema,validator)
    folder=path.parent/('hnls-recovery-'+str(time.time_ns()))
    folder.mkdir(mode=0o700)
    if not no_service:
        capture(folder)
        subprocess.run(['systemctl','stop','mlsc'],check=True)
    config_written=False
    try:
        # Re-read after the service stops so the repair cannot overwrite a concurrent save.
        candidate,changes=prepare(path,schema,validator)
        shutil.copy2(path,folder/'config.json')
        original_backup=path.parent/'config_backup.json'
        if original_backup.is_file():shutil.copy2(original_backup,folder/'config_backup.json')
        cue_path=path.parent/'song_moments.json'
        if cue_path.is_file():
            shutil.copy2(cue_path,folder/'song_moments.json')
            try:
                saved=json.loads(cue_path.read_text())
                regions=saved.get('regions',[]) if isinstance(saved,dict) else []
                if not isinstance(regions,list):regions=[]
            except ValueError:regions=[]
            atomic_json(cue_path,{'version':1,'cues':[],'regions':regions})
        else:
            disabled=sorted(path.parent.glob('song_moments.disabled-*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
            if disabled:
                shutil.copy2(disabled[0],folder/'previously-disabled-song-moments.json')
                try:
                    saved=json.loads(disabled[0].read_text())
                    regions=saved.get('regions',[]) if isinstance(saved,dict) else []
                    if isinstance(regions,list):atomic_json(cue_path,{'version':1,'cues':[],'regions':regions})
                except ValueError:pass
        atomic_json(path,candidate)
        config_written=True
        if not no_service:
            subprocess.run(['systemctl','start','mlsc'],check=True)
            subprocess.run(['systemctl','is-active','--quiet','mlsc'],check=True)
    except Exception:
        if config_written and (folder/'config.json').is_file():shutil.copy2(folder/'config.json',path)
        # Keep cue suppression in place; never automatically restore the white cue.
        if not no_service:subprocess.run(['systemctl','stop','mlsc'],check=False)
        print('Recovery did not complete. Service left stopped. Originals:',folder)
        raise
    print('HNLS configuration passes the installed schema.')
    print('Specific fields repaired:',len(changes))
    for change in changes:print('  '+change)
    print('Saved song cues are disabled. Named light groups are retained when available.')
    print('All original settings and cues are preserved in:',folder)
    print('GPIO assignments, LED counts, colors, brightness, audio and remote pairing were not reset.')
    if not no_service:
        print('Installed service mlsc is running. Refresh the HNLS web page.')
        print('Keep LED power off for the first check. Do not replay the white cue yet.')
    return folder


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('/share/music_led_strip_control'))
    parser.add_argument('--config',type=Path)
    parser.add_argument('--check',action='store_true',help='Validate proposed repair without writing or controlling services')
    parser.add_argument('--no-service',action='store_true',help='Offline verification only')
    args=parser.parse_args()
    if not args.check and not args.no_service and os.geteuid()!=0:parser.error('Run with sudo /share/.venv/bin/python3')
    root=args.root.resolve();path=args.config or root.parent/'.mlsc/config.json'
    schema,validator=load_schema(root)
    if args.check:
        _,changes=prepare(path,schema,validator)
        print('Proposed repair passes the installed schema; no files changed.')
        for change in changes:print(change)
        return
    recover(root,path,schema,validator,args.no_service)


if __name__=='__main__':
    try:main()
    except ModuleNotFoundError as exc:raise SystemExit('Use the HNLS venv: sudo /share/.venv/bin/python3 /home/pi/recover_hnls.py. Missing dependency: '+str(exc)) from None
    except (ValueError,OSError,subprocess.SubprocessError) as exc:raise SystemExit(str(exc)) from None
