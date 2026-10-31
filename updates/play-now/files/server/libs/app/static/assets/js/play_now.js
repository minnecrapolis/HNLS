(function () {
    'use strict';
    const $=id=>document.getElementById(id),play=$('hnlsPlayNow'),stop=$('hnlsStopShow'),status=$('hnlsPlayNowStatus');
    if(!play||!stop||!status)return;
    let busy=false,polling=false,generation=0;
    function show(value){
        const note=value.error?' Schedule needs attention: '+value.error:'';
        status.textContent=(value.message||'Your saved show hours are unchanged.')+note;
    }
    async function command(action){
        if(busy)return;generation++;busy=true;play.disabled=true;stop.disabled=true;
        try{
            const response=await fetch('/api/music/show-now',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({action})});
            const value=await response.json();if(!response.ok)throw Error(value.error||'Show command failed.');
            show(value);
        }catch(error){status.textContent=error.message;}
        finally{busy=false;play.disabled=false;stop.disabled=false;}
    }
    play.addEventListener('click',()=>command('play'));stop.addEventListener('click',()=>command('stop'));
    async function refresh(){
        if(polling||busy)return;polling=true;const stamp=generation;
        try{
            const response=await fetch('/api/music/show-schedule',{credentials:'same-origin',cache:'no-store'});
            const value=await response.json();if(!response.ok)throw Error(value.error||'Schedule status unavailable.');
            if(!busy&&stamp===generation)show(value);
        }catch(error){if(!busy&&stamp===generation)status.textContent='Status unavailable. Play now and Stop show can still be tried. '+error.message;}
        finally{polling=false;}
    }
    refresh();window.setInterval(refresh,5000);
}());
