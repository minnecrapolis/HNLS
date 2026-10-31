"""Persistent local-time show windows; no browser or cron dependency."""
from datetime import datetime,timedelta,timezone
import json,os,re,threading,time
from pathlib import Path
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

DEFAULT={'enabled':False,'days':list(range(7)),'start':'17:00','end':'22:00','timezone':'America/Chicago'}

def validate(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT):raise ValueError('Expected enabled, days, start, end and timezone')
    if type(value['enabled']) is not bool:raise ValueError('Enable schedule must be on or off')
    days=value['days']
    if not isinstance(days,list) or not days or any(type(d) is not int or not 0<=d<=6 for d in days) or len(set(days))!=len(days):raise ValueError('Select at least one day, Monday through Sunday')
    for name in ['start','end']:
        if not isinstance(value[name],str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value[name]):raise ValueError('Use a valid hour and minute')
    if value['start']==value['end']:raise ValueError('Start and stop times must be different')
    zone=value['timezone']
    if not isinstance(zone,str) or len(zone)>100:raise ValueError('Choose a valid time zone')
    try:ZoneInfo(zone)
    except (ZoneInfoNotFoundError,ValueError):raise ValueError('Unknown time zone; use an IANA name such as America/Chicago') from None
    return {**value,'days':sorted(days)}

def window_key(settings,now):
    """An overnight window belongs to the weekday on which it starts."""
    if not settings['enabled']:return None
    local=now.astimezone(ZoneInfo(settings['timezone']));minute=local.strftime('%H:%M');day=local.date()
    start,end=settings['start'],settings['end']
    if start<end:
        if not start<=minute<end:return None
    elif minute>=start:pass
    elif minute<end:day-=timedelta(days=1)
    else:return None
    if day.weekday() not in settings['days']:return None
    return (day.isoformat(),start,end,settings['timezone'])

