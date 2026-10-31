const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const base=__dirname+'/../src/controller/server/libs/app/';
const source=fs.readFileSync(base+'static/assets/js/song_show.js','utf8');
const pure=require(base+'static/assets/js/song_show.js');
class Element {
 constructor(){this.value='';this.checked=false;this.disabled=false;this.children=[];this.listeners={};this.style={setProperty(){}};this.options=[];this.dataset={};}
 addEventListener(k,f){this.listeners[k]=f;}append(...v){this.children.push(...v);}replaceChildren(...v){this.children=v;}setAttribute(){}getContext(){return {fillRect(){},fillText(){}};}
 async fire(k){return this.listeners[k]&&this.listeners[k]();}
}
const html=fs.readFileSync(base+'templates/home/effects/effect_song_show.html','utf8');
const nodes={};for(const m of html.matchAll(/id="([^"]+)"/g))nodes[m[1]]=new Element();
nodes.syncDevice.value='device_1';nodes.syncDevice.options=[{value:'device_1'}];
const labels={};pure.colorKeys.forEach(k=>labels[k]=new Element());
const old={section_size:50,sync_mode:'paired',sync_groups:[],max_lit_leds:75,bass_color:'#ff8000',mid_color:'#008000',treble_color:'#8000ff',beat_color:'#ff4000',power_color:'#ffffff'};
const preset={id:'christmas',name:'Christmas',colors:Object.fromEntries(pure.colorKeys.map((k,i)=>[k,['#ff0000','#008000','#ffffff'][i%3]]))};
let ready;let failActivate=false;const posts=[];
const context={console,document:{addEventListener:(k,f)=>ready=f,getElementById:k=>nodes[k],createElement:()=>new Element(),querySelector:q=>labels[q.match(/"([^"]+)"/)[1]],querySelectorAll:()=>[]},localStorage:{getItem(){return null;},setItem(){}},fetch:async(url,o={})=>{
 if(o.method==='POST'){posts.push({url,data:JSON.parse(o.body)});return {ok:!(failActivate&&url==='/api/effect/active'),status:503,json:async()=>({ok:true})};}
 return {ok:true,json:async()=>url.includes('show-palettes')?{palettes:[preset]}:url.includes('settings/device')?{settings:{led_count:750}}:{settings:old}};
}};
(async()=>{vm.runInNewContext(source,context);await ready();assert.equal(nodes.showMode.value,'classic');assert.equal(nodes.expandedBands.checked,false);
 nodes.holidayPalette.value='christmas';await nodes.holidayPalette.fire('change');assert.equal(posts.length,0,'Preset choice does not save or restart playback');assert.equal(nodes.expandedBands.checked,true);assert.equal(nodes.bass_color.value,preset.colors.bass_color);
 nodes.showMode.value='auto';await nodes.showMode.fire('change');assert.match(nodes.showModeHelp.textContent,/Analysis-directed/);
 await nodes.saveSongShow.fire('click');assert.equal(posts.at(-1).url,'/api/effect/active','Explicit Save & use also activates the selected look');const saved=posts.filter(p=>p.url==='/api/settings/effect').at(-1).data;assert.equal(saved.device,'device_1');assert.equal(saved.settings.palette_preset,'christmas');assert.equal(saved.settings.show_mode,'auto');assert.equal(saved.settings.max_lit_leds,75);assert.equal(saved.settings.section_size,50);assert.equal(saved.settings.sync_mode,'paired');assert.equal(saved.settings.brilliance_color,preset.colors.brilliance_color);
 nodes.brilliance_color.value='#123456';await nodes.brilliance_color.fire('input');assert.equal(nodes.holidayPalette.value,'custom');await nodes.saveSongShow.fire('click');assert.equal(posts.filter(p=>p.url==='/api/settings/effect').at(-1).data.settings.brilliance_color,'#123456');assert.equal(posts.filter(p=>p.url==='/api/settings/effect').at(-1).data.settings.palette_preset,'custom');
 failActivate=true;await nodes.saveSongShow.fire('click');assert.match(nodes.syncStatus.textContent,/saved, but.*could not be turned on/);assert.equal(nodes.songShowControls.disabled,false);
 console.log('Holiday palette UI passed: legacy load, editable ten-color preset, no autosave, analysis mode and preserved grouping/LED budget.');})().catch(e=>{console.error(e);process.exitCode=1;});
