/* Song Show controls; uses the existing authenticated settings and effect APIs. */
(function () {
    'use strict';
    const colorKeys = ['subbass_color','bass_color','lowmid_color','mid_color','uppermid_color','presence_color','treble_color','brilliance_color','beat_color','power_color'];
    const defaults = {section_size: 50, sync_mode: 'paired', sync_groups: [], max_lit_leds: 0,
        bass_color: '#ff2106', mid_color: '#05adff', treble_color: '#991fff',
        beat_color: '#ff8500', power_color: '#ff3300', subbass_color:'#ff2106', lowmid_color:'#05adff',
        uppermid_color:'#05adff', presence_color:'#991fff', brilliance_color:'#991fff',
        expanded_bands:false, show_mode:'classic', palette_preset:'custom'};

    function presetGroups(mode, count) {
        return Array.from({length: count}, (_, i) => mode === 'paired' ? Math.min(i, count-1-i)+1 :
            mode === 'adjacent' ? Math.floor(i/2)+1 : mode === 'alternating' ? i%2+1 :
            mode === 'all' ? 1 : i+1);
    }
    function compactGroups(groups) {
        const labels = new Map();
        return groups.map(g => {if (!labels.has(g)) labels.set(g, labels.size+1); return labels.get(g);});
    }
    function validate(settings, ledCount) {
        if (!Number.isInteger(settings.section_size) || settings.section_size < 1 || settings.section_size > 5000)
            throw Error('Enter a section size between 1 and 5,000.');
        if (!['paired','independent','all','custom','auto'].includes(settings.sync_mode)) throw Error('Choose a sync mode.');
        if (!Number.isInteger(settings.max_lit_leds) || settings.max_lit_leds < 0 || settings.max_lit_leds > ledCount)
            throw Error(`The LED limit must be between 1 and ${ledCount}, or use automatic coverage.`);
        if (!['classic','auto','comets','waves','ribbons','chase','sparkle','pulse','bounce'].includes(settings.show_mode || 'classic')) throw Error('Choose a show mode.');
        if (settings.expanded_bands !== undefined && typeof settings.expanded_bands !== 'boolean') throw Error('Choose expanded bands on or off.');
        const count = Math.ceil(ledCount/settings.section_size);
        if (settings.sync_mode === 'custom' && (settings.sync_groups.length !== count ||
            settings.sync_groups.some(g => !Number.isInteger(g) || g < 1 || g > 5000)))
            throw Error('Assign a sync group to every section.');
        colorKeys.forEach(k => {if (!/^#[0-9a-f]{6}$/i.test(settings[k])) throw Error('Choose a valid color for every band.');});
        return settings;
    }
    function applyPalette(settings, preset) {
        const result = {...settings};
        colorKeys.forEach(k => {if (!/^#[0-9a-f]{6}$/i.test(preset.colors[k])) throw Error('Invalid preset colors.'); result[k] = preset.colors[k];});
        result.palette_preset = preset.id; result.expanded_bands = true;
        return result;
    }
    const pure = {presetGroups, compactGroups, validate, applyPalette, defaults, colorKeys};
    if (typeof module !== 'undefined' && module.exports) module.exports = pure;
    if (typeof document === 'undefined') return;

    document.addEventListener('DOMContentLoaded', async () => {
        const el = id => document.getElementById(id);
        if (!el('syncDevice')) return;
        let ledCount = 0, customGroups = [], loaded = false, loadToken = 0;
        let requestBusy = false, palettes = [];
        const device = el('syncDevice');
        const descriptions = {
            paired: 'The first section matches the last, the second matches the second-last, and so on.',
            independent: 'Every section has its own place in the show. No sections are linked.',
            all: 'Every section repeats the same animation in the same pixel order.',
            custom: 'Give sections the same group number to synchronize them. Different groups move independently.',
            auto: 'The music chooses grouping patterns at phrase changes, with a minimum of 8 seconds between changes. This preview shows one possible arrangement, not live grouping.'
        };
        function status(text, error=false) {
            el('syncStatus').textContent = text;
            el('syncStatus').className = `alert mt-3 ${error ? 'alert-danger' : 'alert-success'}`;
        }
        async function api(url, options={}) {
            const response = await fetch(url, {credentials:'same-origin', ...options});
            if (!response.ok) throw Error(`Request failed (${response.status}). Check your connection and sign-in.`);
            return response.json();
        }
        function sectionCount() {return Math.ceil(ledCount/Number(el('sectionSize').value || 50));}
        function activeGroups() {
            const mode = el('syncMode').value;
            return mode === 'custom' ? customGroups : presetGroups(mode === 'auto' ? 'paired' : mode, sectionCount());
        }
        function readSettings() {
            const automatic = el('automaticDensity').checked;
            if (!automatic && (!Number.isInteger(Number(el('maxLit').value)) || Number(el('maxLit').value) < 1))
                throw Error('Choose at least 1 LED, or turn on automatic coverage.');
            const settings = {section_size:Number(el('sectionSize').value), sync_mode:el('syncMode').value,
                sync_groups:[...customGroups], max_lit_leds:automatic ? 0 : Number(el('maxLit').value),
                expanded_bands:el('expandedBands').checked, show_mode:el('showMode').value, palette_preset:el('holidayPalette').value};
            colorKeys.forEach(k => settings[k] = el(k).value);
            return validate(settings, ledCount);
        }
        function showColors(settings) {
            colorKeys.forEach(k => {el(k).value=settings[k];document.querySelector(`[data-color-label="${k}"]`).textContent=settings[k].toUpperCase();});
            el('holidayPalette').value=settings.palette_preset || 'custom';
            el('expandedBands').checked=!!settings.expanded_bands;
        }
        function modeHelp() {
            el('showModeHelp').textContent=el('showMode').value==='auto' ?
                'Analysis-directed: chooses comets, waves, ribbons, chases, twinkles, pulses and bounces from tempo and quiet/loud passages. Changes are phrase-paced, at least 8 seconds apart. Your colors, grouping, LED limit and saved moments stay in control.' :
                'Classic keeps the existing choreography. A named motion holds that movement while it reacts to the music. Prepared song analysis is used when available; streaming uses live analysis.';
        }
        function groupColor(group) {return `hsl(${(group*137.508)%360} 65% 55%)`;}
        function updateDensity() {
            const automatic = el('automaticDensity').checked;
            el('maxLit').disabled = automatic;
            const maximum = Number(el('maxLit').value);
            el('densityHelp').textContent = automatic ?
                `Automatic coverage varies up to about ${Math.floor(ledCount*.4)} of ${ledCount} LEDs; quiet sections use fewer.` :
                `Ordinary frames stay at or below ${maximum} of ${ledCount} LEDs. This is a maximum, not a target.`;
            const groups = activeGroups();
            const repeats = new Map();
            groups.forEach(g => repeats.set(g, (repeats.get(g)||0)+1));
            const largest = Math.max(1, ...repeats.values());
            el('groupLimitWarning').textContent = !automatic && maximum < largest ?
                `Some linked groups repeat each pixel ${largest} times. If the limit is smaller, those groups may stay dark to honor your limit.` : '';
        }
        function drawPreview(groups) {
            const canvas = el('syncPreview'), context = canvas.getContext('2d');
            if (!context) return;
            context.fillStyle = '#0c1423'; context.fillRect(0,0,canvas.width,canvas.height);
            const size = Number(el('sectionSize').value);
            groups.forEach((g, i) => {
                const x = i*size/ledCount*canvas.width;
                const width = Math.min(size,ledCount-i*size)/ledCount*canvas.width;
                context.fillStyle = groupColor(g); context.fillRect(x+1,12,Math.max(1,width-2),48);
                if (width>28) {context.fillStyle='#101827';context.font='bold 13px sans-serif';context.textAlign='center';context.fillText(String(i+1),x+width/2,42);}
            });
        }
        function renderGroups() {
            if (!loaded) return;
            const size = Number(el('sectionSize').value);
            if (!Number.isInteger(size) || size<1 || size>5000) return;
            const count = sectionCount(), mode = el('syncMode').value;
            if (customGroups.length !== count) customGroups = presetGroups('paired',count);
            const groups = activeGroups(), grid = el('sectionGrid');
            grid.replaceChildren();
            groups.forEach((g,i) => {
                const card = document.createElement('div');card.className='sync-section';
                card.style.setProperty('--group-color',groupColor(g));
                const title=document.createElement('strong');title.textContent=`Section ${i+1}`;
                const range=document.createElement('small');range.textContent=`LEDs ${i*size+1}–${Math.min(ledCount,(i+1)*size)}`;
                const numeric=mode==='custom'&&count>100;
                const select=document.createElement(numeric?'input':'select');select.className='form-control form-control-sm';
                if(numeric){select.type='number';select.min=1;select.max=count;select.step=1;}
                select.setAttribute('aria-label',`Sync group for section ${i+1}`);
                select.disabled=mode!=='custom';
                // Non-custom sections are labels; avoid generating a large disabled dropdown.
                const options=numeric?[]:mode==='custom' ? Array.from({length:count},(_,n)=>n+1) : [g];
                options.forEach(n => {const option=document.createElement('option');option.value=n;option.textContent=`Group ${n}`;select.append(option);});
                select.value=g;
                select.addEventListener('change',()=>{
                    const value=Number(select.value);
                    if(!Number.isInteger(value)||value<1||value>count){select.value=customGroups[i];status(`Choose a group number between 1 and ${count}.`,true);return;}
                    customGroups[i]=value;renderGroups();
                });
                card.append(title,range,select);grid.append(card);
            });
            el('syncDescription').textContent=descriptions[mode];
            el('syncSummary').textContent=`${ledCount.toLocaleString()} LEDs · ${count} sections · ${new Set(groups).size} ${mode==='auto'?'preview groups':'sync groups'}`;
            drawPreview(groups);updateDensity();
        }
        async function load() {
            const token=++loadToken;loaded=false;el('songShowControls').disabled=true;
            try {
                const id=encodeURIComponent(device.value);
                const [configuration,response]=await Promise.all([
                    api(`/api/settings/device?device=${id}&excluded_key=effects`),
                    api(`/api/settings/effect?device=${id}&effect=effect_song_show`)
                ]);
                if(token!==loadToken)return;
                ledCount=configuration.settings.led_count;
                const settings={...defaults,...response.settings};
                el('sectionSize').value=settings.section_size;el('syncMode').value=settings.sync_mode;
                const count=Math.ceil(ledCount/settings.section_size);
                customGroups=settings.sync_groups.length===count ? compactGroups(settings.sync_groups) : presetGroups('paired',count);
                el('maxLit').max=ledCount;el('maxLit').value=Math.min(ledCount,settings.max_lit_leds||Math.max(1,Math.floor(ledCount*.4)));
                el('automaticDensity').checked=settings.max_lit_leds===0;
                showColors(settings);el('showMode').value=settings.show_mode;modeHelp();
                localStorage.setItem('lastDevice',device.value);
                loaded=true;el('songShowControls').disabled=false;status('');renderGroups();
            } catch(error) {if(token===loadToken)status(error.message,true);}
        }
        const last=localStorage.getItem('lastDevice');
        if([...device.options].some(o=>o.value===last))device.value=last;
        if(!device.options.length){status('Create an LED device first.',true);return;}
        device.addEventListener('change',load);
        el('syncMode').addEventListener('change',renderGroups);
        el('sectionSize').addEventListener('change',renderGroups);
        el('automaticDensity').addEventListener('change',updateDensity);
        el('maxLit').addEventListener('input',updateDensity);
        colorKeys.forEach(k=>el(k).addEventListener('input',()=>{
            document.querySelector(`[data-color-label="${k}"]`).textContent=el(k).value.toUpperCase();
            el('holidayPalette').value='custom';
            if (['subbass_color','lowmid_color','uppermid_color','presence_color','brilliance_color'].includes(k)) el('expandedBands').checked=true;
        }));
        el('showMode').addEventListener('change',modeHelp);
        el('holidayPalette').addEventListener('change',()=>{
            const preset=palettes.find(p=>p.id===el('holidayPalette').value);
            if (!preset) return;
            showColors(applyPalette(defaults,preset));
            status('Holiday colors selected. You can adjust any color; click Save & use this look to apply them. Grouping, coverage and show mode are unchanged.');
        });
        document.querySelectorAll('[data-preset]').forEach(button=>button.addEventListener('click',()=>{
            const preset=button.dataset.preset;
            customGroups=presetGroups(preset,sectionCount());
            el('syncMode').value=['paired','independent','all'].includes(preset)?preset:'custom';renderGroups();
        }));
        async function send(url,body){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});}
        el('saveSongShow').addEventListener('click',async()=>{
            if(requestBusy||!loaded)return;
            try {
                const settings=readSettings();requestBusy=true;device.disabled=true;el('songShowControls').disabled=true;
                await send('/api/settings/effect',{device:device.value,effect:'effect_song_show',settings});
                try {
                    await send('/api/effect/active',{device:device.value,effect:'effect_song_show'});
                    status('Saved and applied to this light string. Music keeps playing.');
                } catch(error) {status('Your settings were saved, but the Light Show could not be turned on. Try Use last saved look. '+error.message,true);}
            } catch(error){status(error.message,true);}
            finally {requestBusy=false;device.disabled=false;el('songShowControls').disabled=false;updateDensity();}
        });
        el('activateSongShow').addEventListener('click',async()=>{
            if(requestBusy||!loaded)return;
            try{await send('/api/effect/active',{device:device.value,effect:'effect_song_show'});status('Your last saved Light Show is active. Use Save & use this look to apply unsaved changes.');}
            catch(error){status(error.message,true);}
        });
        try {
            const catalog=await api('/api/music/show-palettes');palettes=catalog.palettes;
            palettes.forEach(p=>{const option=document.createElement('option');option.value=p.id;option.textContent=p.name;el('holidayPalette').append(option);});
        } catch(error) {status('Could not load holiday palettes: '+error.message,true);return;}
        await load();
    });
})();
