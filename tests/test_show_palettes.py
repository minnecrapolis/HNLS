import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/controller/server'))
from libs.show_palettes import PALETTES,COLOR_KEYS,EXTRA_COLORS,SHOW_MODES
from libs.section_sync import DEFAULT_SYNC,validate_sync_settings
from libs.show_director import ShowDirector
from libs.song_analysis import SongShowAnalyzer,spectrum_levels,MUSICAL_BANDS
from libs.effects.effect_song_show import SongShowRenderer

def features(**changes):
    value=dict(song_id='Garden.mp3:1',position=0.,bass=.7,mid=.7,treble=.7,energy=.6,audible=True,
                beat_count=0,heavy_count=0,last_heavy=-10.,section_kind='live',section_energy=.6,tempo=120)
    value.update(changes);return value

class PaletteTests(unittest.TestCase):
    def test_every_recipe_has_ten_valid_colors_and_preserves_limits(self):
        self.assertEqual(len(PALETTES),14);self.assertEqual(len(COLOR_KEYS),10)
        for p in PALETTES:
            value=validate_sync_settings(1200,{**DEFAULT_SYNC,**p['colors'],'palette_preset':p['id'],'max_lit_leds':97})
            self.assertEqual(set(p['colors']),set(COLOR_KEYS));self.assertEqual(value['max_lit_leds'],97)
            self.assertEqual(value['sync_mode'],'paired');self.assertEqual(value['show_mode'],'classic')
    def test_old_settings_still_valid_and_invalid_new_fields_rejected(self):
        old={k:v for k,v in DEFAULT_SYNC.items() if k not in EXTRA_COLORS and k not in ('expanded_bands','show_mode','palette_preset')}
        result=validate_sync_settings(1200,old);self.assertEqual(result['show_mode'],'classic');self.assertFalse(result['expanded_bands'])
        for change in [{'show_mode':'random_strobe'},{'palette_preset':'unknown'},{'expanded_bands':'true'},{'brilliance_color':'blue'}]:
            with self.assertRaises(ValueError):validate_sync_settings(1200,{**old,**change})
    def test_legacy_schema_required_fields_and_new_optional_properties(self):
        tree=ast.parse((ROOT/'src/controller/server/libs/webserver/schemas/config_validator_service.py').read_text())
        end=next(n.lineno for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='effect_schema' for t in n.targets))
        nodes=[n for n in tree.body if n.lineno<=end and isinstance(n,(ast.Import,ast.ImportFrom,ast.Assign))]
        nodes=[n for n in nodes if not isinstance(n,ast.ImportFrom) or n.module=='libs.show_palettes']
        # Execute only declarations preceding the validator class (no jsonschema dependency).
        scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),'schema.py','exec'),scope)
        schema=scope['effect_schema']['properties']['effect_song_show'];self.assertEqual(schema['maxProperties'],17)
        self.assertNotIn('show_mode',schema['required']);self.assertIn('brilliance_color',schema['properties'])

class SettingsSaveTests(unittest.TestCase):
    def test_saving_new_fields_to_legacy_device_uses_non_audio_refresh(self):
        import __future__
        from libs.notification_enum import NotificationEnum
        tree=ast.parse((ROOT/'src/controller/server/libs/webserver/blueprints/effect_settings_executer.py').read_text())
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='set_effect_settings')
        scope={'validate_sync_settings':validate_sync_settings,'NotFound':object(),'BadRequest':object(),'NotificationEnum':NotificationEnum}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'save.py','exec',flags=__future__.annotations.compiler_flag),scope)
        old={k:v for k,v in DEFAULT_SYNC.items() if k not in EXTRA_COLORS and k not in ('expanded_bands','show_mode','palette_preset')}
        d={'led_count':750,'led_brightness':30,'effects':{'effect_song_show':old}}
        ex=NS(_config={'device_configs':{'device_1':d}},update_cycle_job=Mock(),save_config=Mock(),put_into_notification_queue=Mock(),refresh_device=Mock())
        result=scope['set_effect_settings'](ex,'device_1','effect_song_show',{'show_mode':'auto','expanded_bands':True,**PALETTES[0]['colors'],'palette_preset':'christmas'})
        self.assertEqual(result['settings']['show_mode'],'auto');self.assertEqual(d['effects']['effect_song_show']['palette_preset'],'christmas');self.assertEqual(d['led_count'],750);self.assertEqual(d['led_brightness'],30)
        ex.refresh_device.assert_not_called();ex.put_into_notification_queue.assert_called_once_with(NotificationEnum.song_show_refresh,'device_1')

