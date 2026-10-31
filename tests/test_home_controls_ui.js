const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const app=__dirname+'/../src/controller/server/libs/app/';
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.disabled=false;this.hidden=false;this.checked=false;this.files=[];this.events={};}
 append(...nodes){const before=this.children.length;this.children.push(...nodes);if(this.tag==='select'&&before===0&&nodes.length)this.value=nodes[0].value;}
 replaceChildren(...nodes){this.children=[];if(this.tag==='select')this.value='';this.append(...nodes);}addEventListener(k,f){this.events[k]=f;}async fire(k){if(this.events[k])await this.events[k]();}
}
class Form{constructor(){this.files=[];}append(k,v){this.files.push(v);}}
const html=fs.readFileSync(app+'templates/includes/home_controls.html','utf8'),nodes={};for(const m of html.matchAll(/<(\w+)[^>]*id="([^"]+)"/g))nodes[m[2]]=new Element(m[1]);
nodes['home-controls']=new Element();nodes.homeLightTarget.value='*';
const palettes=[{id:'christmas',name:'Christmas',colors:{}}];const devices=[{id:'device_0',name:'Main',brightness:20,mode:'classic',palette:'custom'},{id:'device_1',name:'Slave',brightness:30,mode:'auto',palette:'custom'}];
const calls=[],timers=[];let confirmDiscard=false,failLook=false,shuffle=false;
const state={state:'playing',file:'<Garden>.mp3',position:12,duration:180};
const context={console,FormData:Form,document:{getElementById:k=>nodes[k],createElement:t=>new Element(t)},window:{confirm:()=>confirmDiscard,setInterval:f=>timers.push(f),setTimeout:f=>timers.push(f)},fetch:async(url,o={})=>{
 if(o.method==='POST'){
  const data=o.body instanceof Form?{upload:true}:JSON.parse(o.body);calls.push({url,data});
  if(url==='/api/music/home-look'){
   if(failLook)return {ok:true,json:async()=>({ok:false,applied:[{name:'Main'}],failed:[{name:'Slave',error:'write failed'}],message:'Saved for Main.'})};
   devices.filter(d=>data.target==='*'||d.id===data.target).forEach(d=>{if(data.palette)d.palette=data.palette;if(data.mode)d.mode=data.mode;if('brightness'in data)d.brightness=data.brightness;});
   return {ok:true,json:async()=>({ok:true,failed:[],message:'Saved.'})};
  }
  if(url==='/api/music/playlist-settings')shuffle=data.shuffle;
  return {ok:true,json:async()=>({ok:true})};
 }
 const values={'/api/music/library':{files:[{name:'<Garden>.mp3'},{name:'Thriller.mp3'}],status:state},'/api/music/home-look':{devices,palettes},'/api/music/audio-output':{settings:{mode:'headphones',address:''},devices:[{address:'AA:BB:CC:DD:EE:FF',name:'Soundbar'}]},'/api/music/playlist-settings':{shuffle}};
 return {ok:true,json:async()=>JSON.parse(JSON.stringify(values[url]))};
}};
const settle=()=>new Promise(r=>setImmediate(r));
(async()=>{vm.runInNewContext(fs.readFileSync(app+'static/assets/js/home_controls.js','utf8'),context);await settle();assert.equal(calls.length,0,'Opening Home is read-only');assert.match(nodes.homeNowPlaying.textContent,/<Garden>/);assert.equal(nodes.homeSong.children[0].textContent,'<Garden>.mp3');assert.equal(nodes.homeMode.value,'');assert.equal(nodes.homeBrightnessLabel.textContent,'Different per string');
 await nodes.homePlaySong.fire('click');assert.equal(calls.at(-1).url,'/api/music/show-now');assert.equal(calls.at(-1).data.file,'<Garden>.mp3');
 await nodes.homePause.fire('click');assert.equal(calls.at(-1).url,'/api/music/pause');await nodes.homeNext.fire('click');assert.equal(calls.at(-1).data.action,'next');
 nodes.homeSeek.value='65';await nodes.homeSeek.fire('input');await nodes.homeSeek.fire('change');assert.equal(calls.at(-1).data.seconds,65);
 nodes.homeShuffle.checked=true;await nodes.homeShuffle.fire('change');assert.equal(shuffle,true);
 nodes.homePalette.value='christmas';await nodes.homePalette.fire('change');nodes.homeBrightnessValue.value='12';await nodes.homeBrightnessValue.fire('input');await nodes.homeSaveBrightness.fire('click');assert.equal(calls.at(-1).data.brightness,12);assert.equal('palette'in calls.at(-1).data,false);assert.equal(nodes.homePalette.value,'christmas','Brightness save preserves unsaved palette choice');assert.equal(nodes.homeSaveLook.disabled,false);
 nodes.homeMode.value='auto';await nodes.homeMode.fire('change');await nodes.homeSaveLook.fire('click');const saved=calls.at(-1).data;assert.equal(saved.target,'*');assert.equal(saved.palette,'christmas');assert.equal(saved.mode,'auto');assert.equal('brightness'in saved,false);assert.equal(calls.some(c=>c.url==='/api/effect/active'),false,'Saving a look must not turn a stopped show on');
 nodes.homePalette.value='christmas';await nodes.homePalette.fire('change');nodes.homeLightTarget.value='device_1';await nodes.homeLightTarget.fire('change');assert.equal(nodes.homeLightTarget.value,'*','Keep edits when target switch is cancelled');confirmDiscard=true;nodes.homeLightTarget.value='device_1';await nodes.homeLightTarget.fire('change');assert.equal(nodes.homeSaveLook.disabled,true);
 nodes.homeMode.value='classic';await nodes.homeMode.fire('change');failLook=true;await nodes.homeSaveLook.fire('click');assert.match(nodes.homeLookNotice.textContent,/Slave.*write failed/);assert.equal(nodes.homeSaveLook.disabled,false,'Partial save remains retryable');
 nodes.homeAudioMode.value='bluetooth';await nodes.homeAudioMode.fire('change');nodes.homeAudioDevice.value='AA:BB:CC:DD:EE:FF';await nodes.homeSaveAudio.fire('click');assert.equal(calls.at(-1).url,'/api/music/audio-output');assert.equal(calls.at(-1).data.address,'AA:BB:CC:DD:EE:FF');
 nodes.homeUploadFiles.files=[{name:'new.mp3'}];await nodes.homeUpload.fire('click');assert.ok(calls.some(c=>c.url==='/api/music/upload'));assert.match(nodes.homeMusicNotice.textContent,/Uploaded 1 song/);
 console.log('Home controls passed: read-only load, safe names, song/transport/seek/shuffle/upload, scoped look/brightness, mixed settings, unsaved edits, partial failures and speakers.');})().catch(e=>{console.error(e);process.exitCode=1;});
