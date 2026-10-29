"""Persistent playlist preferences, no-repeat shuffle and background preparation."""
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

ROOT=Path(os.environ.get('HNLS_SETTINGS_DIR','/share/.mlsc'))
_worker=None

def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.'+str(os.getpid())+'.tmp')
    try:
        tmp.write_text(json.dumps(data));tmp.chmod(0o600);tmp.replace(path)
    finally:tmp.unlink(missing_ok=True)

def settings():
    try:
        value=json.loads((ROOT/'playlist_settings.json').read_text())
        return {'shuffle':value.get('shuffle') is True}
    except (OSError,ValueError,AttributeError):return {'shuffle':False}

def save_settings(value):
    if not isinstance(value,dict) or set(value)!={'shuffle'} or type(value['shuffle']) is not bool:
        raise ValueError('Choose Shuffle playlist on or off')
    atomic(ROOT/'playlist_settings.json',value)
    return settings()

class ShuffleQueue:
    def __init__(self,rng=None):
        self.rng=rng or random.SystemRandom();self.history=[];self.cursor=-1;self.played=set();self.bag=[];self.direction=1

    def order(self,songs,current,direction):
        songs=list(dict.fromkeys(songs));available=set(songs);self.direction=direction
        if self.cursor<0 or self.history[self.cursor]!=current:
            self.history=self.history[:self.cursor+1]+[current];self.cursor=len(self.history)-1
        self.played.add(current);self.played.intersection_update(available)
        self.bag=[n for n in self.bag if n in available and n not in self.played]
        new=[n for n in songs if n not in self.played and n not in self.bag]
        self.rng.shuffle(new);self.bag.extend(new)
        if not self.bag:
            self.played={current};self.bag=[n for n in songs if n!=current];self.rng.shuffle(self.bag)
        history=(list(reversed(self.history[:self.cursor])) if direction<0 else self.history[self.cursor+1:])
        result=[]
        for n in history+self.bag+([current] if current in available else []):
            if n in available and n not in result:result.append(n)
        return result

    def selected(self,name):
        if self.direction<0:
            matches=[i for i,n in enumerate(self.history[:self.cursor]) if n==name]
            if matches:self.cursor=matches[-1];return
        elif self.cursor+1<len(self.history) and self.history[self.cursor+1]==name:
            self.cursor+=1;return
        self.history=self.history[:self.cursor+1]+[name];self.history=self.history[-500:];self.cursor=len(self.history)-1
        self.played.add(name);self.bag=[n for n in self.bag if n!=name]

def shuffle_order(service,songs,current,direction,fallback):
    if not settings()['shuffle']:
        service._hnls_shuffle=None;return fallback
    if getattr(service,'_hnls_shuffle',None) is None:service._hnls_shuffle=ShuffleQueue()
    return service._hnls_shuffle.order(songs,current,direction)

def shuffle_selected(service,name):
    queue=getattr(service,'_hnls_shuffle',None)
    if queue:queue.selected(name)

def profile_summary():
    from libs.music_library import list_music_files,safe_music_path
    from libs.song_analysis import cache_path,valid_profile
    result=[]
    for item in list_music_files():
        row={'file':item['name'],'ready':False}
        try:
            profile=json.loads(cache_path(safe_music_path(item['name'])).read_text())
            if valid_profile(profile):
                row.update(ready=True,tempo=profile.get('tempo_bpm'),sections=len(profile['sections']),duration=profile.get('duration'))
        except (OSError,ValueError,KeyError,AttributeError):pass
        result.append(row)
    try:progress=json.loads((ROOT/'preparation_status.json').read_text())
    except (OSError,ValueError):progress={}
    if not isinstance(progress,dict):progress={}
    if progress.get('state')=='analyzing':
        try:
            pid=int(progress.get('pid',0))
            if pid<=0:raise ValueError('Missing worker PID')
            os.kill(pid,0)
        except (OSError,ValueError,TypeError):progress={'state':'idle'}
    return {'settings':settings(),'files':result,'ready':sum(r['ready'] for r in result),'total':len(result),'progress':progress}

def start_preparation():
    global _worker
    if _worker is not None and _worker.poll() is None:return {'queued':True}
    _worker=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--prepare'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
    return {'queued':True}

def prepare_library():
    import fcntl
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    from libs.music_library import list_music_files,safe_music_path
    from libs.song_analysis import analyze_file,cache_path
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'preparation.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        def status(state,filename=None,error=None):atomic(ROOT/'preparation_status.json',{'state':state,'file':filename,'error':error,'pid':os.getpid(),'updated':time.time()})
        failures=[]
        for item in list_music_files():
            name=item['name'];status('analyzing',name)
            try:analyze_file(safe_music_path(name))
            except Exception as exc:failures.append({'file':name,'error':str(exc)[:200]})
        atomic(ROOT/'preparation_status.json',{'state':'complete','errors':failures,'updated':time.time()})

if __name__=='__main__':
    try:os.nice(10)
    except (AttributeError,OSError):pass
    prepare_library()
