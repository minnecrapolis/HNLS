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
