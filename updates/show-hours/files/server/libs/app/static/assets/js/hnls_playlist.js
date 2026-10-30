(() => {
 'use strict';
 const $=id=>document.getElementById(id);if(!$('hnlsShuffle'))return;
 let busy=false,saving=false,listSignature=null;
 async function request(method='GET',data){
  const response=await fetch(data?'/api/music/playlist-settings':'/api/music/show-preparation',{method,credentials:'same-origin',...(data?{headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{})});
  const body=await response.json();if(!response.ok)throw Error(body.error||'Playlist request failed');return body;
 }
 async function refresh(){
  if(busy)return;busy=true;
  try{
   const data=await request();if(!saving)$('hnlsShuffle').checked=data.settings.shuffle;
   const progress=data.progress||{};
   $('hnlsPreparationStatus').textContent=data.ready+' of '+data.total+' songs analyzed.'+(progress.state==='analyzing'?' Working on: '+progress.file: data.ready===data.total?' Ready for song-aware playback.':' Playback still works while analysis is pending.')+(progress.errors?.length?' Some files could not be analyzed. See the list below.':'');
   const signature=JSON.stringify([data.files,progress.errors]);
   if(signature!==listSignature){
   $('hnlsAnalysisList').replaceChildren();
   const errors=new Map((progress.errors||[]).map(e=>[e.file,e.error]));
   for(const file of data.files){const tr=document.createElement('tr');for(const text of [file.file,file.ready?'Ready · '+file.sections+' passages':errors.has(file.file)?'Could not analyze: '+errors.get(file.file):'Pending',file.tempo?file.tempo+' BPM':'—']){const td=document.createElement('td');if(text===file.file){const play=document.createElement('button');play.type='button';play.className='btn btn-link hnls-song-link text-left';play.textContent=text;play.setAttribute('aria-label','Play '+text);play.addEventListener('click',async()=>{play.disabled=true;try{const response=await fetch('/api/music/play',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({file:file.file})});const result=await response.json();if(!response.ok)throw Error(result.error||'Playback failed');$('hnlsPreparationStatus').textContent='Starting: '+file.file;}catch(error){$('hnlsPreparationStatus').textContent=error.message;}finally{play.disabled=false;}});td.append(play);}else td.textContent=text;tr.append(td);}$('hnlsAnalysisList').append(tr);} listSignature=signature; }
  }catch(error){$('hnlsPreparationStatus').textContent=error.message;}finally{busy=false;}
 }
 $('hnlsShuffle').addEventListener('change',async()=>{
  const desired=$('hnlsShuffle').checked;saving=true;$('hnlsShuffle').disabled=true;
  try{await request('POST',{shuffle:desired});$('hnlsShuffleStatus').textContent=desired?'Shuffle saved. Takes effect at the next song transition.':'Alphabetical order saved. Takes effect at the next song transition.';}
  catch(error){$('hnlsShuffle').checked=!desired;$('hnlsShuffleStatus').textContent=error.message;}
  finally{saving=false;$('hnlsShuffle').disabled=false;}
 });
 $('hnlsPrepare').addEventListener('click',async()=>{ $('hnlsPrepare').disabled=true;try{await request('POST');$('hnlsPreparationStatus').textContent='Analysis queued. Music can keep playing.';await refresh();}catch(error){$('hnlsPreparationStatus').textContent=error.message;}finally{$('hnlsPrepare').disabled=false;} });
 refresh();window.setInterval(refresh,3000);
 // Prepare existing uploads when Music is opened; fresh uploads also queue on the server.
 request('POST').catch(()=>{});
})();
