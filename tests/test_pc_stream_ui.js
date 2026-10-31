const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(__dirname+'/../src/controller/server/libs/app/static/assets/js/pc_stream.js','utf8');
class Node {constructor(){this.listeners={};this.disabled=false;this.textContent='';this.hidden=false;this.attributes={};}addEventListener(k,f){this.listeners[k]=f;}setAttribute(k,v){this.attributes[k]=v;}}
const nodes={};for(const id of ['pcStreamStart','pcStreamStop','pcStreamStatus','pcLocalStart','hnlsPlayNowPanel'])nodes[id]=new Node();
const localControls=[new Node(),new Node()];const calls=[],timers=[];let failure=false,state='pc_stream_waiting',hold=null;
const context={Date,document:{getElementById:k=>nodes[k],querySelectorAll:()=>localControls},window:{setTimeout:f=>timers.push(f)},fetch:async(url,o={})=>{if(o.method==='POST'){calls.push({url,...JSON.parse(o.body)});return {ok:!failure,json:async()=>failure?{error:'Port unavailable'}:{ok:true}};}if(hold)await hold;return {ok:true,json:async()=>({state})};}};
(async()=>{vm.runInNewContext(source,context);await new Promise(r=>setImmediate(r));assert.equal(calls.length,0);assert.match(nodes.pcStreamStatus.textContent,/Waiting/);assert.ok(localControls.every(n=>n.hidden));assert.equal(nodes.hnlsPlayNowPanel.hidden,true);
 await nodes.pcStreamStart.listeners.click();assert.equal(calls.at(-1).action,'start');assert.equal(nodes.pcStreamStart.disabled,false);
 failure=true;await nodes.pcStreamStart.listeners.click();assert.equal(nodes.pcStreamStatus.textContent,'Port unavailable');assert.equal(nodes.pcLocalStart.disabled,false);
 failure=false;state='pc_stream';await timers.shift()();assert.match(nodes.pcStreamStatus.textContent,/Receiving/);
 await nodes.pcStreamStop.listeners.click();assert.equal(calls.at(-1).action,'stop');assert.match(nodes.pcStreamStatus.textContent,/Spotify may keep playing/);
 state='stopped';await timers.shift()();assert.ok(localControls.every(n=>!n.hidden));assert.equal(nodes.hnlsPlayNowPanel.hidden,false);
 await nodes.pcLocalStart.listeners.click();assert.equal(calls.at(-1).url,'/api/music/show-now');assert.equal(calls.at(-1).action,'play');assert.equal(calls.some(c=>c.action==='record'),false);
 state='playing';await timers.shift()();assert.ok(localControls.every(n=>!n.hidden));
 // An older status response cannot undo a source choice made while it was loading.
 let release;hold=new Promise(r=>release=r);const inFlight=timers.shift()();await nodes.pcStreamStart.listeners.click();release();await inFlight;hold=null;assert.ok(localControls.every(n=>n.hidden));
 const html=fs.readFileSync(__dirname+'/../src/controller/server/libs/app/templates/home/music.html','utf8');assert.ok(html.indexOf('includes/pc_audio.html')<html.indexOf('id="playlist"'));
 console.log('PC streaming source UI passed: visible choice, read-only load, local/stream requests, contextual controls, failures and stale-poll protection.');})().catch(e=>{console.error(e);process.exitCode=1;});
