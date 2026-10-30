const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const base=__dirname+'/../src/controller/server/libs/app/';
const html=fs.readFileSync(base+'templates/home/music.html','utf8'),source=fs.readFileSync(base+'static/assets/js/music.js','utf8');
class Element {
 constructor(){this.children=[];this.listeners={};this.value='';this.files=[];this.disabled=false;this.dataset={};this.classList={add(){},remove(){},toggle(){}};}
 setAttribute(name,value){this[name]=value;}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}
 addEventListener(name,fn){this.listeners[name]=fn;}async fire(name){if(this.listeners[name])await this.listeners[name]();}
}
const nodes={};for(const match of html.matchAll(/id="([^"]+)"/g))nodes[match[1]]=new Element();
const posts=[],timers=[];let confirmed=false;const audio={settings:{mode:'headphones',address:''},devices:[{address:'AA:BB:CC:DD:EE:FF',name:'Soundbar'}],ready:true,backend:'Desktop audio',job:{running:false,message:'',error:''}};
const state={state:'playing',file:'<song>.mp3',position:25,duration:180};
const context={document:{getElementById:id=>nodes[id],createElement:()=>new Element()},console,FormData:class{append(){}},confirm:()=>confirmed,window:{setTimeout:fn=>timers.push(fn),setInterval(){}},fetch:async(url,options={})=>{
 if(url==='/api/music/audio-output'&&options.method!=='POST')return {ok:true,json:async()=>audio};
 if(options.method==='POST'){posts.push({url,data:options.body instanceof Object?{}:JSON.parse(options.body)});return {ok:true,json:async()=>({ok:true})};}
 return {ok:true,json:async()=>({files:[{name:'<song>.mp3',size:1000}],status:state})};
}};
(async()=>{
 vm.runInNewContext(source,context);await new Promise(r=>setImmediate(r));
 assert.equal(nodes.musicTime.textContent,'0:25 / 3:00');assert.equal(nodes.musicSeek.disabled,false);
 const row=nodes.musicList.children[0];assert.equal(row.children[0].children[0].textContent,'<song>.mp3','Song names are rendered as text');
 await row.children[0].children[0].fire('click');assert.equal(posts.at(-1).url,'/api/music/play');assert.equal(posts.at(-1).data.file,'<song>.mp3');
 await timers[0]();assert.equal(nodes.musicList.children[0],row,'Polling preserves the focused song row');
 for(const [id,action,seconds] of [['rewindBtn','seek_relative',-10],['forwardBtn','seek_relative',10],['previousBtn','previous'],['nextBtn','next'],['replayBtn','replay']]){
  await nodes[id].fire('click');assert.equal(posts.at(-1).data.action,action);if(seconds!==undefined)assert.equal(posts.at(-1).data.seconds,seconds);
 }
 nodes.musicSeek.value='65';await nodes.musicSeek.fire('input');assert.equal(nodes.musicTime.textContent,'1:05 / 3:00');await nodes.musicSeek.fire('change');assert.equal(posts.at(-1).data.action,'seek');assert.equal(posts.at(-1).data.seconds,65);
 const del=row.children[2].children[1],before=posts.length;await del.fire('click');assert.equal(posts.length,before,'Cancel does not delete');
 confirmed=true;await del.fire('click');assert.equal(posts.at(-1).data.action,'delete');assert.equal(posts.at(-1).data.file,'<song>.mp3');
 state.state='between_songs';await timers[0]();assert.match(nodes.musicStatus.textContent,/two-second pause/);
 nodes.audioOutputMode.value='bluetooth';nodes.bluetoothDevice.value='AA:BB:CC:DD:EE:FF';await nodes.saveAudioOutput.fire('click');assert.equal(posts.at(-1).url,'/api/music/audio-output');assert.equal(posts.at(-1).data.mode,'bluetooth');assert.equal(posts.at(-1).data.address,'AA:BB:CC:DD:EE:FF');
 await nodes.pairBluetooth.fire('click');assert.equal(posts.at(-1).data.action,'pair');assert.equal(posts.at(-1).data.address,'AA:BB:CC:DD:EE:FF');
 confirmed=false;const count=posts.length;await nodes.enableBluetooth.fire('click');assert.equal(posts.length,count,'Enabling system support requires an explicit confirmation');
 confirmed=true;await nodes.enableBluetooth.fire('click');assert.equal(posts.at(-1).data.action,'setup');
 nodes.audioOutputMode.value='headphones';await nodes.saveAudioOutput.fire('click');assert.equal(posts.at(-1).data.mode,'headphones');
 state.state='stopped';state.file=null;await timers[0]();assert.equal(nodes.nextBtn.disabled,true);assert.equal(nodes.musicSeek.disabled,true);
 console.log('Music Library UI simulation passed: transport buttons, seeking, escaped names, deletion confirmation, gap status and inactive controls.');
})().catch(error=>{console.error(error);process.exitCode=1;});
