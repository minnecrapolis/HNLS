from flask import Blueprint, jsonify, request
from flask_login import login_required
from werkzeug.utils import secure_filename

from libs.music_library import ensure_music_dir, is_supported, safe_music_path
from libs.webserver.executer import Executer


music_library_api = Blueprint("music_library_api", __name__)


@music_library_api.get("/api/music/library")
@login_required
def music_library():
    return jsonify(Executer.instance.music_library_executer.get_library())


@music_library_api.post("/api/music/upload")
@login_required
def music_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    upload = request.files["file"]
    filename = secure_filename(upload.filename or "")
    if not filename or not is_supported(filename):
        return jsonify({"error": "Unsupported audio format"}), 400

    ensure_music_dir()
    destination = safe_music_path(filename)
    upload.save(destination)
    # HNLS prepare uploaded song without blocking the upload response.
    try:
        from libs.hnls_playlist import start_preparation
        start_preparation()
    except OSError:
        pass
    return jsonify({"ok": True, "file": filename})


@music_library_api.post("/api/music/play")
@login_required
def music_play():
    data = request.get_json(silent=True) or {}
    filename = data.get("file")
    try:
        return jsonify(Executer.instance.music_library_executer.play(filename))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except FileNotFoundError:
        return jsonify({"error": "Music file not found"}), 404


@music_library_api.post("/api/music/pause")
@login_required
def music_pause():
    return jsonify(Executer.instance.music_library_executer.pause())


@music_library_api.post("/api/music/resume")
@login_required
def music_resume():
    return jsonify(Executer.instance.music_library_executer.resume())


@music_library_api.post("/api/music/stop")
@login_required
def music_stop():
    return jsonify(Executer.instance.music_library_executer.stop())


@music_library_api.post('/api/music/control')
@login_required
def music_control():
    try:
        return jsonify(Executer.instance.music_library_executer.control(request.get_json(silent=True)))
    except (ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Music file not found'}), 404


@music_library_api.get('/api/music/audio-output')
@login_required
def audio_output_get():
    from libs.audio_output import state
    return jsonify(state())


@music_library_api.post('/api/music/audio-output')
@login_required
def audio_output_set():
    from libs.audio_output import save_settings
    from libs.notification_enum import NotificationEnum
    from libs.notification_item import NotificationItem
    try:
        selected = save_settings(request.get_json(silent=True))
        Executer.instance.music_library_executer.notification_queue_out.put(
            NotificationItem(NotificationEnum.music_play, 'all_devices', {'action':'output_changed'}))
        return jsonify({'ok':True,'settings':selected})
    except (OSError,ValueError,TypeError) as exc:
        return jsonify({'error':str(exc)}),400


@music_library_api.post('/api/music/bluetooth')
@login_required
def bluetooth_action():
    from libs.audio_output import start_job
    try:
        return jsonify(start_job(request.get_json(silent=True)))
    except (ValueError,OSError) as exc:
        return jsonify({'error':str(exc)}),400


@music_library_api.get('/api/music/song-moments')
@login_required
def song_moments_get():
    from libs.song_moments import read
    from libs.music_library import list_music_files,read_status
    import subprocess,json,math
    filename=request.args.get('file','')
    duration=None
    try:
        if filename:
            path=safe_music_path(filename)
            if not path.is_file():raise ValueError('Choose an uploaded song')
            status=read_status()
            if status.get('file')==filename:duration=status.get('duration')
            if not duration:
                result=subprocess.run(['/usr/bin/ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,timeout=3,check=False)
                try:duration=float(json.loads(result.stdout)['format']['duration'])
                except (ValueError,KeyError,TypeError):duration=None
            if duration is not None and (not math.isfinite(float(duration)) or not 0<float(duration)<=86400):duration=None
        config=Executer.instance.music_library_executer._config
        return jsonify(files=list_music_files(),file=filename,duration=duration,current_file=read_status().get('file'),
            cues=[c for c in read()['cues'] if c['file']==filename],regions=read().get('regions',[]),
            outputs=[{'id':k,'name':d['device_name'],'count':d['led_count']} for k,d in config['device_configs'].items()])
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        return jsonify(error=str(exc)),400


@music_library_api.post('/api/music/song-moments')
@login_required
def song_moment_save():
    from libs.song_moments import save_moment
    try:
        cue=save_moment(request.get_json(silent=True),Executer.instance.music_library_executer._config)
        return jsonify(ok=True,cue=cue)
    except (ValueError,OSError,TypeError) as exc:
        return jsonify(error=str(exc)),400


@music_library_api.delete('/api/music/song-moments')
@login_required
def song_moment_delete():
    from libs.song_moments import delete_moment
    try:
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise ValueError('Choose a saved moment')
        return jsonify(delete_moment(data.get('id')))
    except (ValueError,OSError) as exc:
        return jsonify(error=str(exc)),400


@music_library_api.get('/api/music/song-moments/playhead')
@login_required
def song_moment_playhead():
    from libs.music_library import read_status
    return jsonify(read_status())


@music_library_api.post('/api/music/song-regions')
@login_required
def song_region_save():
    from libs.song_moments import save_region
    try:
        return jsonify(ok=True,region=save_region(request.get_json(silent=True),Executer.instance.music_library_executer._config))
    except (ValueError,OSError,TypeError) as exc:
        return jsonify(error=str(exc)),400


@music_library_api.delete('/api/music/song-regions')
@login_required
def song_region_delete():
    from libs.song_moments import delete_region
    try:
        data=request.get_json(silent=True)
        if not isinstance(data,dict):raise ValueError('Choose a named light group')
        return jsonify(delete_region(data.get('id')))
    except (ValueError,OSError) as exc:
        return jsonify(error=str(exc)),400


@music_library_api.get('/api/music/show-preparation')
@login_required
def hnls_show_preparation():
    from libs.hnls_playlist import profile_summary
    return jsonify(profile_summary())


@music_library_api.post('/api/music/show-preparation')
@login_required
def hnls_prepare_library():
    from libs.hnls_playlist import start_preparation
    try:
        return jsonify(start_preparation())
    except OSError:
        return jsonify({'error':'Could not start analysis. Try again after checking free memory and storage.'}),503


@music_library_api.post('/api/music/playlist-settings')
@login_required
def hnls_playlist_settings():
    from libs.hnls_playlist import save_settings
    try:
        return jsonify(save_settings(request.get_json(silent=True)))
    except (ValueError,TypeError) as exc:
        return jsonify({'error':str(exc)}),400
