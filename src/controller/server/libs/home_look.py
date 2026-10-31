"""Small Home look controls; use existing executers and preserve unrelated settings."""
from libs.section_sync import validate_sync_settings
from libs.show_palettes import PALETTES


def view(config):
    return {'devices':[{'id':key,'name':d['device_name'],'brightness':d['led_brightness'],
                       'mode':d.get('effects',{}).get('effect_song_show',{}).get('show_mode','classic'),
                       'palette':d.get('effects',{}).get('effect_song_show',{}).get('palette_preset','custom')}
                      for key,d in config['device_configs'].items()], 'palettes':PALETTES}


def apply(data,executer):
    if not isinstance(data,dict) or set(data)-{'target','palette','mode','brightness'} or 'target' not in data:
        raise ValueError('Choose lights and at least one setting to change.')
    if len(data)<2:raise ValueError('Choose a color palette, effect mode or brightness first.')
    config=executer.effect_settings_executer._config
    target=data['target']
    if not isinstance(target,str):raise ValueError('Choose a light string or All lights.')
    ids=list(config['device_configs']) if target=='*' else [target]
    if not ids or any(key not in config['device_configs'] for key in ids):raise ValueError('Add or select an existing light string first.')
    patch={}
    if 'palette' in data:
        preset=next((p for p in PALETTES if p['id']==data['palette']),None)
        if preset is None:raise ValueError('Choose a holiday palette, or keep your current colors.')
        patch.update(preset['colors'],palette_preset=preset['id'],expanded_bands=True)
    if 'mode' in data:
        if data['mode'] not in ('auto','classic'):raise ValueError('Choose HNLS-selected effects or Classic.')
        patch['show_mode']=data['mode']
    if 'brightness' in data and (type(data['brightness']) is not int or not 0<=data['brightness']<=100):
        raise ValueError('Brightness must be a whole percent from 0 to 100.')
    # Validate every selected output before saving the first one. Only partial
    # settings are passed onward, so sync groups/limits/other colors stay local.
    if patch:
        for key in ids:
            d=config['device_configs'][key]
            validate_sync_settings(d['led_count'],{**d['effects'].get('effect_song_show',{}),**patch})
    applied=[];failed=[]
    for key in ids:
        name=config['device_configs'][key]['device_name']
        try:
            if patch:
                result=executer.effect_settings_executer.set_effect_settings(key,'effect_song_show',dict(patch))
                if not isinstance(result,dict):raise ValueError('Could not save this light string’s look.')
            if 'brightness' in data:
                result=executer.device_settings_executer.set_device_settings(key,{'led_brightness':data['brightness']})
                if not isinstance(result,dict):raise ValueError('Could not save this light string’s brightness.')
            applied.append({'id':key,'name':name})
        except Exception as exc:
            failed.append({'id':key,'name':name,'error':str(exc)[:240]})
    return {'ok':not failed,'applied':applied,'failed':failed,
            'message':'Saved for '+', '.join(d['name'] for d in applied)+'.' if applied else 'No light strings were updated.'}
