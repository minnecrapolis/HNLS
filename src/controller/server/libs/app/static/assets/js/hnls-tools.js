/* A fixed remote toolbar: page selection targets its opener, never this window. */
(() => {
  'use strict';
  const destinations = [
    ['Home', '/'], ['Music', '/music'],
    ['Light Show', '/effects/effect_song_show'], ['Song Editor', '/song-designer'],
    ['My Lights', '/settings/device_settings'], ['Advanced', '/advanced']
  ];
  const allowed = new Set(destinations.map(item => item[1]));
  const isTools = new URLSearchParams(window.location.search).get('hnls_tools') === '1';
  if (!isTools) {
    window.addEventListener('message', event => {
      const data = event.data;
      if (event.origin !== window.location.origin || !data || data.type !== 'hnls:navigate' || !allowed.has(data.path)) return;
      window.location.assign(data.path);
    });
  }
  const workspace = document.getElementById('hnls-workspace');
  if (!workspace) return;
  if (isTools) {
    document.body.classList.add('hnls-tools-window');
    document.addEventListener('click', event => {
      const link=event.target.closest('a');
      if(!link)return;
      const url=new URL(link.href,window.location.href);
      if(url.origin!==window.location.origin||!allowed.has(url.pathname))return;
      event.preventDefault();
      if(window.opener&&!window.opener.closed)window.opener.postMessage({type:'hnls:navigate',path:url.pathname},window.location.origin);
    });
    workspace.innerHTML = '<section class="hnls-fixed-tools"><p class="hnls-kicker">YOUR SECOND-SCREEN TOOLBAR</p><h1>Control your main window</h1><p class="text-muted">Choose a page to open it in your main window.</p><div id="hnls-tool-pages" class="hnls-tool-pages"></div><p id="hnls-main-page" role="status"></p><section class="hnls-toolbar-transport"><p class="hnls-kicker">LIVE PLAYBACK</p><p id="hnls-tools-playback">Connecting…</p><div id="hnls-toolbar-buttons" class="hnls-toolbar-buttons"></div><p id="hnls-tool-feedback" role="status" aria-live="polite"></p></section></section>';
    const pages = document.getElementById('hnls-tool-pages');
    destinations.forEach(([name,path]) => {
      const button = document.createElement('button');
      button.type = 'button';button.textContent = name;button.dataset.path = path;
      button.addEventListener('click', () => {
        if (!window.opener || window.opener.closed) {
          document.getElementById('hnls-main-page').textContent = 'Main window is closed. Open HNLS and launch the toolbar there again.';return;
        }
        window.opener.postMessage({type:'hnls:navigate',path}, window.location.origin);
      });
      pages.append(button);
    });
    const controls = document.getElementById('hnls-toolbar-buttons');
    [['Previous','previous'],['−10 seconds','back'],['Pause','pause'],['Resume','resume'],['+10 seconds','forward'],['Replay','replay'],['Next','next']].forEach(([name,action]) => {
      const button=document.createElement('button');button.type='button';button.className='btn btn-outline-primary';button.textContent=name;
      button.addEventListener('click',async()=>{
        const feedback=document.getElementById('hnls-tool-feedback');
        if(window.HNLS_PREVIEW){feedback.textContent='Preview only. Playback controls connect to your Pi after installation.';return;}
        button.disabled=true;
        try{
          let endpoint='control',data={action};
          if(action==='pause'||action==='resume'){endpoint=action;data={};}
          if(action==='back'||action==='forward')data={action:'seek_relative',seconds:action==='back'?-10:10};
          const response=await fetch('/api/music/'+endpoint,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
          if(!response.ok){const result=await response.json();throw Error(result.error||'Playback command failed.');}
          feedback.textContent=name+' requested.';
        }catch(error){feedback.textContent=error.message;}finally{button.disabled=false;}
      });
      controls.append(button);
    });
  }
  let busy=false;
  const clock=seconds=>{const n=Math.max(0,Math.floor(Number(seconds)||0));return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');};
  async function poll(){
    if(busy)return;busy=true;
    try{
      if(isTools){
        let path;
        try{if(window.opener&&!window.opener.closed)path=window.opener.location.pathname;}catch(e){}
        if(path==='/dashboard')path='/';
        const match=destinations.find(d=>d[1]===path);
        document.getElementById('hnls-main-page').textContent=path?'Main window: '+(match?match[0]:path):'Main window unavailable. Launch the toolbar from HNLS again.';
        document.querySelectorAll('#hnls-tool-pages button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.path===path)));
      }
      if(window.HNLS_PREVIEW)return;
      const response=await fetch('/api/music/song-moments/playhead',{credentials:'same-origin'});
      if(!response.ok)throw Error('Playback status unavailable');
      const state=await response.json();
      const descriptions={playing:'Playing',paused:'Paused',between_songs:'Next song starts in a moment',pc_stream:'Windows PC audio',pc_stream_waiting:'Waiting for Windows audio',stopped:'Stopped',microphone:'Microphone input',error:'Playback needs attention'};
      const text=(descriptions[state.state]||'Audio status')+(state.file?' · '+state.file+' · '+clock(state.position)+' / '+clock(state.duration):'');
      for(const id of ['hnls-live-state','hnls-tools-playback']){const node=document.getElementById(id);if(node)node.textContent=text;}
    }catch(error){for(const id of ['hnls-live-state','hnls-tools-playback']){const node=document.getElementById(id);if(node)node.textContent='Connection unavailable — retrying…';}}
    finally{busy=false;}
  }
  poll();window.setInterval(poll,1000);
})();
