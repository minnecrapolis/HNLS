/* Everyday Home controls. Only explicit actions save settings or start playback. */
(function () {
    'use strict';
    const $=id=>document.getElementById(id);if(!$('home-controls'))return;
    let libraryBusy=false,seeking=false,signature=null,musicState={},snapshot=null;
    let lookDirty=false,brightnessDirty=false,lookBusy=false,loadedTarget='*',audioBusy=false,paletteChanged=false,modeChanged=false,shuffleBusy=false;
    async function api(url,data){
        const options={credentials:'same-origin',cache:'no-store'};
        if(data!==undefined){options.method='POST';if(data instanceof FormData)options.body=data;else{options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(data);}}
        const response=await fetch(url,options);let value;
        try{value=await response.json();}catch(_){throw Error('HNLS did not return a valid response. Try refreshing the page.');}
        if(!response.ok)throw Error(value.error||value.message||'Request failed ('+response.status+').');
        return value;
    }
    function notice(id,message){$(id).textContent=message;}
    function option(select,value,text){const node=document.createElement('option');node.value=value;node.textContent=text;select.append(node);}
    function clock(value){if(!Number.isFinite(value))return '—';const n=Math.max(0,Math.floor(value));return Math.floor(n/60)+':'+String(n%60).padStart(2,'0');}
    function updatePlayback(state){
        musicState=state||{};const active=!!state.file&&['playing','paused','between_songs'].includes(state.state);
        const labels={playing:'Playing',paused:'Paused',between_songs:'Next song in a moment',pc_stream:'Windows PC audio',pc_stream_waiting:'Waiting for Windows audio',microphone:'Microphone input',stopped:'Show stopped',error:'Playback needs attention'};
        notice('homeNowPlaying',(labels[state.state]||'Ready')+(state.file?': '+state.file:'')+(state.error?' — '+state.error:''));
        ['homePrevious','homePause','homeResume','homeNext','homeReplay'].forEach(id=>$(id).disabled=!active);
        $('homePause').hidden=state.state==='paused';$('homeResume').hidden=state.state!=='paused';
        const duration=typeof state.duration==='number'?state.duration:NaN;
        $('homeSeek').disabled=!active||!Number.isFinite(duration)||duration<=0;
        if(!seeking){$('homeSeek').max=duration>0?duration:1;$('homeSeek').value=state.position||0;}
        notice('homeTime',clock(Number(state.position||0))+' / '+clock(duration));
    }
    async function library(){
        if(libraryBusy)return;libraryBusy=true;
        try{
            const value=await api('/api/music/library');const files=value.files||[];const key=JSON.stringify(files.map(f=>f.name));
            if(signature!==key){
                const selected=$('homeSong').value||value.status?.file;
                $('homeSong').replaceChildren();if(!files.length)option($('homeSong'),'','Add songs below to get started');
                files.forEach(f=>option($('homeSong'),f.name,f.name));
                if(files.some(f=>f.name===selected))$('homeSong').value=selected;
                signature=key;$('homePlaySong').disabled=!files.length;
            }
            updatePlayback(value.status||{});
        }catch(error){notice('homeNowPlaying',error.message);}
        finally{libraryBusy=false;}
    }
    function bindMusic(id,url,data){$(id).addEventListener('click',async()=>{
        $(id).disabled=true;try{await api(url,typeof data==='function'?data():data);notice('homeMusicNotice','Requested.');}
        catch(error){notice('homeMusicNotice',error.message);}finally{$(id).disabled=false;window.setTimeout(library,400);}
    });}
    bindMusic('homePlaySong','/api/music/show-now',()=>({action:'play',file:$('homeSong').value}));
    for(const [id,action] of [['homePrevious','previous'],['homeNext','next'],['homeReplay','replay']])bindMusic(id,'/api/music/control',{action});
    bindMusic('homePause','/api/music/pause',{});bindMusic('homeResume','/api/music/resume',{});
    $('homeSeek').addEventListener('input',()=>{seeking=true;notice('homeTime',clock(Number($('homeSeek').value))+' / '+clock(Number(musicState.duration)));});
    $('homeSeek').addEventListener('change',async()=>{try{await api('/api/music/control',{action:'seek',seconds:Number($('homeSeek').value)});}catch(error){notice('homeMusicNotice',error.message);}finally{seeking=false;}});
    $('homeShuffle').addEventListener('change',async()=>{
        const value=$('homeShuffle').checked;shuffleBusy=true;$('homeShuffle').disabled=true;
        try{await api('/api/music/playlist-settings',{shuffle:value});notice('homeMusicNotice','Shuffle '+(value?'on':'off')+'. Takes effect at the next song transition.');}
        catch(error){$('homeShuffle').checked=!value;notice('homeMusicNotice',error.message);}finally{shuffleBusy=false;$('homeShuffle').disabled=false;}
    });
    $('homeUpload').addEventListener('click',async()=>{
        const files=Array.from($('homeUploadFiles').files||[]);if(!files.length){notice('homeMusicNotice','Choose one or more audio files first.');return;}
        $('homeUpload').disabled=true;$('homeUploadFiles').disabled=true;let uploaded=0;const errors=[];
        try{for(const file of files){notice('homeMusicNotice','Uploading '+file.name+'…');try{const form=new FormData();form.append('file',file);await api('/api/music/upload',form);uploaded++;}catch(error){errors.push(file.name+': '+error.message);}}}
        finally{$('homeUpload').disabled=false;$('homeUploadFiles').disabled=false;$('homeUploadFiles').value='';await library();notice('homeMusicNotice','Uploaded '+uploaded+' song'+(uploaded===1?'':'s')+'.'+(errors.length?' Could not upload: '+errors.join('; '):''));}
    });
    function selectedDevices(){return (snapshot?.devices||[]).filter(d=>$('homeLightTarget').value==='*'||d.id===$('homeLightTarget').value);}
    function common(devices,key){return devices.length&&devices.every(d=>d[key]===devices[0][key])?devices[0][key]:null;}
    function renderLook(keepLook=false,keepBrightness=false){
        const devices=selectedDevices();const available=devices.length>0;
        ['homePalette','homeMode','homeBrightnessValue'].forEach(id=>$(id).disabled=!available);
        if(!keepLook){
            const palette=common(devices,'palette'),mode=common(devices,'mode');
            $('homePalette').value=(snapshot?.palettes||[]).some(p=>p.id===palette)?palette:'';
            $('homeMode').value=['auto','classic'].includes(mode)?mode:'';lookDirty=false;paletteChanged=false;modeChanged=false;$('homeSaveLook').disabled=true;
        }
        if(!keepBrightness){const brightness=common(devices,'brightness');$('homeBrightnessValue').value=brightness===null?30:brightness;notice('homeBrightnessLabel',brightness===null?'Different per string':brightness+'%');brightnessDirty=false;$('homeSaveBrightness').disabled=true;}
        notice('homeLookSummary',available?(devices.length===1?devices[0].name:devices.length+' light strings')+'. Choose only the settings you want to replace.': 'Add a light string in My Lights to get started.');
    }
    async function loadLook(keepLook=false,keepBrightness=false){
        const value=await api('/api/music/home-look');const target=$('homeLightTarget').value||'*';snapshot=value;
        $('homeLightTarget').replaceChildren();option($('homeLightTarget'),'*','All lights');value.devices.forEach(d=>option($('homeLightTarget'),d.id,d.name));
        $('homeLightTarget').value=value.devices.some(d=>d.id===target)?target:'*';loadedTarget=$('homeLightTarget').value;$('homeLightTarget').disabled=!value.devices.length;
        const palette=$('homePalette').value,mode=$('homeMode').value;
        $('homePalette').replaceChildren();option($('homePalette'),'','Keep current colors');value.palettes.forEach(p=>option($('homePalette'),p.id,p.name));
        if(keepLook){$('homePalette').value=palette;$('homeMode').value=mode;}
        renderLook(keepLook,keepBrightness);
    }
    $('homeLightTarget').addEventListener('change',()=>{
        if((lookDirty||brightnessDirty)&&!window.confirm('Discard the unsaved Home color/effect/brightness choices and select another string?')){$('homeLightTarget').value=loadedTarget;return;}
        loadedTarget=$('homeLightTarget').value;renderLook();
    });
    function markLook(){lookDirty=true;$('homeSaveLook').disabled=false;}
    $('homePalette').addEventListener('change',()=>{paletteChanged=true;markLook();});$('homeMode').addEventListener('change',()=>{modeChanged=true;markLook();});
    $('homeBrightnessValue').addEventListener('input',()=>{brightnessDirty=true;notice('homeBrightnessLabel',$('homeBrightnessValue').value+'%');$('homeSaveBrightness').disabled=false;});
    async function saveLook(brightnessOnly){
        if(lookBusy)return;const data={target:$('homeLightTarget').value};const message=brightnessOnly?'homeBrightnessNotice':'homeLookNotice';
        if(brightnessOnly)data.brightness=Number($('homeBrightnessValue').value);
        else{if(paletteChanged&&$('homePalette').value)data.palette=$('homePalette').value;if(modeChanged&&$('homeMode').value)data.mode=$('homeMode').value;}
        if(Object.keys(data).length===1){notice(message,'Choose a replacement palette or effect mode first.');return;}
        lookBusy=true;['homeSaveLook','homeSaveBrightness','homeLightTarget','homePalette','homeMode','homeBrightnessValue'].forEach(id=>$(id).disabled=true);
        try{
            const result=await api('/api/music/home-look',data);
            notice(message,result.message+(result.failed?.length?' Needs attention: '+result.failed.map(d=>d.name+' — '+d.error).join('; '):' Use Play now when you want to start.'));
            if(result.ok){if(brightnessOnly){brightnessDirty=false;await loadLook(lookDirty,false);}else{lookDirty=false;paletteChanged=false;modeChanged=false;await loadLook(false,brightnessDirty);}}else{await loadLook(lookDirty,brightnessDirty);}
        }catch(error){notice(message,error.message);}
        finally{lookBusy=false;['homeLightTarget','homePalette','homeMode','homeBrightnessValue'].forEach(id=>$(id).disabled=!selectedDevices().length);$('homeSaveLook').disabled=!lookDirty;$('homeSaveBrightness').disabled=!brightnessDirty;}
    }
    $('homeSaveLook').addEventListener('click',()=>saveLook(false));$('homeSaveBrightness').addEventListener('click',()=>saveLook(true));
    async function loadAudio(){
        const value=await api('/api/music/audio-output');$('homeAudioMode').value=value.settings.mode;
        $('homeAudioDevice').replaceChildren();option($('homeAudioDevice'),'','Choose a saved speaker');
        (value.devices||[]).forEach(d=>option($('homeAudioDevice'),d.address,d.name||d.address));
        if(value.settings.address&&!value.devices?.some(d=>d.address===value.settings.address))option($('homeAudioDevice'),value.settings.address,value.settings.address);
        $('homeAudioDevice').value=value.settings.address||'';$('homeAudioMode').disabled=false;$('homeSaveAudio').disabled=false;$('homeAudioDevice').disabled=value.settings.mode!=='bluetooth';
    }
    $('homeAudioMode').addEventListener('change',()=>{$('homeAudioDevice').disabled=$('homeAudioMode').value!=='bluetooth';});
    $('homeSaveAudio').addEventListener('click',async()=>{
        if(audioBusy)return;audioBusy=true;['homeSaveAudio','homeAudioMode','homeAudioDevice'].forEach(id=>$(id).disabled=true);
        try{await api('/api/music/audio-output',{mode:$('homeAudioMode').value,address:$('homeAudioMode').value==='bluetooth'?$('homeAudioDevice').value:''});notice('homeAudioNotice','Speaker choice saved. Audio is reopening.');}
        catch(error){notice('homeAudioNotice',error.message+' Use speaker setup in Music if needed.');}
        finally{audioBusy=false;$('homeSaveAudio').disabled=false;$('homeAudioMode').disabled=false;$('homeAudioDevice').disabled=$('homeAudioMode').value!=='bluetooth';}
    });
    loadLook().catch(error=>notice('homeLookNotice',error.message));
    loadAudio().catch(error=>notice('homeAudioNotice',error.message));
    async function loadShuffle(){if(shuffleBusy)return;try{const value=await api('/api/music/playlist-settings');if(!shuffleBusy){$('homeShuffle').checked=value.shuffle;$('homeShuffle').disabled=false;}}catch(error){notice('homeMusicNotice',error.message);}}
    loadShuffle();window.setInterval(loadShuffle,5000);
    library();window.setInterval(library,1500);
}());
