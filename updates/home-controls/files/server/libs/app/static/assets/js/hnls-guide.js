/* Task navigation only. Searching/opening sections never changes playback/settings. */
(function () {
    'use strict';
    const destinations = [
        {name:'Play the full show now', detail:'Home · manual start outside scheduled hours', url:'/#hnlsPlayNowPanel', words:'manual override schedule play now start show'},
        {name:'Play an uploaded song', detail:'Home · song choice, play, pause, next and replay', url:'/#homeMusic', words:'mp3 library music playback skip rewind'},
        {name:'Add songs', detail:'Home · upload files to your playlist', url:'/#homeUploadFiles', words:'upload mp3 collection add'},
        {name:'Play Spotify or Pandora from Windows', detail:'Home · PC sender download and live audio', url:'/#homePcSource', words:'stream spotify pandora windows pc audio sender'},
        {name:'Choose a holiday palette', detail:'Home · Christmas, Halloween and other colors', url:'/#homeLook', words:'holiday palette colors christmas halloween thanksgiving easter'},
        {name:'Let HNLS choose the effects', detail:'Home · automatic music effects', url:'/#homeMode', words:'automatic analysis effects motion choreography'},
        {name:'Change individual music colors', detail:'Light Show · bass, treble and eight frequency bands', url:'/effects/effect_song_show#band-colors', words:'bass frequency audio treble power color bands'},
        {name:'Choose which sections move together', detail:'Light Show · matching groups and mirrors', url:'/effects/effect_song_show#section-groups', words:'mirror sync synchronize group sections paired independent'},
        {name:'Limit how many LEDs light up', detail:'Light Show · normal coverage and POWER exception', url:'/effects/effect_song_show#light-limit', words:'maximum density limit power coverage leds'},
        {name:'Edit one part of a song', detail:'Song Editor · select a time, lights and effect', url:'/song-designer', words:'moment timeline strobe flash scroll seconds custom tree'},
        {name:'Change brightness', detail:'Home · all lights or one string', url:'/#homeBrightness', words:'dim brightness light level'},
        {name:'Change LED count or string name', detail:'My Lights · choose a string and edit its settings', url:'/settings/device_settings#string-settings', words:'device string count name settings'},
        {name:'Fix RGB / GRB colors', detail:'My Lights · correct color order for LED ranges', url:'/settings/device_settings#colorRangesPanel', words:'rgb grb wrong colors orange green order ranges'},
        {name:'Add another string on this Pi', detail:'My Lights · GPIO output setup', url:'/settings/device_settings#gpioStringsPanel', words:'gpio output second third string pin'},
        {name:'Add a second Pi', detail:'My Lights · pair a remote Pi', url:'/settings/device_settings#remotePiPanel', words:'slave remote network pair second pi'},
        {name:'Set automatic start and stop times', detail:'Home · schedule days and show hours', url:'/#homeHours', words:'schedule hours timer start stop nightly'},
        {name:'Choose speakers or Bluetooth', detail:'Home · headphone jack and wireless speakers', url:'/#homeSound', words:'sound audio output jack headphones bluetooth speaker'},
        {name:'Analyze the playlist', detail:'Music · prepare songs for an automatic show', url:'/music#song-analysis', words:'analysis analyze scan tempo prepare shuffle'},
        {name:'Advanced tools', detail:'Advanced · sequence imports, studio and network timing', url:'/advanced', words:'falcon xlights fseq advanced studio sequence import offset'}
    ];
    function search(text) {
        const tokens = String(text).trim().toLowerCase().split(/\s+/).filter(Boolean);
        return destinations.filter(item => tokens.every(t => (item.name+' '+item.detail+' '+item.words).toLowerCase().includes(t)));
    }
    function reveal(document, hash) {
        let id; try {id=decodeURIComponent((hash||'').replace(/^#/,''));} catch (_) {return false;}
        if (!id) return false;
        const target=document.getElementById(id); if(!target) return false;
        let parent=target;
        while(parent) {if(parent.tagName==='DETAILS') parent.open=true;parent=parent.parentElement;}
        target.scrollIntoView({behavior:'auto',block:'start'});
        if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex','-1');
        target.focus({preventScroll:true});return true;
    }
    if (typeof module!=='undefined') module.exports={search,reveal,destinations};
    if (typeof document==='undefined') return;
    const dialog=document.getElementById('hnls-find-dialog'),input=document.getElementById('hnls-find-input'),results=document.getElementById('hnls-find-results');
    let opener=null;
    function close(){if(dialog.close)dialog.close();else dialog.removeAttribute('open');if(opener)opener.focus();}
    function showResults(){
        results.replaceChildren();const matches=search(input.value);
        document.getElementById('hnls-find-count').textContent=matches.length ? matches.length+' places to go' : 'No matches. Try colors, song, Bluetooth, GPIO or schedule.';
        matches.forEach(item=>{const a=document.createElement('a');a.href=item.url;const title=document.createElement('strong'),detail=document.createElement('span');title.textContent=item.name;detail.textContent=item.detail;a.append(title,detail);a.addEventListener('click',()=>close());results.append(a);});
    }
    if(dialog && input && results){
        document.querySelectorAll('[data-hnls-find]').forEach(button=>button.addEventListener('click',()=>{
            opener=button;input.value='';showResults();if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');input.focus();
        }));
        document.getElementById('hnls-find-close').addEventListener('click',close);input.addEventListener('input',showResults);
        dialog.addEventListener('cancel',()=>{if(opener)opener.focus();});
    }
    const names={'/':'Home','/dashboard':'Home','/music':'Music','/effects/effect_song_show':'Light Show','/song-designer':'Song Editor','/settings/device_settings':'My Lights','/advanced':'Advanced'};
    const crumb=document.getElementById('hnls-current-place');if(crumb)crumb.textContent=names[window.location.pathname]||'Advanced settings';
    document.querySelectorAll('[data-hnls-jump]').forEach(a=>a.addEventListener('click',()=>{
        try{const hash=new URL(a.href,window.location.href).hash;reveal(document,hash);}catch(_){}
    }));
    window.addEventListener('hashchange',()=>reveal(document,window.location.hash));
    if(window.location.hash)window.setTimeout(()=>reveal(document,window.location.hash),0);
    // My Lights fills its primary form asynchronously. Follow an intentional
    // deep link after that form becomes visible, so it cannot push the target away.
    const panel=document.getElementById('deviceFound');
    if(panel && window.location.hash && typeof MutationObserver!=='undefined') {
        const observer=new MutationObserver(()=>{
            if(!panel.classList.contains('d-none')) {observer.disconnect();reveal(document,window.location.hash);}
        });
        observer.observe(panel,{attributes:true,attributeFilter:['class']});
        window.setTimeout(()=>observer.disconnect(),5000);
    }

}());
