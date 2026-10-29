(function(){
'use strict';
const apiRoot='/api/studio';
function id(){return Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');}
function newProject(output){return {id:id(),name:'New show',media:'',asset:'',duration_ms:180000,frame_ms:40,audio_device:'headphones',audio_offset_ms:0,groups:{},outputs:[{...output}],cues:[],loop:false};}
function seconds(value){
 const text=String(value).trim();
 if(!/^(?:\d+(?:\.\d+)?|\d+:\d{2}(?:\.\d+)?|\d+:\d{2}:\d{2}(?:\.\d+)?)$/.test(text))throw Error('Use seconds or a time such as 2:53 or 2:53.500.');
 const parts=text.split(':').map(Number);
 if(parts.length>1&&parts.slice(1).some(v=>v>=60))throw Error('Minutes and seconds after a colon must be below 60.');
 return parts.reduce((total,part)=>total*60+part,0);
}
function moveCue(cue,delta,duration,frame,edge='move'){
 const step=Math.max(1,frame),snap=v=>Math.round(v/step)*step,end=cue.start_ms+cue.duration_ms;
 if(edge==='start'){const start=Math.max(0,Math.min(end-1,snap(cue.start_ms+delta)));return {...cue,start_ms:start,duration_ms:end-start};}
 if(edge==='end')return {...cue,duration_ms:Math.max(1,Math.min(duration-cue.start_ms,snap(end+delta)-cue.start_ms))};
 return {...cue,start_ms:Math.max(0,Math.min(duration-cue.duration_ms,snap(cue.start_ms+delta)))};
}
function cueFromFields(values){const start=seconds(values.start),duration=String(values.end??'').trim()?seconds(values.end)-start:seconds(values.duration);return {id:values.id||id(),target:values.target,start_ms:Math.round(start*1000),duration_ms:Math.round(duration*1000),effect:values.effect,color:values.color,intensity:Number(values.intensity),period_ms:Number(values.period),power:!!values.power};}
if(typeof module!=='undefined')module.exports={newProject,cueFromFields,seconds,moveCue};
if(typeof document==='undefined')return;
document.addEventListener('DOMContentLoaded',async()=>{
const $=name=>document.getElementById(name);
if(!$('studioProjects'))return;
let wizardStep=1,wizardLine=0,layoutIndex=0,layoutDrag=null,cueDrag=null,suppressTimelineClick=false,previewColors=null;
let config,project,dirty=false,previewing=false,previewStart=0,previewBusy=false,previewAgain=false,lastPreview=0,lastPaused=false;
const message=(text,error=false)=>{$('studioMessage').textContent=text;$('studioMessage').className='alert studio-message mt-3 '+(error?'alert-danger':'alert-info');};
const mark=()=>{dirty=true;$('studioSaved').textContent='Unsaved changes';};
async function api(route,data,method){const options={credentials:'same-origin',method:method||(data===undefined?'GET':'POST')};if(data!==undefined){if(data instanceof FormData)options.body=data;else{options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(data);}}const response=await fetch(route.startsWith('/api/')?route:apiRoot+route,options);const result=await response.json();if(!response.ok)throw Error(result.error||`Request failed (${response.status})`);return result;}
function action(name,fn){$(name).addEventListener('click',async()=>{const button=$(name);button.disabled=true;try{await fn();}catch(error){message(error.message,true);}finally{button.disabled=false;}});}
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o;}
function fillList(){const current=project?.id;$('studioProjects').replaceChildren(option('','Choose a saved show'));config.projects.forEach(p=>$('studioProjects').append(option(p.id,p.name)));if(current)$('studioProjects').value=current;}
function renderMusic(){const value=project?.media||'';$('showMedia').replaceChildren(option('','No audio'));config.music.forEach(f=>$('showMedia').append(option(f.name,f.name)));$('showMedia').value=value;}
function readForm(){project.name=$('showName').value;project.media=$('showMedia').value;project.duration_ms=Math.round(Number($('showDuration').value)*1000);project.frame_ms=Number($('showFrame').value);project.audio_device=$('showAudio').value;project.audio_offset_ms=Number($('audioOffset').value);project.loop=$('showLoop').checked;}
function setAudio(){const audio=$('studioAudioPreview');audio.pause();audio.src=project.media?apiRoot+'/media/'+encodeURIComponent(project.media):'';}
function renderProject(){
 $('showName').value=project.name;renderMusic();$('showDuration').value=project.duration_ms/1000;$('showFrame').value=project.frame_ms;$('showAudio').value=project.audio_device;$('audioOffset').value=project.audio_offset_ms;$('showLoop').checked=project.loop;
 $('studioScrub').max=project.duration_ms;$('studioScrub').value=0;setAudio();renderOutputs();renderCues();renderGroups();resetCue();renderWizard();renderLayout();drawTimeline();refreshPreview();$('studioImportInfo').textContent=project.asset?'Imported FSEQ is the base layer. Cue overlays can change or blackout individual LEDs.':'Create cues here or import a rendered .fseq file from xLights / Falcon Player.';
 dirty=false;$('studioSaved').textContent='Loaded';fillList();
}
async function save(){readForm();const response=await api('/projects',project);project=response.project;renderOutputs();renderCues();renderGroups();renderWizard();renderLayout();dirty=false;$('studioSaved').textContent='Saved';config.projects=config.projects.filter(p=>p.id!==project.id);config.projects.push({id:project.id,name:project.name});fillList();return project;}
function button(text,callback,style='btn-outline-secondary'){const b=document.createElement('button');b.type='button';b.className='btn btn-sm '+style;b.textContent=text;b.addEventListener('click',()=>{try{callback();}catch(e){message(e.message,true);}});return b;}
function cell(text){const td=document.createElement('td');td.textContent=text;return td;}
function renderCues(){
 const body=$('studioCues');body.replaceChildren();
 project.cues.forEach((cue,index)=>{const row=document.createElement('tr');row.append(cell(cue.target),cell((cue.start_ms/1000).toFixed(3)),cell((cue.duration_ms/1000).toFixed(3)),cell(cue.effect+(cue.power?' · POWER':'')));const color=cell(cue.color);color.style.borderLeft='8px solid '+cue.color;row.append(color);const actions=document.createElement('td');actions.append(button('Edit',()=>editCue(cue)),button('↑',()=>{if(index){[project.cues[index-1],project.cues[index]]=[project.cues[index],project.cues[index-1]];mark();renderCues();refreshPreview();}}),button('Delete',()=>{project.cues.splice(index,1);mark();renderCues();refreshPreview();},'btn-outline-danger'));row.append(actions);body.append(row);});drawTimeline();
}
function resetCue(){$('cueId').value='';$('cueEnd').value='';}
function editCue(c){$('cueId').value=c.id;$('cueTarget').value=c.target;$('cueStart').value=c.start_ms/1000;$('cueDuration').value=c.duration_ms/1000;$('cueEnd').value=(c.start_ms+c.duration_ms)/1000;$('cueEffect').value=c.effect;$('cueColor').value=c.color;$('cueIntensity').value=c.intensity;$('cuePeriod').value=c.period_ms;$('cuePower').checked=c.power;}
function renderGroups(){const root=$('studioGroups'),list=$('studioGroupNames');root.replaceChildren();list.replaceChildren();Object.entries(project.groups).forEach(([name,targets])=>{list.append(option('@'+name,'@'+name));const entry=document.createElement('div');entry.append(button(name+' · '+targets,()=>{$('groupName').value=name;$('groupTargets').value=targets;}),button('×',()=>{if(project.cues.some(c=>c.target==='@'+name))throw Error('Change or remove the cues using this group first.');delete project.groups[name];mark();renderGroups();}));root.append(entry);});}
function renderOutputs(){
 const body=$('studioOutputs'),preview=$('studioPreviewOutput');const old=preview.value;body.replaceChildren();preview.replaceChildren();
 project.outputs.forEach((out,index)=>{
  preview.append(option(index,out.name));const row=document.createElement('tr');
  const fields=['enabled','name','node','gpio','count','first_pixel','fps','offset_ms','brightness','order','max_lit'];
  fields.forEach(key=>{const td=document.createElement('td');let input;
   if(['node','gpio','order'].includes(key)){input=document.createElement('select');if(key==='node'){input.append(option('local','This Pi'));config.nodes.forEach(n=>input.append(option(n.id,n.name)));}else if(key==='gpio'){[21,10,18,13,12,19].forEach(n=>input.append(option(n,'GPIO '+n)));}else ['GRB','RGB','RBG','GBR','BRG','BGR'].forEach(n=>input.append(option(n,n)));}
   else{input=document.createElement('input');input.type=key==='enabled'?'checkbox':key==='name'?'text':'number';if(key==='enabled')input.checked=out[key];if(['count','first_pixel','fps'].includes(key))input.min=1;if(key==='offset_ms')input.step=1;}
   input.className='form-control form-control-sm'+(['name','node'].includes(key)?' wide':'');input.setAttribute('aria-label',`${out.name} ${key}`);if(key!=='enabled')input.value=out[key];input.addEventListener('change',()=>{out[key]=key==='enabled'?input.checked:['name','node','order'].includes(key)?input.value:Number(input.value);mark();if(key==='name')preview.options[index].textContent=out.name;renderLayout();drawTimeline();refreshPreview();});td.append(input);row.append(td);
  });const actions=document.createElement('td');actions.append(button('Test',async()=>{try{await save();await api('/play',{project:project.id,test_output:index});message('Output test scheduled. Normal playback resumes after the test.');}catch(e){message(e.message,true);}}),button('Remove',()=>{project.outputs.splice(index,1);mark();renderOutputs();renderLayout();renderWizard();},'btn-outline-danger'));row.append(actions);body.append(row);
 });preview.value=old||'0';if(!preview.value&&project.outputs.length)preview.value='0';
}
function drawTimeline(){if(!project)return;const canvas=$('studioTimeline');canvas.height=Math.max(120,50+project.cues.length*24);const ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#101c2c';ctx.fillRect(0,0,canvas.width,canvas.height);const duration=project.duration_ms||1;ctx.fillStyle='#617387';ctx.font='12px sans-serif';for(let i=0;i<=10;i++){const x=i*canvas.width/10;ctx.fillRect(x,0,1,canvas.height);ctx.fillText((duration*i/10000).toFixed(1)+'s',x+3,14);}if(project.asset){ctx.fillStyle='#233c61';ctx.fillRect(0,22,canvas.width,15);ctx.fillStyle='#d7e6ff';ctx.fillText('Imported FSEQ base',8,34);}project.cues.forEach((cue,i)=>{ctx.fillStyle=cue.color;ctx.fillRect(cue.start_ms/duration*canvas.width,42+i*24,Math.max(2,cue.duration_ms/duration*canvas.width),18);ctx.fillStyle='#ffffff';ctx.fillText(cue.target,Math.max(2,cue.start_ms/duration*canvas.width+3),55+i*24);});ctx.fillStyle='#fff';ctx.fillRect(Number($('studioScrub').value)/duration*canvas.width,0,2,canvas.height);}
async function refreshPreview(){if(!project?.outputs.length)return;if(previewBusy){previewAgain=true;return;}previewBusy=true;try{readForm();const time=Number($('studioScrub').value);$('studioClock').textContent=(time/1000).toFixed(3)+' s';const result=await api('/preview',{project,time_ms:time,output:Number($('studioPreviewOutput').value||0)});const raw=atob(result.rgb);previewColors={raw,index:Number($('studioPreviewOutput').value||0),count:result.count};drawLayout();const canvas=$('studioPixels'),ctx=canvas.getContext('2d');ctx.fillStyle='#0b1320';ctx.fillRect(0,0,canvas.width,canvas.height);const columns=Math.min(100,result.count),rows=Math.ceil(result.count/columns),width=canvas.width/columns,height=canvas.height/rows;for(let i=0;i<result.count;i++){ctx.fillStyle=`rgb(${raw.charCodeAt(i*3)},${raw.charCodeAt(i*3+1)},${raw.charCodeAt(i*3+2)})`;ctx.fillRect(i%columns*width+1,Math.floor(i/columns)*height+1,Math.max(1,width-2),Math.max(1,height-2));}}catch(e){if(!previewing)message(e.message,true);}finally{previewBusy=false;if(previewAgain){previewAgain=false;refreshPreview();}}drawTimeline();}
function stopPreview(){previewing=false;$('studioAudioPreview').pause();}
function animate(){if(previewing){const audio=$('studioAudioPreview');const t=project.media?audio.currentTime*1000:performance.now()-previewStart;if(t>=project.duration_ms)stopPreview();else{$('studioScrub').value=t;if(performance.now()-lastPreview>140){lastPreview=performance.now();refreshPreview();}}}requestAnimationFrame(animate);}
function showTab(name){document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===name)));document.querySelectorAll('.studio-panel').forEach(panel=>panel.hidden=panel.id!==name);if(name==='guided')renderWizard();if(name==='layout')renderLayout();}
document.querySelectorAll('[data-tab]').forEach(tab=>tab.addEventListener('click',()=>showTab(tab.dataset.tab)));
action('newProject',()=>{stopPreview();project=newProject(config.default_output);renderProject();mark();});
action('saveProject',async()=>{await save();message('Show saved.');});
$('studioProjects').addEventListener('change',async()=>{if(!$('studioProjects').value)return;try{stopPreview();project=(await api('/projects/'+$('studioProjects').value)).project;renderProject();}catch(e){message(e.message,true);}});
action('deleteProject',async()=>{if(!confirm('Delete this saved show?'))return;await api('/projects/'+project.id,undefined,'DELETE');config.projects=config.projects.filter(p=>p.id!==project.id);project=newProject(config.default_output);renderProject();});
action('saveCue',()=>{readForm();const cue=cueFromFields({id:$('cueId').value,target:$('cueTarget').value,start:$('cueStart').value,duration:$('cueDuration').value,end:$('cueEnd').value,effect:$('cueEffect').value,color:$('cueColor').value,intensity:$('cueIntensity').value,period:$('cuePeriod').value,power:$('cuePower').checked});if(!cue.target||cue.duration_ms<1||cue.start_ms<0||cue.start_ms+cue.duration_ms>project.duration_ms)throw Error('Check the cue target, start and duration.');const index=project.cues.findIndex(c=>c.id===cue.id);if(index<0)project.cues.push(cue);else project.cues[index]=cue;mark();renderCues();refreshPreview();});
action('clearCue',resetCue);
action('saveStudioGroup',()=>{const name=$('groupName').value.trim(),targets=$('groupTargets').value.trim();if(!name||!targets)throw Error('Enter a group name and LED ranges.');project.groups[name]=targets;mark();renderGroups();});
action('addStudioOutput',()=>{const next=Math.max(0,...project.outputs.map(o=>o.first_pixel+o.count-1))+1;project.outputs.push({...config.default_output,name:'Line '+(project.outputs.length+1),first_pixel:next,gpio:project.outputs.some(o=>o.gpio===21&&o.node==='local')?10:21});mark();renderOutputs();renderWizard();renderLayout();});
action('uploadStudioMusic',async()=>{const file=$('studioMusicFile').files[0];if(!file)throw Error('Choose an audio file.');const form=new FormData();form.append('file',file);const result=await api('/api/music/upload',form);project.media=result.file;config=await api('/config');renderMusic();setAudio();mark();message('Song uploaded. Set the show duration to match the song.');});
action('importStudioFseq',async()=>{const file=$('studioFseqFile').files[0];if(!file)throw Error('Choose a .fseq file.');const form=new FormData();form.append('file',file);message('Uploading and validating sequence…');const result=(await api('/import',form)).sequence;project.asset=result.asset;project.duration_ms=result.duration_ms;project.frame_ms=result.frame_ms;if(!project.media&&config.music.some(m=>m.name===result.media))project.media=result.media;renderProject();mark();message(`Imported FSEQ ${result.version}: ${result.frames} frames, ${result.channels} channels. Map outputs to the appropriate first pixels and choose the matching song.`);});
action('previewStudio',async()=>{readForm();const audio=$('studioAudioPreview');if(project.media){audio.currentTime=Number($('studioScrub').value)/1000;await audio.play();}previewStart=performance.now()-Number($('studioScrub').value);previewing=true;});
action('stopPreview',stopPreview);
$('studioAudioPreview').addEventListener('loadedmetadata',()=>{const duration=$('studioAudioPreview').duration;if(Number.isFinite(duration))message(`Song length: ${duration.toFixed(3)} seconds. Set show duration as needed.`);});
$('studioScrub').addEventListener('input',()=>{stopPreview();refreshPreview();});
$('studioTimeline').addEventListener('click',event=>{if(suppressTimelineClick){suppressTimelineClick=false;return;}stopPreview();const rect=$('studioTimeline').getBoundingClientRect();$('studioScrub').value=(event.clientX-rect.left)/rect.width*project.duration_ms;refreshPreview();});
$('studioPreviewOutput').addEventListener('change',refreshPreview);
action('playStudio',async()=>{stopPreview();await save();await api('/play',{project:project.id});message('Preparing advanced playback. Only now will Advanced Users take control of the lights.');});
action('pauseStudio',async()=>{await api('/control',{command:lastPaused?'resume':'pause'});});
action('stopStudio',async()=>{stopPreview();await api('/control',{command:'stop'});message('Advanced playback stopped. Normal controls restored.');});
action('downloadStudioProject',async()=>{await save();location.href=apiRoot+'/project-download/'+project.id;});
action('restoreStudioProject',async()=>{const file=$('studioProjectFile').files[0];if(!file)throw Error('Choose a project JSON file.');const imported=JSON.parse(await file.text());imported.id=id();project=(await api('/projects',imported)).project;config=await api('/config');renderProject();message('Project imported. Upload matching FSEQ/audio assets if needed.');});
action('exportStudioFseq',async()=>{await save();location.href=apiRoot+'/export/'+project.id;message('Rendering FSEQ export. Long shows can take a while.');});
function renderNodes(){$('studioNodeName').value=config.local.name;$('studioNodeKey').value=config.local.pairing_key;const root=$('studioNodes');root.replaceChildren();config.nodes.forEach(node=>{const row=document.createElement('div');row.className='studio-toolbar mb-2';const label=document.createElement('span');label.textContent=node.name+' · '+node.url;row.append(label,button('Remove',async()=>{try{await api('/nodes/'+node.id,undefined,'DELETE');config=await api('/config');renderNodes();renderOutputs();}catch(e){message(e.message,true);}},'btn-outline-danger'));root.append(row);});}
$('showNodeKey').addEventListener('change',()=>$('studioNodeKey').type=$('showNodeKey').checked?'text':'password');
action('pairStudioNode',async()=>{message('Connecting to the other Pi…');await api('/nodes',{url:$('pairUrl').value.trim(),key:$('pairKey').value.trim()});$('pairKey').value='';config=await api('/config');renderNodes();renderOutputs();renderWizard();message('Pi paired. Select it in LED outputs & timing.');});
async function setup(action,text){if(!confirm(text))return;const result=await api('/platform',{action});message(result.message);}
action('prepareSpi',()=>setup('spi','Enable SPI on this Pi? Boot files will be backed up; a reboot will be needed.'));
action('preparePwm',()=>setup('pwm','This disables built-in 3.5 mm audio on THIS Pi after reboot. Use only on a remote Pi that does not play audio. Continue?'));
action('rebootStudioPi',()=>setup('reboot','Reboot this Pi now? Playback and this connection will stop temporarily.'));
['showName','showDuration','showFrame','showAudio','audioOffset','showLoop'].forEach(name=>$(name).addEventListener('change',()=>{readForm();mark();$('studioScrub').max=project.duration_ms;drawTimeline();}));
$('showMedia').addEventListener('change',()=>{project.media=$('showMedia').value;setAudio();mark();});

function renderWizard(){
 if(!project)return;
 $('wizardProgress').textContent=`Step ${wizardStep} of 3: ${['Song and audio','LED lines and Pis','Review and save'][wizardStep-1]}`;
 [1,2,3].forEach(n=>$('wizardStep'+n).hidden=n!==wizardStep);
 $('wizardBack').disabled=wizardStep===1;$('wizardNext').hidden=wizardStep===3;$('wizardFinish').hidden=wizardStep!==3;
 $('wizardName').value=project.name;$('wizardAudio').value=project.audio_device;
 const root=$('wizardLines');root.replaceChildren();project.outputs.forEach((o,i)=>root.append(button(`${o.name}: ${o.count} LEDs (${o.first_pixel}–${o.first_pixel+o.count-1})`,()=>{wizardLine=i;loadWizardLine();})));
 $('wizardNode').replaceChildren(option('local','This Pi'));config.nodes.forEach(n=>$('wizardNode').append(option(n.id,n.name)));
 loadWizardLine();
 $('wizardSummary').textContent=`${project.outputs.length} LED lines · ${project.outputs.filter(o=>o.enabled).reduce((n,o)=>n+o.count,0).toLocaleString()} enabled LEDs · ${new Set(project.outputs.filter(o=>o.enabled).map(o=>o.node)).size} Pis assigned. No lights activate until you explicitly Play or Test.`;
}
function loadWizardLine(){
 const out=project.outputs[wizardLine]||{...config.default_output,name:'Line '+(project.outputs.length+1),first_pixel:Math.max(0,...project.outputs.map(o=>o.first_pixel+o.count-1))+1,gpio:21,node:'local'};
 for(const [input,key] of [['wizardLineName','name'],['wizardNode','node'],['wizardPin','gpio'],['wizardCount','count'],['wizardFirst','first_pixel'],['wizardBrightness','brightness']])$(input).value=out[key];
}
action('wizardNext',()=>{if(wizardStep===1){project.name=$('wizardName').value.trim()||'New show';project.audio_device=$('wizardAudio').value;$('showName').value=project.name;$('showAudio').value=project.audio_device;mark();}wizardStep=Math.min(3,wizardStep+1);renderWizard();});
action('wizardBack',()=>{wizardStep=Math.max(1,wizardStep-1);renderWizard();});
action('wizardNewLine',()=>{wizardLine=-1;loadWizardLine();});
action('wizardApplyLine',()=>{
 const count=Number($('wizardCount').value),first=Number($('wizardFirst').value),brightness=Number($('wizardBrightness').value);
 if(!Number.isInteger(count)||count<1||!Number.isInteger(first)||first<1||!Number.isFinite(brightness)||brightness<0||brightness>100)throw Error('Enter a positive whole LED count and first LED, and brightness from 0 to 100.');
 const out={...(project.outputs[wizardLine]||config.default_output),enabled:true,name:$('wizardLineName').value.trim()||'LED line',node:$('wizardNode').value,gpio:Number($('wizardPin').value),count,first_pixel:first,brightness,fps:Math.min(25,1/(count*30e-6+.004))};
 if(out.fps<1)throw Error('Split this line across additional outputs or Pis.');
 // Round down to one decimal FPS so the chosen rate never exceeds the wire time.
 out.fps=Math.floor(Math.min(25,1/(count*30e-6+.004))*10)/10;
 if(wizardLine<0){project.outputs.push(out);wizardLine=project.outputs.length-1;}else project.outputs[wizardLine]=out;
 mark();renderOutputs();renderWizard();renderLayout();message('Line applied. Save setup to check hardware compatibility.');
});
action('wizardPair',()=>showTab('nodes'));
action('wizardFinish',async()=>{await save();showTab('layout');message('Setup saved. Arrange your lines, then choose a song and add cues in Show editor.');});
function layoutPosition(out,index){return {x:(out.layout_x??5)/100*1200,y:(out.layout_y??(5+index%10*9))/100*600};}
function drawLayout(){
 if(!project)return;const canvas=$('studioLayout'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#101c2c';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.font='13px sans-serif';
 project.outputs.forEach((o,i)=>{const {x,y}=layoutPosition(o,i),width=240;ctx.fillStyle=i===layoutIndex?'#ffffff':'#37506b';ctx.fillRect(x-3,y-3,width+6,36);ctx.fillStyle='#37506b';ctx.fillRect(x,y,width,30);
 if(previewColors&&previewColors.index===i){const samples=Math.min(120,previewColors.count);for(let j=0;j<samples;j++){const pixel=Math.floor(j/samples*previewColors.count)*3,raw=previewColors.raw;ctx.fillStyle=`rgb(${raw.charCodeAt(pixel)},${raw.charCodeAt(pixel+1)},${raw.charCodeAt(pixel+2)})`;ctx.fillRect(x+j/samples*width,y,width/samples+1,30);}}
 ctx.fillStyle='#e0eaff';const name=o.node==='local'?'This Pi':config.nodes.find(n=>n.id===o.node)?.name||'Unpaired Pi';ctx.fillText(`${o.name} · ${name} · ${o.first_pixel}–${o.first_pixel+o.count-1}${o.enabled?'':' (off)'}`,x,y+48);
 });
}
function renderLayout(){
 if(!project)return;layoutIndex=Math.max(0,Math.min(layoutIndex,project.outputs.length-1));$('layoutOutput').replaceChildren();project.outputs.forEach((o,i)=>$('layoutOutput').append(option(i,o.name)));$('layoutOutput').value=layoutIndex;const out=project.outputs[layoutIndex];$('layoutX').value=out?.layout_x??5;$('layoutY').value=out?.layout_y??(5+layoutIndex%10*9);drawLayout();
}
$('layoutOutput').addEventListener('change',()=>{layoutIndex=Number($('layoutOutput').value);renderLayout();});
['layoutX','layoutY'].forEach(name=>$(name).addEventListener('change',()=>{const out=project.outputs[layoutIndex];if(!out)return;out.layout_x=Math.max(0,Math.min(80,Number($('layoutX').value)||0));out.layout_y=Math.max(0,Math.min(90,Number($('layoutY').value)||0));mark();renderLayout();}));
function point(canvas,event){const rect=canvas.getBoundingClientRect();return {x:(event.clientX-rect.left)/rect.width*canvas.width,y:(event.clientY-rect.top)/rect.height*canvas.height};}
$('studioLayout').addEventListener('pointerdown',event=>{const canvas=$('studioLayout'),p=point(canvas,event);for(let i=project.outputs.length-1;i>=0;i--){const pos=layoutPosition(project.outputs[i],i);if(p.x>=pos.x-4&&p.x<=pos.x+244&&p.y>=pos.y-4&&p.y<=pos.y+50){layoutIndex=i;layoutDrag={id:event.pointerId,dx:p.x-pos.x,dy:p.y-pos.y};canvas.setPointerCapture(event.pointerId);renderLayout();break;}}});
$('studioLayout').addEventListener('pointermove',event=>{if(!layoutDrag||layoutDrag.id!==event.pointerId)return;const p=point($('studioLayout'),event),out=project.outputs[layoutIndex];out.layout_x=Math.max(0,Math.min(80,(p.x-layoutDrag.dx)/12));out.layout_y=Math.max(0,Math.min(90,(p.y-layoutDrag.dy)/6));mark();renderLayout();});
['pointerup','pointercancel'].forEach(name=>$('studioLayout').addEventListener(name,()=>{layoutDrag=null;}));
$('studioTimeline').addEventListener('pointerdown',event=>{const canvas=$('studioTimeline'),p=point(canvas,event),index=Math.floor((p.y-42)/24),cue=project.cues[index];if(!cue||p.y<42||p.y>42+index*24+18)return;const left=cue.start_ms/project.duration_ms*canvas.width,right=(cue.start_ms+cue.duration_ms)/project.duration_ms*canvas.width;if(p.x<left-7||p.x>right+7)return;stopPreview();suppressTimelineClick=true;cueDrag={id:event.pointerId,index,x:p.x,original:{...cue},edge:Math.abs(p.x-right)<8?'end':Math.abs(p.x-left)<8?'start':'move'};canvas.setPointerCapture(event.pointerId);editCue(cue);});
$('studioTimeline').addEventListener('pointermove',event=>{if(!cueDrag||cueDrag.id!==event.pointerId)return;const canvas=$('studioTimeline'),p=point(canvas,event),delta=(p.x-cueDrag.x)/canvas.width*project.duration_ms;project.cues[cueDrag.index]=moveCue(cueDrag.original,delta,project.duration_ms,project.frame_ms,cueDrag.edge);editCue(project.cues[cueDrag.index]);mark();drawTimeline();});
['pointerup','pointercancel'].forEach(name=>$('studioTimeline').addEventListener(name,()=>{if(cueDrag){cueDrag=null;renderCues();refreshPreview();}}));

try{config=await api('/config');project=newProject(config.default_output);renderNodes();renderProject();if(!config.projects.length)showTab('guided');requestAnimationFrame(animate);}catch(e){message(e.message,true);}
let polling=false;setInterval(async()=>{if(polling)return;polling=true;try{const s=await api('/status');lastPaused=s.paused;$('studioRuntime').textContent=(s.preparing?'Preparing':s.state)+` · ${(Math.max(0,s.position_ms)/1000).toFixed(2)} s · ${s.remote_count} remote Pis`+(s.message?' · '+s.message:'')+(s.audio_error?' · Audio: '+s.audio_error:'')+(s.outputs?.length?' · '+s.outputs.map(o=>`${o.name}: ${o.actual_fps}/${o.requested_fps} FPS`).join(', '):'');if(s.error)message(s.error,true);}catch(e){$('studioRuntime').textContent='Pi status unavailable';}finally{polling=false;}},1200);
});
})();
