"""Persistent physical RGB wire-order overrides on inclusive device LED ranges."""
import json,os,re,threading,time
from pathlib import Path
import numpy as np
ORDERS=('RGB','RBG','GRB','GBR','BRG','BGR')
LOCK=threading.RLock();CACHE={'at':-1.,'stamp':None,'devices':{}}
def path():return Path(os.environ.get('HNLS_SETTINGS_DIR','/share/.mlsc'))/'color_ranges.json'
def base_order(config):
    strip=config.get('led_strip','')
    match=re.fullmatch(r'ws2811_strip_([rgb]{3})',strip)
    if match and match.group(1).upper() in ORDERS:return match.group(1).upper()
    if strip=='ws2812_strip' and config.get('output_type')=='output_raspi':
        # Resolve the native alias from the installed driver's constants rather
        # than guessing its byte order. Importing constants does not open GPIO.
        try:
            import _rpi_ws281x as ws
            value=getattr(ws,'WS2812_STRIP',None)
            if value is not None:
                return next((order for order in ORDERS if getattr(ws,'WS2811_STRIP_'+order,None)==value),None)
        except ImportError:pass
    return None

def normalize(rows,count):
    if not isinstance(rows,list) or len(rows)>100:raise ValueError('Use at most 100 color-order ranges per output')
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)-{'first','last','order','name'}:raise ValueError('Expected first, last, order and optional name')
        first,last,order=row.get('first'),row.get('last'),row.get('order')
        if type(first) is not int or type(last) is not int or not 1<=first<=last<=count:raise ValueError('LED ranges must be inside this output, starting at LED 1')
        if order not in ORDERS:raise ValueError('Choose RGB, RBG, GRB, GBR, BRG or BGR')
        name=row.get('name','')
        if not isinstance(name,str) or len(name)>60:raise ValueError('Range name must be at most 60 characters')
        result.append({'first':first,'last':last,'order':order,'name':name.strip()})
    result.sort(key=lambda x:x['first'])
    if any(a['last']>=b['first'] for a,b in zip(result,result[1:])):raise ValueError('Color-order ranges cannot overlap; leave gaps to inherit the default order')
    return result

def read():
    try:data=json.loads(path().read_text())
    except FileNotFoundError:return {'version':1,'devices':{}}
    if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('devices'),dict):raise ValueError('Unsupported color-range settings')
    return data

def cached():
    now=time.monotonic()
    if CACHE['at']<0 or now-CACHE['at']>=.25:
        CACHE['at']=now
        try:
            p=path();stamp=(p.stat().st_mtime_ns,p.stat().st_size) if p.exists() else None
            if stamp!=CACHE['stamp']:
                data=read();safe={}
                for key,rows in data['devices'].items():
                    try:safe[key]=normalize(rows,2**63-1)
                    except (ValueError,TypeError):continue
                CACHE.update(stamp=stamp,devices=safe)
        except (ValueError,OSError,TypeError):pass
    return CACHE['devices']

def save(device,rows,config):
    outputs=config['device_configs']
    if not isinstance(device,str) or device not in outputs:raise ValueError('Choose an existing output')
    output=outputs[device]
    if output.get('output_type') not in ('output_raspi','output_udp'):raise ValueError('This output backend does not support RGB range mapping')
    if rows and not base_order(output):raise ValueError('First choose an explicit RGB/GRB/RBG/GBR/BRG/BGR strip type for this output in Device Settings; unresolved aliases and RGBW are not supported')
    rows=normalize(rows,output['led_count'])
    with LOCK:
        data=read();data['devices'][device]=rows;write(data)
    return rows


def write(data):
    p=path();p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    try:
        fd=os.open(str(tmp),os.O_CREAT|os.O_WRONLY|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
        tmp.replace(p)
    finally:tmp.unlink(missing_ok=True)
    CACHE['at']=-1.


def forget(device):
    with LOCK:
        data=read()
        if device in data['devices']:
            del data['devices'][device];write(data)


def view(config):
    document=read();result=[]
    for key,d in config['device_configs'].items():
        rows=document['devices'].get(key,[]);error=''
        try:rows=normalize(rows,d['led_count'])
        except (ValueError,TypeError) as exc:error=str(exc)
        result.append({'id':key,'name':d['device_name'],'count':d['led_count'],'base_order':base_order(d),'strip_type':d.get('led_strip'),'supported':base_order(d) is not None and d.get('output_type') in ('output_raspi','output_udp'),'ranges':rows,'error':error})
    return {'outputs':result,'orders':list(ORDERS)}

def apply(frame,device_id,config):
    rows=cached().get(device_id,[])
    if not rows:return frame
    order=base_order(config);count=frame.shape[1];result=None
    for row in rows:
        lo=max(0,min(count,row['first']-1));hi=max(0,min(count,row['last']))
        if hi<=lo:continue
        if order is not None and frame.shape[0]==3 and row['order']==order:continue
        if result is None:result=np.array(frame,copy=True)
        if order is None or frame.shape[0]!=3:
            result[:,lo:hi]=0
            continue
        # Driver still applies P (the output default). Precompensate by P^-1 Q
        # so physical bytes match Q (the selected segment's actual wiring).
        indices=['RGB'.index(row['order'][order.index(channel)]) for channel in 'RGB']
        result[:3,lo:hi]=frame[indices,lo:hi]
    return frame if result is None else result
