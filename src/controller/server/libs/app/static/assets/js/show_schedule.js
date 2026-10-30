(() => {
 'use strict';
 const $=id=>document.getElementById(id);if(!$('hnlsScheduleForm'))return;
 let loading=false,ready=false;
 async function request(data){
  const response=await fetch('/api/music/show-schedule',{credentials:'same-origin',...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{})});
  const value=await response.json();if(!response.ok)throw Error(value.error||'Schedule request failed');return value;
 }
 function status(value){
  $('hnlsScheduleClock').textContent=value.local_time?'Show clock: '+value.local_time.replace('T',' '):'';
  $('hnlsScheduleStatus').textContent=value.error?'Schedule error: '+value.error:value.message||'';
 }
 async function refresh(){
  if(loading)return;loading=true;
  try{const value=await request();status(value);if(!ready&&value.settings){const s=value.settings;$('hnlsScheduleEnabled').checked=s.enabled;$('hnlsScheduleStart').value=s.start;$('hnlsScheduleEnd').value=s.end;$('hnlsScheduleTimezone').value=s.timezone;for(let d=0;d<7;d++)$('hnlsScheduleDay'+d).checked=s.days.includes(d);ready=true;$('hnlsScheduleSave').disabled=false;}}
  catch(error){$('hnlsScheduleStatus').textContent=error.message;}finally{loading=false;}
 }
 $('hnlsScheduleForm').addEventListener('submit',async event=>{
  event.preventDefault();$('hnlsScheduleSave').disabled=true;
  const days=[];for(let d=0;d<7;d++)if($('hnlsScheduleDay'+d).checked)days.push(d);
  const data={enabled:$('hnlsScheduleEnabled').checked,days,start:$('hnlsScheduleStart').value,end:$('hnlsScheduleEnd').value,timezone:$('hnlsScheduleTimezone').value.trim()};
  try{const result=await request(data);status(result);$('hnlsScheduleStatus').textContent='Schedule saved. '+(result.error?'Action error: '+result.error:result.message);}
  catch(error){$('hnlsScheduleStatus').textContent=error.message;}finally{$('hnlsScheduleSave').disabled=false;}
 });
 refresh();window.setInterval(refresh,10000);
})();
