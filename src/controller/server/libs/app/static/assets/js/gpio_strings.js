(function(){
'use strict';
const $=id=>document.getElementById(id);
if(!$('gpioStringsPanel'))return;
let ready=false,occupied=false;
const message=(text,error=false)=>{$('gpioStringsStatus').textContent=text;$('gpioStringsStatus').className=error?'text-danger':'text-muted';};
async function request(suffix='',data){
 const options={credentials:'same-origin'};
 if(data!==undefined){options.method='POST';options.headers={'Content-Type':'application/json'};options.body=JSON.stringify(data);}
 const response=await fetch('/api/system/gpio-strings'+suffix,options),result=await response.json();
 if(!response.ok)throw Error(result.error||'GPIO request failed');
 return result;
}
async function load(){
 try{
  const state=await request();ready=state.spi.ready;occupied=state.devices.some(d=>d.gpio===10);
  $('gpioStringSource').replaceChildren();
  state.devices.filter(d=>d.gpio===21).forEach(d=>{const option=document.createElement('option');option.value=d.id;option.textContent=d.name+' · '+d.count+' LEDs';$('gpioStringSource').append(option);});
  $('addGpioString').disabled=!ready||occupied||!$('gpioStringSource').children.length;
  message(occupied?'GPIO10 already has a string. Select that device below to change its settings.':ready?'GPIO10 SPI is ready. Enter the new string details.':'GPIO10 needs preparation and a reboot. Your existing GPIO21 string stays configured.');
 }catch(error){message(error.message,true);}
}
$('prepareGpioSpi').addEventListener('click',async()=>{
 if(!confirm('Prepare GPIO10 SPI? This backs up and updates boot settings. A reboot will be needed.'))return;
 $('prepareGpioSpi').disabled=true;
 try{const result=await request('/prepare',{});ready=false;$('addGpioString').disabled=true;message(result.message);}
 catch(error){message(error.message,true);}finally{$('prepareGpioSpi').disabled=false;}
});
$('rebootGpioSpi').addEventListener('click',async()=>{
 if(!confirm('Reboot this Pi now? Music and lights will stop temporarily.'))return;
 try{const result=await request('/reboot',{});message(result.message+' Reopen this page after the Pi returns.');}
 catch(error){message(error.message,true);}
});
$('addGpioString').addEventListener('click',async()=>{
 if(!ready||occupied)return;
 $('addGpioString').disabled=true;
 try{
  const data={source:$('gpioStringSource').value,name:$('gpioStringName').value.trim(),count:Number($('gpioStringCount').value),strip:$('gpioStringOrder').value,brightness:Number($('gpioStringBrightness').value)};
  const result=await request('',data);localStorage.setItem('lastDevice',result.device);message('String added. Loading its device settings…');location.reload();
 }catch(error){message(error.message,true);$('addGpioString').disabled=false;}
});
load();
})();
