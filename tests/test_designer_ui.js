const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(__dirname+'/../src/controller/server/libs/app/templates/includes/song_moments.html','utf8');
const source=fs.readFileSync(__dirname+'/../src/controller/server/libs/app/static/assets/js/song_moments.js','utf8');
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.listeners={};this.value='';this.checked=false;this.disabled=false;this.width=1200;this.height=220;this.dataset={};this.attributes={};this.classList={toggle(){}};this.scrolled=false;this.focused=false;}
 setAttribute(name,value){this.attributes[name]=value;}
 scrollIntoView(){this.scrolled=true;}focus(){this.focused=true;}
 append(...nodes){this.children.push(...nodes);if(this.tag==='select'&&!this.value&&nodes[0])this.value=nodes[0].value;}
 replaceChildren(...nodes){this.children=[];if(this.tag==='select')this.value='';this.append(...nodes);}
 addEventListener(type,handler){this.listeners[type]=handler;}
 async fire(type,e={}){if(this.listeners[type])await this.listeners[type](e);if(this['on'+type])await this['on'+type](e);}
 querySelectorAll(selector){const found=[];const walk=e=>{for(const c of e.children||[]){if(c.tag==='input'&&(selector!=='input:checked'||c.checked))found.push(c);walk(c);}};walk(this);return found;}
 getContext(){return new Proxy({measureText:t=>({width:t.length*6})},{get:(target,key)=>key in target?target[key]:(()=>{}),set:(target,key,value)=>(target[key]=value,true)});}
 getBoundingClientRect(){return {left:0,top:0,width:1200,height:this.height};}setPointerCapture(){}
}
(async()=>{
 const nodes={};for(const m of html.matchAll(/<(\w+)[^>]*\bid="([^"]+)"([^>]*)>/g)){const e=new Element(m[1]);e.checked=/\bchecked\b/.test(m[3]);const v=m[3].match(/\bvalue="([^"]*)"/);if(v)e.value=v[1];nodes[m[2]]=e;}
 // Option defaults are normally selected by the browser parser.
 nodes.momentDirection.value='forward';nodes.momentEffect.value='flash';let state={file:'Thriller.mp3',state:'playing',position:180,duration:360};let saved=null,interval=null;
 const posts=[];let cues=[],regions=[],cueSaves=0;
 const context={document:{hidden:false,getElementById:id=>nodes[id],createElement:tag=>new Element(tag),createTextNode:text=>({textContent:text})},window:{setInterval:f=>interval=f},setTimeout,Date,confirm:()=>true,fetch:async(url,options={})=>{
  if(url.endsWith('/playhead'))return {ok:true,json:async()=>({...state})};
  const method=options.method||'GET';const data=options.body?JSON.parse(options.body):null;
  if(url==='/api/music/song-regions'){if(method==='POST'){const region={...data,id:data.id||'b'.repeat(32)};regions=[region];return {ok:true,json:async()=>({region})};}regions=[];return {ok:true,json:async()=>({ok:true})};}
  if(url.startsWith('/api/music/song-moments')){
   if(method==='POST'){cueSaves++;saved={...data,id:data.id||'a'.repeat(32)};const at=cues.findIndex(c=>c.id===saved.id);if(at<0)cues.push(saved);else cues[at]=saved;return {ok:true,json:async()=>({cue:saved})};}
   if(method==='DELETE'){cues=[];return {ok:true,json:async()=>({ok:true})};}
   const file=url.includes('?file=')?decodeURIComponent(url.split('?file=')[1]):'';
   return {ok:true,json:async()=>({file,current_file:'Thriller.mp3',duration:360,files:[{name:'Thriller.mp3'}],cues:file?cues:[],regions,outputs:[{id:'device_0',name:'Main',count:1200},{id:'device_1',name:'Remote',count:750}]})};
  }
  posts.push({url,data});if(url.endsWith('/pause'))state.state='paused';if(url.endsWith('/resume'))state.state='playing';return {ok:true,json:async()=>({ok:true})};
 }};
 vm.runInNewContext(source,context);await new Promise(r=>setImmediate(r));await new Promise(r=>setImmediate(r));
 assert.equal(nodes.momentSong.value,'Thriller.mp3');assert.equal(nodes.momentSave.disabled,false);
 const x=t=>30+t/360*1140;
 await nodes.momentTimeline.fire('pointerdown',{clientX:x(184),clientY:30,pointerId:1});await nodes.momentTimeline.fire('pointermove',{clientX:x(186),clientY:30});await nodes.momentTimeline.fire('pointerup');
 assert.equal(nodes.momentStart.value,'3:04');assert.equal(nodes.momentEnd.value,'3:06');assert.equal(Number(nodes.momentDuration.value),2);
 nodes.momentAll.checked=false;await nodes.momentAll.fire('change');const checkbox=nodes.momentTargets.querySelectorAll('input')[0];checkbox.checked=true;await checkbox.fire('change');
 const px=n=>25+(n-1+.1)/1200*1150;
 await nodes.momentPixelMap.fire('pointerdown',{clientX:px(112),pointerId:2});await nodes.momentPixelMap.fire('pointermove',{clientX:px(214)});await nodes.momentPixelMap.fire('pointerup');
 assert.equal(Number(nodes.momentFirst.value),112);assert.equal(Number(nodes.momentLast.value),214);
 nodes.momentRegionName.value='Tree 1';await nodes.momentRegionSave.fire('click');assert.equal(nodes.momentRegion.value,'b'.repeat(32));assert.equal(regions[0].first,112);assert.equal(regions[0].last,214);
 await nodes.momentSave.fire('click');assert.equal(saved.start,184);assert.equal(saved.end,186);assert.equal(saved.first,112);assert.equal(saved.last,214);assert.deepEqual(Array.from(saved.targets),['device_0']);assert.equal(saved.effect,'flash');assert.equal(saved.region,'b'.repeat(32));
 state.position=190.125;await interval();await nodes.momentMarkStart.fire('click');assert.equal(nodes.momentStart.value,'3:10.125');assert.equal(state.state,'paused');
 await nodes.momentResume.fire('click');state.position=194.375;await interval();await nodes.momentMarkEnd.fire('click');assert.equal(nodes.momentEnd.value,'3:14.375');assert.equal(Number(nodes.momentDuration.value),4.25);
 await nodes.momentSeek.fire('click');assert.equal(posts.at(-1).url,'/api/music/control');assert.equal(posts.at(-1).data.seconds,190.125);
 await nodes.momentRegionDelete.fire('click');assert.equal(nodes.momentRegionDelete.disabled,true);
 nodes.momentEffect.value='color_blocks';await nodes.momentEffect.fire('change');assert.equal(Number(nodes.momentCycle.value),8);assert.match(nodes.momentEffectHelp.textContent,/prominent|Sharp|scroll/);
 for(const effect of ['bounce','flash','comet','pulse','rainbow','wipe']){nodes.momentEffect.value=effect;await nodes.momentEffect.fire('change');assert.equal(nodes.momentColor2.disabled,false,effect+' must allow second color');assert(nodes.momentUseColor2.checked);}
 nodes.momentUseColor2.checked=false;await nodes.momentUseColor2.fire('change');nodes.momentColor2.value='#0000ff';await nodes.momentColor2.fire('change');assert(nodes.momentUseColor2.checked,'Choosing a second color enables it');
 nodes.momentEffect.value='color_blocks';await nodes.momentEffect.fire('change');
 const boxes=nodes.momentTargets.querySelectorAll('input');boxes[0].checked=false;boxes[1].checked=true;nodes.momentAll.checked=false;await boxes[1].fire('change');nodes.momentFirst.value='700';nodes.momentLast.value='750';
 const before=cueSaves,playState=state.state;nodes.momentReserve.checked=true;await nodes.momentReserve.fire('change');assert.equal(cueSaves,before);assert.equal(state.state,playState,'Checking reserve must not restart playback');
 await nodes.momentSave.fire('click');assert.equal(saved.cycle_seconds,8);assert.equal(saved.band_width,8);assert.equal(saved.direction,'forward');assert.equal(saved.first,700);assert.equal(saved.last,750);assert.deepEqual(Array.from(saved.targets),['device_1']);assert(saved.reserve);assert(saved.use_color2);
 cues.push({...saved,id:'c'.repeat(32),effect:'solid'});await nodes.momentReload.fire('click');assert.match(nodes.momentConflictHelp.textContent,/overlap/);
 const toEdit=cues[1],savedBefore=cueSaves,postsBefore=posts.length;
 nodes.momentEffect.value='flash';nodes.momentColor2.value='#000000';nodes.momentFineTune.open=false;
 await nodes.momentList.children[1].children[3].children[0].fire('click');
 assert(nodes.momentFineTune.open,'Edit opens Fine-tune');assert(nodes.momentEditor.scrolled,'Edit scrolls to the editor');assert(nodes.momentEffect.focused,'Edit focuses a real editable control');
 assert.equal(nodes.momentEffect.value,toEdit.effect);assert.equal(nodes.momentColor2.value,toEdit.color2);assert.equal(nodes.momentSave.textContent,'Update moment');assert.equal(nodes.momentList.children[1].attributes['aria-selected'],'true');assert.equal(nodes.momentList.children[0].attributes['aria-selected'],'false');assert.match(nodes.momentEditingInfo.textContent,/Editing/);
 assert.equal(cueSaves,savedBefore,'Edit does not save');assert.equal(posts.length,postsBefore,'Edit does not change playback');
 const firstId=cues[0].id;nodes.momentBrightness.value='35';await nodes.momentSave.fire('click');assert.equal(saved.id,toEdit.id,'Update targets the clicked moment');assert.equal(saved.brightness,35);assert.equal(cues[0].id,firstId,'Other moments are retained');
 nodes.momentEditor.scrollIntoView=()=>{throw Error('simulated UI failure')};await nodes.momentList.children[0].children[3].children[0].fire('click');assert.match(nodes.momentStatus.textContent,/Could not open/);assert.match(nodes.momentStatus.textContent,/Ctrl\+F5/);nodes.momentEditor.scrollIntoView=()=>{};
 await nodes.momentDelete.fire('click');assert.equal(nodes.momentDelete.disabled,true);
 console.log('Song moment UI passed: current-song selection, visual 2-second span, LEDs 112–214, named tree groups, save/edit/delete, pause-and-mark, duration and seek.');
})().catch(e=>{console.error(e);process.exitCode=1;});
