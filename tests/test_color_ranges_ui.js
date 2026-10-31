const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const base=__dirname+'/../src/controller/server/libs/app/';const html=fs.readFileSync(base+'templates/home/settings/device_settings.html','utf8');
class Element{constructor(){this.children=[];this.handlers={};this.value='';this.disabled=false;this.parent=null;}append(...items){for(const item of items){this.children.push(item);item.parent=this}}replaceChildren(){this.children=[]}setAttribute(){}addEventListener(k,f){this.handlers[k]=f}remove(){this.parent.children=this.parent.children.filter(c=>c!==this)}}
(async()=>{
 const nodes={};for(const m of html.matchAll(/id="([^"]+)"/g))nodes[m[1]]=new Element();let posted,fail=false,confirm=true;
 const outputs=[{id:'device_1',name:'Second Strip',count:750,base_order:'GRB',strip_type:'ws2811_strip_grb',supported:true,ranges:[]},{id:'device_2',name:'Slave',count:350,base_order:'RGB',strip_type:'ws2811_strip_rgb',supported:true,ranges:[]}];
 const context={document:{getElementById:id=>nodes[id],createElement:()=>new Element()},confirm:()=>confirm,fetch:async(url,options={})=>{assert.equal(url,'/api/system/color-ranges');if(options.method==='POST'){posted=JSON.parse(options.body);return {ok:!fail,json:async()=>fail?{error:'Ranges overlap'}:{ok:true,ranges:posted.ranges}};}return {ok:true,json:async()=>({outputs})};}};
 vm.runInNewContext(fs.readFileSync(base+'static/assets/js/color_ranges.js','utf8'),context);await new Promise(r=>setImmediate(r));assert.match(nodes.colorRangesSummary.textContent,/750/);assert(!nodes.colorRangesSave.disabled);
 await nodes.colorRangesAdd.handlers.click();let row=nodes.colorRangesRows.children[0];row.fields.first.value='601';row.fields.last.value='650';row.fields.order.value='RGB';row.fields.name.value='50 LED set';
 confirm=false;nodes.colorRangesOutput.value='device_2';await nodes.colorRangesOutput.handlers.change();assert.equal(nodes.colorRangesOutput.value,'device_1','Unsaved range edits must not disappear');
 await nodes.colorRangesForm.handlers.submit({preventDefault(){}});assert.equal(posted.device,'device_1');assert.deepEqual(posted.ranges,[{name:'50 LED set',first:601,last:650,order:'RGB'}]);assert.match(nodes.colorRangesStatus.textContent,/does not restart/);
 await nodes.colorRangesAdd.handlers.click();fail=true;await nodes.colorRangesForm.handlers.submit({preventDefault(){}});assert.match(nodes.colorRangesStatus.textContent,/overlap/);assert.equal(nodes.colorRangesRows.children.length,2,'Failed save retains editable rows');assert(!nodes.colorRangesSave.disabled);
 fail=false;await nodes.colorRangesClear.handlers.click();await nodes.colorRangesForm.handlers.submit({preventDefault(){}});assert.deepEqual(posted.ranges,[]);
 confirm=true;nodes.colorRangesOutput.value='device_2';await nodes.colorRangesOutput.handlers.change();assert.match(nodes.colorRangesSummary.textContent,/350/);
 console.log('Color-range UI passed: exact device/range/order, unsaved edit protection, server error retention, clearing and slave selection.');
})().catch(error=>{console.error(error);process.exitCode=1});
