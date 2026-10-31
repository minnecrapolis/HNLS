(() => {
 'use strict';
 const $=id=>document.getElementById(id);if(!$('colorRangesForm'))return;
 let outputs=[],selected=null,dirty=false,busy=false;
 function message(text){$('colorRangesStatus').textContent=text;}
 async function request(data){const response=await fetch('/api/system/color-ranges',{credentials:'same-origin',...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{})});const result=await response.json();if(!response.ok)throw Error(result.error||'Color-range request failed');return result;}
 function input(type,value,label){const el=document.createElement('input');el.type=type;el.className='form-control';el.value=value??'';el.setAttribute('aria-label',label);el.addEventListener('input',()=>dirty=true);return el;}
 function addRow(row={}){
  if(!selected)return;
  if($('colorRangesRows').children.length>=100){message('Use at most 100 ranges per output.');return;}
  const tr=document.createElement('tr'),name=input('text',row.name,'Range name');name.maxLength=60;
  const first=input('number',row.first,'First LED'),last=input('number',row.last,'Last LED');for(const el of [first,last]){el.min=1;el.max=selected.count;el.step=1;el.required=true;}
  const order=document.createElement('select');order.className='form-control';order.setAttribute('aria-label','Physical color order for this range');for(const text of ['RGB','RBG','GRB','GBR','BRG','BGR']){const option=document.createElement('option');option.value=text;option.textContent=text;order.append(option);}order.value=row.order||selected.base_order||'RGB';order.addEventListener('change',()=>dirty=true);
  const remove=document.createElement('button');remove.type='button';remove.className='btn btn-outline-danger';remove.textContent='Remove';remove.addEventListener('click',()=>{tr.remove();dirty=true;});
  for(const el of [name,first,last,order,remove]){const td=document.createElement('td');td.append(el);tr.append(td);}
  tr.fields={name,first,last,order};$('colorRangesRows').append(tr);
 }
 function display(id){
  selected=outputs.find(o=>o.id===id)||null;$('colorRangesRows').replaceChildren();dirty=false;
  $('colorRangesSave').disabled=!selected?.supported;$('colorRangesAdd').disabled=!selected?.supported;$('colorRangesClear').disabled=!selected;
  if(!selected){message('Add an output in Device Settings first.');return;}
  $('colorRangesSummary').textContent=selected.name+' · '+selected.count+' LEDs · default '+(selected.base_order||selected.strip_type)+'. Unlisted LEDs inherit this default.';
  for(const row of Array.isArray(selected.ranges)?selected.ranges:[])addRow(row);
  message(selected.error?'Saved range needs attention: '+selected.error:selected.supported?'Add only the ranges with a different physical order, then Save. Playback keeps running.':'Choose an explicit RGB/GRB/RBG/GBR/BRG/BGR strip type in this output’s Configuration panel, save it, then Reload outputs. RGBW and unresolved strip aliases are not supported by this range editor.');
 }
 async function load(){
  if(busy)return;
  if(dirty&&!confirm('Discard unsaved color-range edits and reload?'))return;
  busy=true;try{const data=await request();const wanted=selected?.id;outputs=data.outputs;$('colorRangesOutput').replaceChildren();for(const output of outputs){const option=document.createElement('option');option.value=output.id;option.textContent=output.name+' · '+output.count+' LEDs';$('colorRangesOutput').append(option);}$('colorRangesOutput').value=outputs.some(o=>o.id===wanted)?wanted:outputs[0]?.id||'';display($('colorRangesOutput').value);}catch(error){message(error.message);}finally{busy=false;}
 }
 $('colorRangesOutput').addEventListener('change',()=>{const id=$('colorRangesOutput').value;if(dirty&&!confirm('Discard unsaved color-range edits?')){$('colorRangesOutput').value=selected?.id||'';return;}display(id);});
 $('colorRangesReload').addEventListener('click',load);
 $('colorRangesAdd').addEventListener('click',()=>{addRow();dirty=true;});
 $('colorRangesClear').addEventListener('click',()=>{$('colorRangesRows').replaceChildren();dirty=true;$('colorRangesSave').disabled=!selected;message('Ranges cleared in the editor. Save to restore the output default everywhere.');});
 $('colorRangesForm').addEventListener('submit',async event=>{
  event.preventDefault();if(busy||!selected)return;busy=true;$('colorRangesSave').disabled=true;
  try{const ranges=Array.from($('colorRangesRows').children).map(tr=>({name:tr.fields.name.value,first:Number(tr.fields.first.value),last:Number(tr.fields.last.value),order:tr.fields.order.value}));const data=await request({device:selected.id,ranges});selected.ranges=data.ranges;const id=selected.id;display(id);message('Saved. Outgoing frames will use these ranges; music does not restart.');}
  catch(error){message(error.message);}finally{busy=false;$('colorRangesSave').disabled=!selected?.supported;}
 });
 load();
})();