class ShowSchedule:
    def __init__(self,start_show,stop_show,path=None,clock=None):
        self.path=Path(path) if path else Path(os.environ.get('HNLS_SETTINGS_DIR','/share/.mlsc'))/'show_schedule.json'
        self.start_show=start_show;self.stop_show=stop_show;self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.lock=threading.RLock();self.last_key=None;self.seen=False;self.enabled_before=False;self.owned=False
        self.retry_after=0.;self.error='';self.message='Schedule disabled.';self.manual_state=None
    def load(self):
        try:return validate(json.loads(self.path.read_text()))
        except FileNotFoundError:return {**DEFAULT,'days':list(DEFAULT['days'])}
        except (OSError,ValueError,TypeError) as exc:raise ValueError('Cannot read show schedule: '+str(exc)) from exc
    def save(self,value):
        value=validate(value)
        with self.lock:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            tmp=self.path.with_name(self.path.name+'.'+str(os.getpid())+'.tmp')
            try:
                fd=os.open(str(tmp),os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600)
                with os.fdopen(fd,'w') as f:json.dump(value,f);f.flush();os.fsync(f.fileno())
                tmp.replace(self.path)
            finally:tmp.unlink(missing_ok=True)
            self.retry_after=0.
        self.tick()
        return self.view()
    def manual_message(self,settings,key):
        if self.manual_state=='stopped':
            return 'Show stopped manually. The saved schedule is unchanged; the next scheduled start can run normally.' if settings['enabled'] else 'Show stopped manually. Schedule is disabled.'
        if not settings['enabled']:
            return 'Manual show requested. Schedule is disabled; use Stop show when finished.'
        if key is not None:
            return 'Manual show requested. It will stop at the scheduled closing time. Saved hours are unchanged.'
        return 'Manual show requested outside show hours. Normal scheduled playback resumes at the next scheduled start. Saved hours are unchanged.'

    def play_now(self,filename=None):
        with self.lock:
            settings=self.load();key=window_key(settings,self.clock())
            try:
                started=self.start_show() if filename is None else self.start_show(filename=filename)
            except Exception:
                # Effects may already have been queued before playback failed.
                self.manual_state=None
                try:self.stop_show();self.owned=False
                except Exception:self.owned=True;self.last_key=None
                raise
            if started is False:
                raise ValueError('Upload at least one song before using Play now. For Spotify or Pandora, choose PC audio in Music.')
            self.manual_state='playing';self.owned=True;self.last_key=key
            self.seen=True;self.enabled_before=settings['enabled'];self.retry_after=0.;self.error=''
            self.message=self.manual_message(settings,key)
            return {**self.view(),'ok':True,'queued':True}

    def stop_now(self):
        with self.lock:
            # Stop remains available even if the saved schedule needs repair.
            self.stop_show()
            try:
                settings=self.load();key=window_key(settings,self.clock())
            except ValueError:
                settings=None;key=None
            self.manual_state='stopped';self.owned=False;self.last_key=key
            self.seen=True;self.enabled_before=bool(settings and settings['enabled']);self.retry_after=0.;self.error=''
            self.message=self.manual_message(settings,key) if settings else 'Show stopped manually. The saved schedule needs attention.'
            return {**self.view(),'ok':True,'queued':True}

    def tick(self,now=None):
        with self.lock:
            attempting_start=False;attempting_stop=False
            try:
                settings=self.load();now=now or self.clock();key=window_key(settings,now)
                if self.manual_state is not None and key!=self.last_key:
                    self.manual_state=None
                # Stop on closing boundary, disabling an owned show, or an enabled cold boot outside hours.
                must_stop=(self.owned and key!=self.last_key) or (settings['enabled'] and key is None and self.manual_state is None and (not self.seen or not self.enabled_before))
                if must_stop:
                    attempting_stop=True;self.stop_show();self.owned=False;self.last_key=None;attempting_stop=False
                if key is not None and key!=self.last_key:
                    if time.monotonic()<self.retry_after:return
                    attempting_start=True
                    if self.start_show() is False:
                        self.retry_after=time.monotonic()+30;self.message='Waiting for an uploaded song; retrying shortly.'
                    else:self.last_key=key;self.owned=True;self.manual_state=None;self.message='Scheduled show started. Manual controls remain available.'
                elif key is None:self.message='Outside show hours; scheduled lights are off.' if settings['enabled'] else 'Schedule disabled.'
                if self.manual_state is not None:self.message=self.manual_message(settings,key)
                self.seen=True;self.enabled_before=settings['enabled'];self.error=''
            except Exception as exc:
                self.error=str(exc);self.retry_after=time.monotonic()+30
                if attempting_start or (self.owned and not attempting_stop):
                    try:self.stop_show();self.owned=False;self.last_key=None
                    except Exception:self.owned=True;self.last_key=None
                # Failed stop boundaries remain owned and are retried on the next tick.
    def view(self):
        with self.lock:
            try:settings=self.load()
            except ValueError as exc:return {'settings':None,'error':str(exc),'message':self.message,'manual_state':self.manual_state}
            local=self.clock().astimezone(ZoneInfo(settings['timezone']))
            return {'settings':settings,'local_time':local.isoformat(timespec='seconds'),'in_window':window_key(settings,self.clock()) is not None,'message':self.message,'error':self.error,'manual_state':self.manual_state}

class ScheduleActions:
    """Use the same queues/effect controls as the web UI, including remote outputs."""
    def __init__(self,executer):self.executer=executer
    def release_studio(self):
        from libs.webserver.blueprints import studio_api
        if studio_api._runtime is not None:studio_api._runtime[2].stop()
    def start(self,filename=None):
        from libs.hnls_playlist import save_settings
        from libs.music_library import list_music_files
        import secrets
        songs=list_music_files()
        if not songs:return False
        if filename is not None and (not isinstance(filename,str) or filename not in {song['name'] for song in songs}):
            raise ValueError('Choose a song currently in the uploaded playlist.')
        self.release_studio()
        if filename is None:save_settings({'shuffle':True})
        self.executer.effect_executer.set_active_effect_for_all('effect_song_show')
        self.executer.music_library_executer.play(filename if filename is not None else secrets.choice(songs)['name'])
        return True
    def stop(self):
        self.release_studio()
        self.executer.effect_executer.set_active_effect_for_all('effect_off')
        self.executer.music_library_executer.stop()
