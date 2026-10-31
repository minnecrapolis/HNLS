const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const app=__dirname+'/../src/controller/server/libs/app/';
class Element{constructor(){this.disabled=false;this.textContent='';this.events={};}addEventListener(k,f){this.events[k]=f;}}
const nodes={};for(const id of ['hnlsPlayNow','hnlsStopShow','hnlsPlayNowStatus'])nodes[id]=new Element();
const calls=[];let poll,fail=false,pendingResolve=null,hold=false;
const context={document:{getElementById:id=>nodes[id]},window:{setInterval:f=>poll=f},fetch:async(url,o={})=>{
 if(o.method==='POST'){calls.push({url,data:JSON.parse(o.body)});if(hold)await new Promise(r=>pendingResolve=r);return {ok:!fail,json:async()=>fail?{error:'Upload at least one song'}:{message:'Manual show requested. Saved hours are unchanged.'}};}
 return {ok:true,json:async()=>({message:'Outside show hours; scheduled lights are off.'})};
}};
(async()=>{vm.runInNewContext(fs.readFileSync(app+'static/assets/js/play_now.js','utf8'),context);await new Promise(r=>setImmediate(r));assert.equal(calls.length,0,'Merely opening Home must not start the show');
 hold=true;const first=nodes.hnlsPlayNow.events.click();assert.equal(nodes.hnlsPlayNow.disabled,true);await nodes.hnlsPlayNow.events.click();assert.equal(calls.length,1,'Ignore double click while queued');pendingResolve();await first;hold=false;
 assert.equal(calls[0].url,'/api/music/show-now');assert.equal(calls[0].data.action,'play');assert.match(nodes.hnlsPlayNowStatus.textContent,/unchanged/);assert.equal(nodes.hnlsPlayNow.disabled,false);
 await nodes.hnlsStopShow.events.click();assert.equal(calls.at(-1).data.action,'stop');fail=true;await nodes.hnlsPlayNow.events.click();assert.match(nodes.hnlsPlayNowStatus.textContent,/Upload/);assert.equal(nodes.hnlsStopShow.disabled,false);
 for(const file of ['templates/includes/hournerd_start.html','templates/home/music.html'])assert.ok(fs.readFileSync(app+file,'utf8').includes("include 'includes/play_now.html'"));
 console.log('Play now UI passed: Home/Music placement, deliberate start/stop, double-click protection and actionable errors.');})().catch(e=>{console.error(e);process.exitCode=1;});
