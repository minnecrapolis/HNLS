(function () {
    'use strict';
    function clock(seconds) {
        if (!Number.isFinite(seconds)) return '--:--';
        const total = Math.max(0, Math.floor(seconds));
        return Math.floor(total / 60) + ':' + String(total % 60).padStart(2, '0');
    }
    if (typeof module !== 'undefined') module.exports = {clock};
    if (typeof document === 'undefined') return;
    const $ = id => document.getElementById(id);
    let loading = false, seeking = false, status = {}, librarySignature = null;
    const controls = ['previousBtn', 'rewindBtn', 'replayBtn', 'forwardBtn', 'nextBtn', 'pauseBtn', 'resumeBtn'];
    function message(text, error = false) {
        $('musicStatus').textContent = text;
        $('musicStatus').className = 'alert ' + (error ? 'alert-danger' : 'alert-info');
    }
    async function request(url, data) {
        const options = {credentials: 'same-origin'};
        if (data !== undefined) {
            options.method = 'POST';
            if (data instanceof FormData) options.body = data;
            else { options.headers = {'Content-Type': 'application/json'}; options.body = JSON.stringify(data); }
        }
        const response = await fetch(url, options);
        const result = await response.json();
        if (!response.ok) throw Error(result.error || 'Music request failed.');
        return result;
    }
    function updateStatus(value) {
        status = value || {};
        const state = status.state || 'microphone';
        const texts = {playing: 'Playing: ', paused: 'Paused: ', between_songs: 'Lights off — two-second pause after: '};
        message(state === 'error' ? 'Playback error: ' + (status.error || 'unknown error') :
            texts[state] ? texts[state] + (status.file || 'music file') :
            state === 'stopped' ? 'Playlist stopped. All lights off.' : 'Audio source: Microphone', state === 'error');
        if (status.error && state !== 'error') message('Audio output error: ' + status.error, true);
        const active = ['playing', 'paused', 'between_songs'].includes(state) && !!status.file;
        controls.forEach(id => $(id).disabled = !active);
        const duration = Number(status.duration);
        $('musicSeek').disabled = !active || !Number.isFinite(duration) || duration <= 0;
        $('musicTime').textContent = clock(Number(status.position || 0)) + ' / ' + clock(duration > 0 ? duration : NaN);
        if (!seeking) { $('musicSeek').max = duration > 0 ? duration : 1; $('musicSeek').value = status.position || 0; }
    }
    function button(label, callback, style) {
        const el = document.createElement('button'); el.type = 'button';
        el.className = 'btn btn-sm mr-2 ' + (style || 'btn-primary'); el.textContent = label;
        el.addEventListener('click', async () => {
            el.disabled = true;
            try { await callback(); } catch (error) { message(error.message, true); }
            finally { el.disabled = false; }
        });
        return el;
    }
    async function loadLibrary() {
        if (loading) return;
        loading = true;
        try {
            const result = await request('/api/music/library');
            const body = $('musicList');
            const signature = JSON.stringify((result.files || []).map(f => [f.name, f.size, f.modified]));
            if (signature !== librarySignature) {
            body.replaceChildren();
            (result.files || []).forEach(file => {
                const row = document.createElement('tr'); row.className = 'music-row'; row.dataset.file = file.name;
                const name = document.createElement('td'); name.className = 'music-name';
                const playName = button(file.name, () => command('/api/music/play', {file: file.name}), 'btn-link text-left hnls-song-link');
                playName.setAttribute('aria-label', 'Play ' + file.name); name.append(playName);
                const size = document.createElement('td'); size.textContent = (file.size / 1048576).toFixed(2) + ' MB';
                const actions = document.createElement('td'); actions.className = 'text-right';
                actions.append(button('Play', () => command('/api/music/play', {file: file.name})),
                    button('Delete', async () => {
                        if (!confirm('Delete "' + file.name + '" from the playlist? It will be moved to the music trash folder. If it is playing, the next song will start after the two-second pause.')) return;
                        await command('/api/music/control', {action: 'delete', file: file.name});
                    }, 'btn-outline-danger'));
                row.append(name, size, actions); body.append(row);
            });
            if (!(result.files || []).length) {
                const row = document.createElement('tr'), cell = document.createElement('td'); cell.colSpan = 3;
                cell.textContent = 'No music files yet. Upload one above.'; row.append(cell); body.append(row);
            }
            librarySignature = signature;
            }
            for (const row of body.children) row.classList.toggle('active', row.dataset.file === result.status?.file);
            updateStatus(result.status);
        } catch (error) { message(error.message, true); }
        finally { loading = false; }
    }
    async function command(url, data = {}) {
        await request(url, data);
        window.setTimeout(loadLibrary, 800);
    }
    function bind(id, url, data) {
        $(id).addEventListener('click', async () => {
            $(id).disabled = true;
            try { await command(url, data); } catch (error) { message(error.message, true); }
            finally { $(id).disabled = false; }
        });
    }
    bind('previousBtn', '/api/music/control', {action: 'previous'});
    bind('nextBtn', '/api/music/control', {action: 'next'});
    bind('replayBtn', '/api/music/control', {action: 'replay'});
    bind('rewindBtn', '/api/music/control', {action: 'seek_relative', seconds: -10});
    bind('forwardBtn', '/api/music/control', {action: 'seek_relative', seconds: 10});
    bind('pauseBtn', '/api/music/pause'); bind('resumeBtn', '/api/music/resume'); bind('stopBtn', '/api/music/stop');
    $('musicSeek').addEventListener('input', () => {
        seeking = true;
        $('musicTime').textContent = clock(Number($('musicSeek').value)) + ' / ' + clock(Number(status.duration));
    });
    $('musicSeek').addEventListener('change', async () => {
        try { await command('/api/music/control', {action: 'seek', seconds: Number($('musicSeek').value)}); }
        catch (error) { message(error.message, true); }
        finally { seeking = false; }
    });
    $('uploadBtn').addEventListener('click', async () => {
        const input = $('musicFile');
        if (!input.files?.length) { message('Choose an audio file first.'); return; }
        $('uploadBtn').disabled = true; $('uploadProgress').classList.remove('d-none');
        try { const data = new FormData(); data.append('file', input.files[0]); await request('/api/music/upload', data); input.value = ''; await loadLibrary(); }
        catch (error) { message(error.message, true); }
        finally { $('uploadBtn').disabled = false; $('uploadProgress').classList.add('d-none'); }
    });
    let bluetoothBusy = false, bluetoothPolling = false, audioLoaded = false;
    const bluetoothButtons = ['enableBluetooth','scanBluetooth','pairBluetooth','connectBluetooth','disconnectBluetooth'];
    async function loadAudioOutput() {
        if (bluetoothPolling) return;
        bluetoothPolling = true;
        try {
            const result = await request('/api/music/audio-output');
            if (!audioLoaded) { $('audioOutputMode').value = result.settings.mode; audioLoaded = true; }
            const selected = $('bluetoothDevice').value || result.settings.address;
            $('bluetoothDevice').replaceChildren();
            const initial = document.createElement('option'); initial.value = ''; initial.textContent = 'Select a device'; $('bluetoothDevice').append(initial);
            const devices = result.devices || [];
            if (result.settings.address && !devices.some(d => d.address === result.settings.address)) devices.push({address:result.settings.address,name:'Saved speaker'});
            devices.forEach(device => { const el = document.createElement('option'); el.value = device.address; el.textContent = device.name + ' · ' + device.address; $('bluetoothDevice').append(el); });
            $('bluetoothDevice').value = selected || '';
            bluetoothBusy = !!result.job.running;
            bluetoothButtons.forEach(id => $(id).disabled = bluetoothBusy);
            $('bluetoothStatus').textContent = (result.job.error || result.job.message || result.error || 'Audio backend: ' + result.backend) + (bluetoothBusy ? ' Please wait…' : '');
        } catch (error) { $('bluetoothStatus').textContent = error.message; }
        finally { bluetoothPolling = false; }
    }
    async function bluetooth(action) {
        if (bluetoothBusy) return;
        if (action === 'setup' && !confirm('Enable Bluetooth audio support? Required system packages may be installed from the internet. An existing desktop audio stack will be reused.')) return;
        bluetoothBusy = true; bluetoothButtons.forEach(id => $(id).disabled = true);
        try { await request('/api/music/bluetooth', {action,address:$('bluetoothDevice').value}); await loadAudioOutput(); }
        catch (error) { bluetoothBusy = false; bluetoothButtons.forEach(id => $(id).disabled = false); $('bluetoothStatus').textContent = error.message; }
    }
    for (const [id, action] of [['enableBluetooth','setup'],['scanBluetooth','scan'],['pairBluetooth','pair'],['connectBluetooth','connect'],['disconnectBluetooth','disconnect']]) $(id).addEventListener('click', () => bluetooth(action));
    $('saveAudioOutput').addEventListener('click', async () => {
        $('saveAudioOutput').disabled = true;
        try {
            const data = {mode:$('audioOutputMode').value,address:$('bluetoothDevice').value};
            await request('/api/music/audio-output', data);
            $('bluetoothStatus').textContent = 'Audio output saved. Playback will switch at the current song position.';
        } catch (error) { $('bluetoothStatus').textContent = error.message; }
        finally { $('saveAudioOutput').disabled = false; }
    });
    loadAudioOutput(); window.setInterval(() => { if (bluetoothBusy) loadAudioOutput(); }, 2000);
    loadLibrary(); window.setInterval(loadLibrary, 1000);
})();
