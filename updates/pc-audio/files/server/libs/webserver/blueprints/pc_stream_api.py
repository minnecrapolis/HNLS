"""Web-login controlled LAN audio source and private Windows sender download."""
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
from libs.webserver.executer import Executer

pc_stream_api = Blueprint('pc_stream_api', __name__)


@pc_stream_api.get('/api/music/pc-stream')
@login_required
def status():
    from libs.music_library import read_status
    from libs.pc_stream import PORT
    value = read_status()
    return jsonify(state=value.get('state'), error=value.get('error'), port=PORT)


@pc_stream_api.post('/api/music/pc-stream')
@login_required
def control():
    from libs.pc_stream import credentials
    from libs.notification_enum import NotificationEnum
    from libs.notification_item import NotificationItem
    try:
        value = request.get_json(silent=True)
        if not isinstance(value, dict) or set(value) != {'action'} or value['action'] not in ('start', 'stop'):
            raise ValueError('Choose Start or Stop PC audio.')
        if value['action'] == 'start':
            credentials()
            from libs.show_schedule import ScheduleActions
            ScheduleActions(Executer.instance).release_studio()
            Executer.instance.effect_executer.set_active_effect_for_all('effect_song_show')
        Executer.instance.music_library_executer.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_play, 'all_devices', {'action': 'pc_stream_' + value['action']}))
        return jsonify(ok=True, queued=True)
    except (OSError, ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


@pc_stream_api.get('/api/music/pc-stream/sender')
@login_required
def sender():
    from libs.pc_stream import sender_bundle
    from urllib.parse import urlsplit
    try:
        host = urlsplit(request.url_root).hostname
        response = send_file(sender_bundle(host), mimetype='application/zip', as_attachment=True,
                             download_name='HNLS-PC-Audio.zip', max_age=0)
        response.headers['Cache-Control'] = 'no-store'
        return response
    except (OSError, ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
