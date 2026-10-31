(function(){
'use strict';
const $=id=>document.getElementById(id);if(!$('songMomentsPanel'))return;
const canvas=$('momentTimeline'),ctx=canvas.getContext('2d');
let regions=[],editingRegion=null,cues=[],outputs=[],selected=null,duration=300,drag=null,loadedFile='',playback={},pollBusy=false;
const message=(s,error=false)=>{$('momentStatus').textContent=s;$('momentStatus').className='small my-3 '+(error?'text-danger':'text-muted');};
function time(s){let m=Math.floor(s/60),v=(s-m*60).toFixed(3).replace(/\.?0+$/,'');if(v==='')v='0';return m+':'+(Number(v)<10?'0':'')+v;}
function seconds(s){const parts=s.trim().split(':');if(parts.length===1&&/^\d+(\.\d+)?$/.test(parts[0]))return Number(parts[0]);if(parts.length===2&&/^\d+$/.test(parts[0])&&/^\d{1,2}(\.\d+)?$/.test(parts[1])&&Number(parts[1])<60)return Number(parts[0])*60+Number(parts[1]);throw Error('Use m:ss, for example 3:04.200');}
async function request(method='GET',data){const r=await fetch('/api/music/song-moments'+(method==='GET'&&$('momentSong').value?'?file='+encodeURIComponent($('momentSong').value):''),{method,credentials:'same-origin',...(data?{headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{})});const body=await r.json();if(!r.ok)throw Error(body.error||'Song-moment request failed');return body;}
function choices(){const all=$('momentAll').checked;$('momentTargets').querySelectorAll('input').forEach(c=>c.disabled=all);drawPixels();}
function bounds(){return [seconds($('momentStart').value),seconds($('momentEnd').value)];}
function syncDuration(){try{const [a,b]=bounds();$('momentDuration').value=Number((b-a).toFixed(3));}catch(e){}}
function draw(){
 canvas.height=Math.max(220,70+cues.length*29);ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#202b23';ctx.fillRect(0,0,canvas.width,canvas.height);
 const x=t=>30+t/duration*(canvas.width-60),tick=duration>900?120:duration>300?60:duration>120?30:10;
 ctx.font='12px system-ui';ctx.textAlign='center';for(let t=0;t<=duration;t+=tick){ctx.strokeStyle='#45523e';ctx.beginPath();ctx.moveTo(x(t),27);ctx.lineTo(x(t),canvas.height-15);ctx.stroke();ctx.fillStyle='#c6d2bc';ctx.fillText(time(t),x(t),18);}
 try{const [a,b]=bounds();ctx.fillStyle='#d5e96930';ctx.fillRect(x(a),28,Math.max(1,x(b)-x(a)),canvas.height-43);ctx.strokeStyle='#d5e969';ctx.strokeRect(x(a),28,Math.max(2,x(b)-x(a)),canvas.height-43);}catch(e){}
 cues.forEach((c,i)=>{const y=46+i*29;ctx.fillStyle=c.id===selected?'#d5e969':c.color;ctx.fillRect(x(c.start),y,Math.max(3,x(c.end)-x(c.start)),19);ctx.fillStyle='#edf3e5';ctx.textAlign='left';const label=time(c.start)+'–'+time(c.end)+' · '+c.effect.replace('_',' ');const labelX=x(c.end)+7;ctx.fillText(label,Math.min(labelX,canvas.width-ctx.measureText(label).width-8),y+14);});
 if(playback.file===loadedFile&&Number.isFinite(playback.position)){ctx.strokeStyle='#ff9c64';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x(playback.position),25);ctx.lineTo(x(playback.position),canvas.height);ctx.stroke();ctx.lineWidth=1;}
}
function form(c){selected=c?.id||null;$('momentRegion').value=c?.region||'';editingRegion=c?.region||null;$('momentRegionDelete').disabled=!editingRegion;const region=regions.find(r=>r.id===editingRegion);$('momentRegionName').value=region?.name||'';$('momentDelete').disabled=!selected;
 if(c){$('momentStart').value=time(c.start);$('momentEnd').value=time(c.end);$('momentEffect').value=c.effect;$('momentBrightness').value=c.brightness;$('momentColor').value=c.color;$('momentColor2').value=c.color2;$('momentUseColor2').checked=c.use_color2??['color_scroll','color_blocks','twinkle'].includes(c.effect);$('momentSpeed').value=c.speed;$('momentCycle').value=c.cycle_seconds??defaultPeriod(c.effect);$('momentWidth').value=c.band_width??8;$('momentDirection').value=c.direction??'forward';$('momentAll').checked=c.targets.includes('*');$('momentFirst').value=c.first;$('momentLast').value=c.last??'';$('momentReserve').checked=c.reserve;$('momentTargets').querySelectorAll('input').forEach(x=>x.checked=c.targets.includes(x.value));}
 $('momentSave').textContent=selected?'Update moment':'Save moment';syncDuration();choices();draw();effectHelp();conflicts();editorState(c);}
function editorState(c){
 $('momentEditorHeading').textContent=c?'Edit this moment':'Build the effect';
 $('momentEditingInfo').textContent=c?'Editing '+time(c.start)+'–'+time(c.end)+' · '+c.effect.replace(/_/g,' ')+' · LEDs '+c.first+'–'+(c.last??'end')+'. Change the controls, then click Update moment.':'New moment — select its time, LEDs and effect.';
 for(const row of $('momentList').children){const active=row.dataset.momentId===selected;row.classList.toggle('table-active',active);row.setAttribute('aria-selected',String(active));}
}
function editMoment(c){
 try{
  if(!c||!c.id)throw Error('This moment could not be found. Refresh songs & moments, then try again.');
  form(c);$('momentFineTune').open=true;
  const reduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  $('momentEditor').scrollIntoView({behavior:reduced?'auto':'smooth',block:'start'});
  $('momentEffect').focus({preventScroll:true});
  message('Moment opened for editing. Change its controls, then click Update moment.');
 }catch(e){message('Could not open this moment: '+e.message+' Try Ctrl+F5 to reload the editor.',true);}
}
function list(){
 $('momentList').replaceChildren();cues.forEach(c=>{const row=document.createElement('tr');row.dataset.momentId=c.id;for(const value of [time(c.start)+'–'+time(c.end),c.effect.replace('_',' '),(c.targets.includes('*')?'All strings':c.targets.map(id=>outputs.find(o=>o.id===id)?.name||id).join(', '))+' · LEDs '+c.first+'–'+(c.last??'end')]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}const cell=document.createElement('td'),button=document.createElement('button');button.type='button';button.className='btn btn-sm btn-outline-primary';button.textContent='Edit';button.setAttribute('aria-label','Edit moment '+time(c.start)+' to '+time(c.end));button.addEventListener('click',()=>editMoment(c));cell.append(button);row.append(cell);$('momentList').append(row);});
}
async function load(){
 $('momentSave').disabled=true;
 try{const data=await request();const wanted=$('momentSong').value||data.current_file;$('momentSong').replaceChildren();data.files.forEach(f=>{const option=document.createElement('option');option.value=f.name;option.textContent=f.name;$('momentSong').append(option);});if(data.files.some(f=>f.name===wanted))$('momentSong').value=wanted;
 if(data.file!==$('momentSong').value&&$('momentSong').value)return await load();loadedFile=data.file;cues=data.cues;outputs=data.outputs;regions=data.regions||[];regionOptions();
 duration=data.duration||Math.max(300,...cues.map(c=>c.end));$('momentLength').value=duration.toFixed(3);$('momentTargets').replaceChildren();outputs.forEach(o=>{const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.value=o.id;input.addEventListener('change',()=>{$('momentRegion').value='';drawPixels();});label.append(input,document.createTextNode(' '+o.name+' · '+o.count+' LEDs'));$('momentTargets').append(label);});
 list();form(null);if(cues.length)form(cues[0]);message(loadedFile?'Drag across the timeline to create a moment, or click a saved block.':'Upload a song first.');$('momentSave').disabled=!loadedFile||!outputs.length;
 }catch(e){message(e.message,true);}
}
function at(event){const rect=canvas.getBoundingClientRect();return {time:Math.max(0,Math.min(duration,((event.clientX-rect.left)/rect.width*canvas.width-30)/(canvas.width-60)*duration)),y:(event.clientY-rect.top)/rect.height*canvas.height};}
canvas.addEventListener('pointerdown',e=>{const point=at(e),row=Math.floor((point.y-46)/29),cue=cues[row];if(point.y>=46&&cue&&point.time>=cue.start-.5&&point.time<=cue.end+.5){editMoment(cue);return;}drag=point.time;selected=null;$('momentDelete').disabled=true;$('momentSave').textContent='Save moment';editorState(null);canvas.setPointerCapture(e.pointerId);$('momentStart').value=time(drag);$('momentEnd').value=time(Math.min(duration,drag+1));syncDuration();draw();});
canvas.addEventListener('pointermove',e=>{if(drag===null)return;const t=at(e).time;const a=Math.round(Math.min(t,drag)*10)/10,b=Math.round(Math.max(t,drag)*10)/10;$('momentStart').value=time(a);$('momentEnd').value=time(Math.min(duration,Math.max(a+.1,b)));syncDuration();draw();});
canvas.addEventListener('pointerup',()=>{drag=null;});canvas.addEventListener('pointercancel',()=>{drag=null;});
$('momentSong').addEventListener('change',()=>{selected=null;load();});$('momentReload').onclick=load;$('momentAll').onchange=()=>{$('momentRegion').value='';choices();};
$('momentLength').onchange=()=>{const n=Number($('momentLength').value);if(Number.isFinite(n)&&n>0&&n<=86400){duration=n;draw();}};
['momentStart','momentEnd'].forEach(id=>$(id).addEventListener('change',()=>{try{bounds();syncDuration();draw();}catch(e){message(e.message,true);}}));
function defaultPeriod(effect){return {flash:.5,color_scroll:8,color_blocks:8,chase:8,comet:8,bounce:8,pulse:4,twinkle:1.2,rainbow:12,wipe:8}[effect]??6;}
function effectHelp(){
 const effect=$('momentEffect').value,two=$('momentUseColor2').checked,moving=['color_scroll','color_blocks','chase','comet','bounce','rainbow','wipe'].includes(effect);
 $('momentColor').disabled=effect==='blackout'||(effect==='rainbow'&&!two);$('momentColor2').disabled=['solid','blackout'].includes(effect);$('momentUseColor2').disabled=['solid','blackout'].includes(effect);
 $('momentCycle').disabled=['solid','blackout'].includes(effect);$('momentWidth').disabled=!['color_scroll','color_blocks','chase','comet','bounce','rainbow'].includes(effect);$('momentDirection').disabled=!moving;
 const details={color_scroll:'Smooth two-color blend. Increase the cycle time to slow it down.',color_blocks:'Sharp two-color bands for a more prominent scroll. Start with 8 seconds and a width of 8 LEDs.',chase:'A moving block of Color 1; the rest of the range uses the chosen background.',comet:'A moving Color 1 head fades into the chosen background.',bounce:'A light travels to the end of the selected range and back.',pulse:'One gradual fade up and down per cycle.',twinkle:'Deterministic colored sparkles on black, synchronized to the song position.',rainbow:'A saturated rainbow moves along the selected range.',wipe:'Your color fills the selected range, then the cycle starts again.',flash:'One on/off flash per cycle. Larger numbers flash more slowly.',solid:'Your selected LEDs remain this color for the whole moment.',blackout:'Your selected LEDs remain off for the whole moment.'};
 const colorHelp={flash:'With two colors: alternate Color 1 and Color 2. Use black for on/off flashes.',bounce:'Color 1 bounces over Color 2. Black keeps the background dark.',comet:'Color 1 fades into a Color 2 background. Black gives a dark trail.',chase:'Color 1 moves over Color 2. Black keeps gaps dark.',pulse:'Fade between Color 2 and Color 1. Black gives a brightness pulse.',wipe:'Color 1 fills a Color 2 background, then repeats.',rainbow:'Checked: scroll only the two chosen colors. Unchecked: use the full rainbow.',twinkle:'Two sparkle colors on black. Uncheck to use only Color 1.',color_scroll:'Blend the chosen colors. Uncheck to scroll Color 1 over black.',color_blocks:'Alternate the chosen colors. Uncheck to use Color 1 and black.'};
 $('momentColor2Help').textContent=colorHelp[effect]||'This effect uses only the first color.';
 $('momentEffectHelp').textContent=details[effect]||'';
 if(two&&['chase','comet','bounce','pulse','wipe'].includes(effect))$('momentEffectHelp').textContent+=' Color 2 is the background / fade color.';
 if(effect==='rainbow'&&two)$('momentEffectHelp').textContent='Two-color palette scroll; uncheck Use second color for the full rainbow.';
}
function conflicts(){
 try{const [start,end]=bounds(),targets=$('momentAll').checked?['*']:Array.from($('momentTargets').querySelectorAll('input:checked')).map(x=>x.value),first=Number($('momentFirst').value),last=$('momentLast').value===''?Infinity:Number($('momentLast').value);
 const overlap=cues.filter(c=>c.id!==selected&&c.start<end&&start<c.end&&first<=(c.last??Infinity)&&c.first<=last&&(targets.includes('*')||c.targets.includes('*')||c.targets.some(t=>targets.includes(t))));
 $('momentConflictHelp').textContent=overlap.length?overlap.length+' other saved moment(s) overlap these LEDs and times. Later rows take priority; edit or remove the overlap to show only this effect.':'';
 }catch(e){$('momentConflictHelp').textContent='';}
}
$('momentEffect').addEventListener('change',()=>{$('momentCycle').value=defaultPeriod($('momentEffect').value);$('momentUseColor2').checked=true;effectHelp();});
$('momentUseColor2').addEventListener('change',effectHelp);
$('momentColor2').addEventListener('input',()=>{$('momentUseColor2').checked=true;effectHelp();});
$('momentColor2').addEventListener('change',()=>{$('momentUseColor2').checked=true;effectHelp();});
$('momentReserve').addEventListener('change',()=>message('Reservation changes only the selected range. Click Save moment to apply; playback does not restart.'));
for(const id of ['momentStart','momentEnd','momentFirst','momentLast','momentAll','momentTargets','momentRegion'])$(id).addEventListener('change',conflicts);
effectHelp();
$('momentNew').onclick=()=>{form(null);message('Drag a new time span, then choose its lights and effect.');};
$('momentSave').onclick=async()=>{try{if(!loadedFile||loadedFile!==$('momentSong').value)throw Error('Load the selected song first');const [start,end]=bounds();$('momentSave').disabled=true;const targets=$('momentAll').checked?['*']:Array.from($('momentTargets').querySelectorAll('input:checked')).map(c=>c.value);const result=await request('POST',{id:selected,region:$('momentRegion').value||null,file:loadedFile,start,end,effect:$('momentEffect').value,color:$('momentColor').value,color2:$('momentColor2').value,use_color2:$('momentUseColor2').checked,speed:Number($('momentSpeed').value),cycle_seconds:Number($('momentCycle').value),band_width:Number($('momentWidth').value),direction:$('momentDirection').value,brightness:Number($('momentBrightness').value),targets,first:Number($('momentFirst').value),last:$('momentLast').value===''?null:Number($('momentLast').value),reserve:$('momentReserve').checked});const index=cues.findIndex(c=>c.id===result.cue.id);if(index>=0)cues[index]=result.cue;else cues.push(result.cue);list();form(result.cue);message('Saved. This moment will run whenever this song plays.');}catch(e){message(e.message,true);}finally{$('momentSave').disabled=!loadedFile;}};
$('momentDelete').onclick=async()=>{if(!selected||!confirm('Delete this saved light moment?'))return;try{await request('DELETE',{id:selected});cues=cues.filter(c=>c.id!==selected);list();form(null);message('Moment deleted.');}catch(e){message(e.message,true);}};

const pixelCanvas=$('momentPixelMap'),pixelCtx=pixelCanvas.getContext('2d');let pixelAnchor=null;
function oneOutput(){if($('momentAll').checked)return null;const chosen=Array.from($('momentTargets').querySelectorAll('input:checked'));return chosen.length===1?outputs.find(o=>o.id===chosen[0].value):null;}
function drawPixels(){
 const o=oneOutput();pixelCtx.fillStyle='#202b23';pixelCtx.fillRect(0,0,1200,95);pixelCtx.font='13px system-ui';pixelCtx.textAlign='left';pixelCtx.fillStyle='#cad6c1';
 if(!o){pixelCtx.fillText('Choose one string above to highlight an LED range.',25,52);$('momentPixelHelp').textContent='All strings or multiple strings can still use the number fields. For a visual LED selection, uncheck Every configured string and select one string.';return;}
 const first=Math.max(1,Number($('momentFirst').value)||1),last=$('momentLast').value===''?o.count:Number($('momentLast').value);pixelCtx.fillText(o.name+' · '+o.count+' addressable LEDs',25,23);pixelCtx.fillStyle='#526149';pixelCtx.fillRect(25,37,1150,23);pixelCtx.fillStyle='#d5e969';pixelCtx.fillRect(25+(first-1)/o.count*1150,37,Math.max(1,(Math.min(last,o.count)-first+1)/o.count*1150),23);pixelCtx.fillStyle='#cad6c1';pixelCtx.fillText('1',25,82);pixelCtx.textAlign='right';pixelCtx.fillText(String(o.count),1175,82);$('momentPixelHelp').textContent='Selected LEDs '+first+'–'+last+' on '+o.name+'. Drag the bar to change this range; number fields give exact boundaries.';
}
function pixelAt(e){const o=oneOutput();if(!o)return null;const rect=pixelCanvas.getBoundingClientRect();return Math.max(1,Math.min(o.count,Math.floor((((e.clientX-rect.left)/rect.width*1200)-25)/1150*o.count)+1));}
pixelCanvas.addEventListener('pointerdown',e=>{const n=pixelAt(e);if(n===null)return;pixelAnchor=n;pixelCanvas.setPointerCapture(e.pointerId);$('momentRegion').value='';$('momentFirst').value=n;$('momentLast').value=n;drawPixels();});
pixelCanvas.addEventListener('pointermove',e=>{if(pixelAnchor===null)return;const n=pixelAt(e);if(n===null)return;$('momentRegion').value='';$('momentFirst').value=Math.min(n,pixelAnchor);$('momentLast').value=Math.max(n,pixelAnchor);drawPixels();});
pixelCanvas.addEventListener('pointerup',()=>pixelAnchor=null);pixelCanvas.addEventListener('pointercancel',()=>pixelAnchor=null);
['momentFirst','momentLast'].forEach(id=>$(id).addEventListener('change',()=>{$('momentRegion').value='';drawPixels();}));
$('momentDuration').addEventListener('change',()=>{try{const a=seconds($('momentStart').value),span=Number($('momentDuration').value);if(!Number.isFinite(span)||span<.1||span>3600)throw Error('Choose a duration between 0.1 and 3600 seconds');$('momentEnd').value=time(a+span);draw();}catch(e){message(e.message,true);}});


async function transport(path,data={}){const response=await fetch('/api/music/'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Music command failed');return result;}
async function poll(){if(pollBusy||document.hidden)return;pollBusy=true;try{const response=await fetch('/api/music/song-moments/playhead',{credentials:'same-origin'});if(!response.ok)return;playback=await response.json();$('momentPlayhead').textContent=playback.file===loadedFile?(playback.state+' · '+time(Number(playback.position)||0)+' / '+time(Number(playback.duration)||duration)):'The selected song is not currently playing.';draw();}catch(e){}finally{pollBusy=false;}}
async function pauseMark(which){
 try{if(playback.file!==loadedFile||!['playing','paused'].includes(playback.state))throw Error('Play the selected song first.');await transport('pause');
 const until=Date.now()+3000;let status;
 do{const response=await fetch('/api/music/song-moments/playhead',{credentials:'same-origin'});if(!response.ok)throw Error('Cannot read music position');status=await response.json();if(status.file!==loadedFile)throw Error('The song changed before marking; select the current song.');if(status.state==='paused')break;await new Promise(r=>setTimeout(r,100));}while(Date.now()<until);
 if(status.state!=='paused')throw Error('Playback has not paused yet. Try marking again.');
 playback=status;const position=Math.round(Number(status.position)*1000)/1000;
 if(which==='start'){$('momentStart').value=time(position);$('momentEnd').value=time(position+Math.max(.1,Number($('momentDuration').value)||2));}else{if(position<=seconds($('momentStart').value))throw Error('Play past the start marker before marking the end.');$('momentEnd').value=time(position);}
 syncDuration();draw();message('Song paused. '+(which==='start'?'Start':'End')+' marked at '+time(position)+'.');
 }catch(e){message(e.message,true);}
}
$('momentPlay').onclick=async()=>{try{if(!loadedFile)throw Error('Choose a song first');await transport('play',{file:loadedFile});message('Starting the selected song. Use Pause + mark start when you hear the moment.');}catch(e){message(e.message,true);}};
$('momentResume').onclick=async()=>{try{if(playback.file!==loadedFile)throw Error('Play the selected song first');await transport('resume');message('Resuming. Pause + mark end at the end of your moment.');}catch(e){message(e.message,true);}};
$('momentMarkStart').onclick=()=>pauseMark('start');$('momentMarkEnd').onclick=()=>pauseMark('end');
$('momentSeek').onclick=async()=>{try{if(playback.file!==loadedFile||!['playing','paused'].includes(playback.state))throw Error('Play the selected song first');await transport('control',{action:'seek',seconds:seconds($('momentStart').value)});message('Seeking to the start of your selection. If paused, use Resume song to hear it.');}catch(e){message(e.message,true);}};
poll();window.setInterval(poll,300);


function regionOptions(){const old=$('momentRegion').value;$('momentRegion').replaceChildren();const option=document.createElement('option');option.value='';option.textContent='Choose LEDs manually / all lights';$('momentRegion').append(option);regions.forEach(r=>{const o=document.createElement('option');o.value=r.id;o.textContent=r.name;$('momentRegion').append(o);});$('momentRegion').value=old;}
function chooseRegion(){const r=regions.find(r=>r.id===$('momentRegion').value);editingRegion=r?.id||null;$('momentRegionDelete').disabled=!r;if(!r)return;$('momentRegionName').value=r.name;$('momentAll').checked=false;$('momentTargets').querySelectorAll('input').forEach(c=>c.checked=c.value===r.device);$('momentFirst').value=r.first;$('momentLast').value=r.last;choices();}
async function regionRequest(method,data){const response=await fetch('/api/music/song-regions',{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Light-group request failed');return result;}
$('momentRegion').onchange=chooseRegion;
$('momentRegionNew').onclick=()=>{editingRegion=null;$('momentRegion').value='';$('momentRegionName').value='';$('momentRegionDelete').disabled=true;message('Name the current LED range to create a separate light group.');};
$('momentRegionSave').onclick=async()=>{try{const o=oneOutput();if(!o)throw Error('Select exactly one string before naming this LED range');const name=$('momentRegionName').value.trim(),old=regions.find(r=>r.id===editingRegion);const groupId=old&&old.name.toLowerCase()===name.toLowerCase()?editingRegion:null;const result=await regionRequest('POST',{id:groupId,name,device:o.id,first:Number($('momentFirst').value),last:$('momentLast').value===''?o.count:Number($('momentLast').value)});const i=regions.findIndex(r=>r.id===result.region.id);if(i<0)regions.push(result.region);else regions[i]=result.region;regionOptions();$('momentRegion').value=result.region.id;chooseRegion();cues.forEach(c=>{if(c.region===result.region.id){c.targets=[result.region.device];c.first=result.region.first;c.last=result.region.last;}});list();message('Light group saved. Choose '+result.region.name+' from the list for any song.');}catch(e){message(e.message,true);}};
$('momentRegionDelete').onclick=async()=>{if(!editingRegion||!confirm('Delete this group name? Existing song moments keep their saved LED ranges.'))return;try{await regionRequest('DELETE',{id:editingRegion});regions=regions.filter(r=>r.id!==editingRegion);cues.forEach(c=>{if(c.region===editingRegion)c.region=null;});editingRegion=null;regionOptions();$('momentRegion').value='';$('momentRegionDelete').disabled=true;message('Group name deleted. Saved song moments retain their LED ranges.');}catch(e){message(e.message,true);}};

load();
})();