class AnalysisTests(unittest.TestCase):
    def test_frequency_tones_peak_in_their_own_band(self):
        rate,n=48000,48000;t=np.arange(n)/rate;window=np.ones(n)
        for index,tone in enumerate((40,120,350,1000,3000,5000,8000,12000)):
            magnitude=abs(np.fft.rfft(np.sin(2*np.pi*tone*t)*.2))
            values=spectrum_levels(magnitude,rate,n,float(np.sum(window**2)),bands=MUSICAL_BANDS)
            self.assertEqual(int(np.argmax(values)),index);self.assertAlmostEqual(float(values[index]),.2/np.sqrt(2),places=5)
    def test_band_normalization_silence_and_song_reset(self):
        a=SongShowAnalyzer();f=a.update([.1,.06,.04,.02],.04,bands=[.1,0,0,0,0,0,0,0]);self.assertGreater(f['bands'][0],.9);self.assertEqual(f['bands'][1:], [0.]*7)
        f=a.update([0,0,0,0],.04,bands=[1]*8);self.assertEqual(f['bands'],[0.]*8)
        a.start_song(None);np.testing.assert_array_equal(a.band_peaks,np.full(8,.04));self.assertIsNone(a.update([.1,.05,.05,.05],.04)['bands'])

class DirectorTests(unittest.TestCase):
    def test_dynamics_change_choices_without_frame_rate_driven_randomization(self):
        quiet=ShowDirector().choose(features(section_kind='quiet',section_energy=.1));self.assertIn(quiet,['pulse','comets','bounce'])
        intense=ShowDirector().choose(features(section_kind='intense',section_energy=.9));self.assertIn(intense,['ribbons','chase','bounce','sparkle'])
        a=ShowDirector();first=a.choose(features())
        self.assertEqual(a.choose(features(position=7.9,section_kind='intense',beat_count=32)),first)
        second=a.choose(features(position=8.,section_kind='intense',beat_count=32,section_energy=.9));self.assertNotEqual(first,second)
        # Extra render calls before a phrase must not change the chosen plan.
        b=ShowDirector();b.choose(features(song_id='Garden.mp3:other'))
        for t in np.arange(.04,7.9,.04):b.choose(features(song_id='Garden.mp3:other',position=float(t)))
        self.assertEqual(b.choose(features(song_id='Garden.mp3:other',position=8.,section_kind='intense',beat_count=32,section_energy=.9)),second)
    def test_live_fallback_varies_at_phrases_and_not_every_frame(self):
        a=ShowDirector();effects=[]
        for p in (0,20,40,60):effects.append(a.choose(features(position=p,tempo=None)))
        self.assertTrue(all(x in SHOW_MODES for x in effects));self.assertGreater(len(set(effects)),1)

class RendererTests(unittest.TestCase):
    def test_every_motion_obeys_physical_count_sync_and_ordinary_limit(self):
        for mode in SHOW_MODES:
            r=SongShowRenderer(1200,settings={'show_mode':mode,'max_lit_leds':60,'sync_mode':'paired','expanded_bands':True})
            f=features();f['bands']=[.8]*8
            frame=r.render(f,now=1.)
            self.assertEqual(frame.shape,(3,1200));self.assertEqual(frame.dtype,np.uint8);self.assertLessEqual(np.count_nonzero(np.any(frame>0,axis=0)),60)
            np.testing.assert_array_equal(frame[:,:50],frame[:,-50:])
    def test_each_of_eight_isolated_bands_uses_its_own_color(self):
        for i,key in enumerate(COLOR_KEYS[:8]):
            colors={k:'#000000' for k in COLOR_KEYS};colors[key]='#ff0000'
            r=SongShowRenderer(600,settings={**colors,'expanded_bands':True,'show_mode':'waves','sync_mode':'independent'})
            f=features();f.update(bands=[float(n==i) for n in range(8)],bass=0,mid=0,treble=0)
            out=r.render(f,now=1.);self.assertGreater(int(out[0].max()),0,key);self.assertEqual(int(out[1:].max()),0,key)
    def test_power_exception_does_not_leave_a_full_strip_trail(self):
        r=SongShowRenderer(350,settings={'show_mode':'auto','max_lit_leds':20,'power_color':'#ffffff','sync_mode':'independent'})
        f=features();f.update(position=1.,last_heavy=1.,heavy_count=1)
        full=r.render(f,now=1.);self.assertEqual(np.count_nonzero(np.any(full>0,axis=0)),350)
        f.update(position=1.13);after=r.render(f,now=1.13);self.assertLessEqual(np.count_nonzero(np.any(after>0,axis=0)),20)
    def test_classic_output_is_identical_to_rc8_reference(self):
        source=(ROOT/'updates/designer-effects/files/server/libs/effects/effect_song_show.py')
        # rc.8 renderer is recorded as the new updater's supported baseline;
        # compare against its extracted golden source fixture below if present.
        golden=ROOT/'tests/fixtures/rc8_effect_song_show.py.txt'
        if not golden.exists():self.fail('Missing reference renderer')
        scope={};exec(compile(golden.read_text(),'reference.py','exec'),scope)
        old=scope['SongShowRenderer'](350,settings={'sync_mode':'independent'});new=SongShowRenderer(350,settings={'sync_mode':'independent'})
        for i in range(40):
            f=features();f.update(position=i*.04,beat_count=i//8)
            np.testing.assert_array_equal(new.render(f,now=i*.04),old.render(f,now=i*.04))

if __name__=='__main__':unittest.main()
