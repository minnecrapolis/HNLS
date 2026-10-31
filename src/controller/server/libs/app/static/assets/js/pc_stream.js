(function () {
    'use strict';
    const $ = id => document.getElementById(id);
    const start = $('pcStreamStart'), stop = $('pcStreamStop'), local = $('pcLocalStart');
    const status = $('pcStreamStatus');
    if (!start || !stop || !status) return;
    let busy = false, generation = 0, pending = null;
    function render(state) {
        const streaming = state === 'pc_stream' || state === 'pc_stream_waiting';
        if (document.querySelectorAll) document.querySelectorAll('[data-hnls-local-controls]').forEach(node => { node.hidden = streaming; });
        const panel = $('hnlsPlayNowPanel'); if (panel) panel.hidden = streaming;
        if (local) local.setAttribute('aria-pressed', String(!streaming));
        start.setAttribute('aria-pressed', String(streaming));
        stop.disabled = busy || !streaming;
    }
    async function call(action) {
        if (busy) return;
        generation++; busy = true; start.disabled = true; stop.disabled = true; if (local) local.disabled = true;
        try {
            const response = await fetch(action === 'local' ? '/api/music/show-now' : '/api/music/pc-stream', {method:'POST', credentials:'same-origin',
                headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:action === 'local' ? 'play' : action})});
            const result = await response.json();
            if (!response.ok) throw Error(result.error || 'Could not change music source.');
            pending = {streaming:action === 'start', until:Date.now()+8000};
            render(action === 'start' ? 'pc_stream_waiting' : 'stopped');
            status.textContent = action === 'start' ? 'PC stream requested. Open Start-HNLS-Audio.cmd on Windows, then play Spotify or Pandora. Sound plays through your Pi speaker.' :
                action === 'local' ? 'Pi playlist requested. The PC stream will stop; songs on the Pi will play on shuffle.' : 'Stop requested. Pi sound and lights will stop. Spotify may keep playing on Windows.';
        } catch (error) { status.textContent = error.message; }
        finally { busy = false; start.disabled = false; if (local) local.disabled = false; if (!pending) stop.disabled = false; else stop.disabled = !pending.streaming; }
    }
    start.addEventListener('click', () => call('start'));
    stop.addEventListener('click', () => call('stop'));
    if (local) local.addEventListener('click', () => call('local'));
    async function poll() {
        if (busy) { window.setTimeout(poll, 2000); return; }
        const stamp = generation;
        try {
            const response = await fetch('/api/music/pc-stream', {credentials:'same-origin', cache:'no-store'});
            const value = await response.json();
            if (!response.ok) throw Error(value.error || 'Music source status unavailable.');
            if (!busy && stamp === generation) {
                const streaming = ['pc_stream','pc_stream_waiting'].includes(value.state);
                if (pending && pending.streaming !== streaming && Date.now() < pending.until) return;
                pending = null; render(value.state);
                const messages = {pc_stream:'Receiving Windows audio. Playing through the Pi speaker; lights follow the live sound.',
                    pc_stream_waiting:'Waiting for Windows audio. Open the sender and play music; check Windows volume and playback device.'};
                status.textContent = value.error || messages[value.state] || 'PC stream is off. Choose Play songs on the Pi, or select a song below.';
            }
        } catch (error) { if (!busy && stamp === generation) status.textContent = error.message; }
        finally { window.setTimeout(poll, 2000); }
    }
    poll();
}());
