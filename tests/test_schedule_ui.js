const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const base=__dirname+'/../src/controller/server/libs/app/';
const html=fs.readFileSync(base+'templates/home/music.html','utf8')+fs.readFileSync(base+'templates/includes/show_hours.html','utf8');
class Element{constructor(){this.children=[];this.checked=false;this.disabled=false;this.value='';this.handlers={};}append(x){this.children.push(x)}replaceChildren(){this.children=[]}setAttribute(){}addEventListener(k,f){this.handlers[k]=f}}
(async()=>{
 const nodes={};for(const x of html.matchAll(/id="([^"]+)"/g))nodes[x[1]]=new Element();
 let fail=false,poll,saved;
 const value={settings:{enabled:true,days:[4],start:'22:00',end:'02:00',timezone:'America/Chicago'},local_time:'2026-10-30T22:00:00-05:00',message:'Show started.'};
 const context={document:{getElementById:id=>nodes[id]},window:{setInterval:f=>poll=f},fetch:async(url,opts={})=>{
  assert.equal(url,'/api/music/show-schedule');if(opts.method==='POST'){saved=JSON.parse(opts.body);if(fail)return {ok:false,json:async()=>({error:'Invalid schedule'})};}
  return {ok:true,json:async()=>value};
 }};
 vm.runInNewContext(fs.readFileSync(base+'static/assets/js/show_schedule.js','utf8'),context);await new Promise(r=>setImmediate(r));
 assert(nodes.hnlsScheduleEnabled.checked);assert(nodes.hnlsScheduleDay4.checked);assert(!nodes.hnlsScheduleDay0.checked);assert.equal(nodes.hnlsScheduleStart.value,'22:00');assert(!nodes.hnlsScheduleSave.disabled);
 nodes.hnlsScheduleStart.value='21:00';await poll();assert.equal(nodes.hnlsScheduleStart.value,'21:00','Status polling must not discard edits');
 await nodes.hnlsScheduleForm.handlers.submit({preventDefault(){}});assert.equal(saved.start,'21:00');assert.deepEqual(saved.days,[4]);assert.match(nodes.hnlsScheduleStatus.textContent,/saved/);
 fail=true;await nodes.hnlsScheduleForm.handlers.submit({preventDefault(){}});assert.match(nodes.hnlsScheduleStatus.textContent,/Invalid/);assert(!nodes.hnlsScheduleSave.disabled);
 console.log('Schedule UI passed: persisted fields, weekday selection, edit preservation and save error recovery.');
 // The analysis list is also a playable list, not just informational rows.
 const rows={};for(const x of html.matchAll(/id="([^"]+)"/g))rows[x[1]]=new Element();let played;
 const ctx={Map,document:{getElementById:id=>rows[id],createElement:()=>new Element()},window:{setInterval(){}},fetch:async(url,opts={})=>{
  if(url==='/api/music/play'){played=JSON.parse(opts.body);return {ok:true,json:async()=>({ok:true})};}
  return {ok:true,json:async()=>({settings:{shuffle:false},ready:1,total:1,files:[{file:'<song>.mp3',ready:true,sections:5}],progress:{}})};
 }};
 vm.runInNewContext(fs.readFileSync(base+'static/assets/js/hnls_playlist.js','utf8'),ctx);await new Promise(r=>setImmediate(r));
 const button=rows.hnlsAnalysisList.children[0].children[0].children[0];assert.equal(button.textContent,'<song>.mp3');await button.handlers.click();assert.equal(played.file,'<song>.mp3');
 console.log('Analysis song-title click passed with safely rendered filename.');
})().catch(e=>{console.error(e);process.exitCode=1});
