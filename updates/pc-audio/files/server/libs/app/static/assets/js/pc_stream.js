(function () {
    'use strict';
    const start = document.getElementById('pcStreamStart'), stop = document.getElementById('pcStreamStop');
    const status = document.getElementById('pcStreamStatus');
    if (!start || !stop || !status) return;
    let busy = false;
    async function call(action) {
        if (busy) return;
        busy = true; start.disabled = true; stop.disabled = true;
        try {
            const response = await fetch('/api/music/pc-stream', {method:'POST', credentials:'same-origin',
                headers:{'Content-Type':'application/json'}, body:JSON.stringify({action})});
            const result = await response.json();
            if (!response.ok) throw Error(result.error || 'Could not select PC audio.');
            status.textContent = action === 'start' ? 'Requested. Start the downloaded Windows sender, then play Spotify or Pandora.' : 'Stop requested. Lights will turn off.';
        } catch (error) { status.textContent = error.message; }
        finally { busy = false; start.disabled = false; stop.disabled = false; }
    }
    start.addEventListener('click', () => call('start'));
    stop.addEventListener('click', () => call('stop'));
    async function poll() {
        try {
            const response = await fetch('/api/music/pc-stream', {credentials:'same-origin', cache:'no-store'});
            const value = await response.json();
            if (!response.ok) throw Error(value.error || 'PC audio status unavailable.');
            if (!busy) {
                const messages = {pc_stream:'Receiving Windows audio. Lights follow the live sound.',
                    pc_stream_waiting:'Waiting for Windows audio. Start the sender and play music; check Windows volume and playback device.'};
                status.textContent = value.error ? value.error : messages[value.state] || 'PC audio is not selected. Receiving PC audio replaces the uploaded-song player.';
            }
        } catch (error) { if (!busy) status.textContent = error.message; }
        window.setTimeout(poll, 2000);
    }
    poll();
}());
