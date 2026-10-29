(function(){
'use strict';
const $=id=>document.getElementById(id);
if(!$('remotePiPanel'))return;
const message=(text,error=false)=>{$('remotePiStatus').textContent=text;$('remotePiStatus').className=(error?'text-danger':'text-muted')+' mt-3';};
async function request(suffix='',data){
 const options={credentials:'same-origin'};
 if(data!==undefined){options.method='POST';options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(data);}
 const response=await fetch('/api/system/remote-pis'+suffix,options),result=await response.json();
 if(!response.ok)throw Error(result.error||'Remote Pi request failed');
 return result;
}
async function load(){
 try{
  const state=await request();$('remotePiSource').replaceChildren();$('remotePiList').replaceChildren();
  state.sources.forEach(source=>{const option=document.createElement('option');option.value=source.id;option.textContent=source.name;$('remotePiSource').append(option);});
  $('addRemotePi').disabled=!state.sources.length;
  state.nodes.forEach(node=>{
   const row=document.createElement('p'),label=document.createElement('span'),button=document.createElement('button');
   label.textContent=node.name+' · '+node.host+' ';button.textContent='Check connection';button.type='button';button.className='btn btn-sm btn-outline-primary';
   button.addEventListener('click',async()=>{
    button.disabled=true;
    try{const status=await request('/status',{device:node.device});message(status.hostname+': '+(status.error|| (status.receiving?'receiving frames':'connected; waiting for frames'))+' · '+status.frames+' frames received');}
    catch(error){message(error.message,true);}finally{button.disabled=false;}
   });
   row.append(label,button);$('remotePiList').append(row);
  });
  message(state.nodes.length?'Remote Pis are listed below. Select a device to adjust its light show.':'Enter the receiver’s address, key and LED count to pair it.');
 }catch(error){message(error.message,true);}
}
$('addRemotePi').addEventListener('click',async()=>{
 $('addRemotePi').disabled=true;message('Checking receiver and adding the string…');
 try{
  const result=await request('',{host:$('remotePiHost').value.trim(),key:$('remotePiKey').value.trim(),name:$('remotePiName').value.trim(),source:$('remotePiSource').value,count:Number($('remotePiCount').value),order:$('remotePiOrder').value,brightness:Number($('remotePiBrightness').value)});
  $('remotePiKey').value='';localStorage.setItem('lastDevice',result.device);message('Paired with '+result.hostname+'. Loading its settings…');location.reload();
 }catch(error){message(error.message,true);$('addRemotePi').disabled=false;}
});
load();
})();
