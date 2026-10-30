import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import numpy as np

BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'src/controller/server'))
from libs.hnls_playlist import ShuffleQueue,settings,save_settings
from libs import hnls_playlist
from libs.song_analysis import timeline_profile,profile_event,valid_profile,SongShowAnalyzer,VERSION
PKG=BASE/'maintenance/hnls-music-intelligence'
spec=importlib.util.spec_from_file_location('music_installer',PKG/'install_music_intelligence.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class ShuffleTests(unittest.TestCase):
    def test_two_complete_passes_without_immediate_boundary_repeat(self):
        songs=['a.mp3','b.mp3','c.mp3','d.mp3'];queue=ShuffleQueue(random.Random(7));current=songs[0];played=[current]
        for _ in range(7):
            nxt=queue.order(songs,current,1)[0];self.assertNotEqual(nxt,current);queue.selected(nxt);played.append(nxt);current=nxt
        self.assertEqual(len(set(played[:4])),4);self.assertEqual(len(set(played[4:])),4)

    def test_previous_and_forward_retrace_history(self):
        songs=['a','b','c'];q=ShuffleQueue(random.Random(2));b=q.order(songs,'a',1)[0];q.selected(b);c=q.order(songs,b,1)[0];q.selected(c)
        self.assertEqual(q.order(songs,c,-1)[0],b);q.selected(b)
        self.assertEqual(q.order(songs,b,1)[0],c)

    def test_single_file_and_deleted_and_uploaded(self):
        q=ShuffleQueue(random.Random(1));self.assertEqual(q.order(['a'],'a',1),['a']);q.selected('a')
        self.assertEqual(q.order(['a','b'],'a',1)[0],'b');q.selected('b')
        self.assertNotIn('b',q.order(['a','c'],'b',1));self.assertIn('c',q.order(['a','c'],'b',1))

    def test_preferences_persist_and_reject_strings(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(hnls_playlist,'ROOT',Path(tmp)):
            self.assertFalse(settings()['shuffle']);save_settings({'shuffle':True});self.assertTrue(settings()['shuffle'])
            with self.assertRaises(ValueError):save_settings({'shuffle':'true'})
            self.assertTrue(settings()['shuffle'])

class TimelineTests(unittest.TestCase):
    def profile(self,values,step=.064):
        pct=np.percentile(values,[25,50,75,90,95,99],axis=0)
        return {'version':VERSION,'percentiles':{str(p):v.tolist() for p,v in zip([25,50,75,90,95,99],pct)},**timeline_profile(values,step,pct)}

    def test_distinguishes_quiet_and_loud_passages(self):
        values=np.ones((512,4))*.01;values[256:]=[.3,.2,.1,.05]
        p=self.profile(values);self.assertEqual(p['sections'][0]['kind'],'quiet');self.assertEqual(p['sections'][-1]['kind'],'intense');self.assertTrue(valid_profile(p))

    def test_detects_regular_attacks_and_estimates_tempo(self):
        values=np.ones((1024,4))*.001
        for i in range(8,1020,8):values[i:i+2]=[.3,.25,.06,.02]
        p=self.profile(values);self.assertGreater(len(p['beat_times']),90);self.assertTrue(105<p['tempo_bpm']<130,p['tempo_bpm'])
        self.assertTrue(all(b-a>=.24 for a,b in zip(p['beat_times'],p['beat_times'][1:])))

    def test_silence_and_corrupt_profile(self):
        p=self.profile(np.zeros((500,4)));self.assertEqual(p['beat_times'],[]);self.assertIsNone(p['tempo_bpm']);self.assertTrue(valid_profile(p))
        p['sections'][0]['ceiling']=[float('nan')]*4;self.assertFalse(valid_profile(p))

    def test_profile_events_release_and_seek_do_not_replay_old_beats(self):
        self.assertTrue(profile_event([1.,2.],1.02,.04,-10))
        self.assertFalse(profile_event([1.,2.],1.06,.04,1.02))
        self.assertFalse(profile_event([1.,2.],10,.04,-10))
        a=SongShowAnalyzer();self.addCleanup(a.close)
        p=self.profile(np.ones((500,4))*.1);p['beat_times']=[1.];p['heavy_times']=[];a.profile=p;a.position=.98
        feature=a.update([.1,.05,.03,.02],.04);self.assertEqual(feature['beat_count'],1)
        feature=a.update([.1,.05,.03,.02],.04);self.assertEqual(feature['beat_count'],1)

class InstallerTests(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp)/'app';root.mkdir()
        for name in installer.CHANGED:
            if name.endswith('hnls_playlist.py') or name.endswith('hnls_playlist.js'):continue
            relative=name.removeprefix('server/libs/')
            source=(BASE/'maintenance/hnls-interface/files/server/libs'/relative) if relative=='app/templates/home/music.html' else BASE/'src/controller/server/libs'/relative
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        (root/'untouched-output.py').write_text('native color driver remains untouched')
        return root
    def snapshot(self,root):return {str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}

    def test_only_advance_method_changes_and_cues_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);before=self.snapshot(root)
            backup=installer.install(root,PKG,True);after=self.snapshot(root)
            self.assertEqual(before['untouched-output.py'],after['untouched-output.py'])
            def methods(text):
                c=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef));return {n.name:ast.dump(n) for n in c.body if isinstance(n,ast.FunctionDef)}
            old=methods(before['server/libs/audio_process_service.py']);new=methods(after['server/libs/audio_process_service.py'])
            for name in old:
                if name!='_advance_music':self.assertEqual(old[name],new[name],name)
            installer.install(root,PKG,True)
            api=(root/'server/libs/webserver/blueprints/music_library_api.py').read_text()
            self.assertEqual(api.count('def hnls_prepare_library('),1)
            html=(root/'server/libs/app/templates/home/music.html').read_text();self.assertEqual(html.count('id="hnlsShuffle"'),1)
            installer.restore(root,backup);self.assertEqual(self.snapshot(root),before)

    def test_failed_write_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.fixture(tmp);before=self.snapshot(root);replace=Path.replace
            def fail(p,target):
                if str(target).endswith('music.html'):raise OSError('simulated disk failure')
                return replace(p,target)
            with patch.object(Path,'replace',fail):
                with self.assertRaises(OSError):installer.install(root,PKG,True)
            self.assertEqual(self.snapshot(root),before)

    def test_routes_require_authentication_and_use_validated_settings(self):
        tree=ast.parse((PKG/'api_additions.py').read_text());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        self.assertEqual(len(nodes),3)
        for node in nodes:self.assertTrue(any(isinstance(d,ast.Name) and d.id=='login_required' for d in node.decorator_list))

class AdvanceTests(unittest.TestCase):
    def test_shuffle_advances_all_playable_files_and_skips_failed(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(hnls_playlist,'ROOT',Path(tmp)/'.settings'):
            root=Path(tmp);songs=['a.mp3','b.mp3','c.mp3','bad.mp3']
            for name in songs:(root/name).touch()
            save_settings({'shuffle':True})
            scope={'safe_music_path':lambda n:root/n,'logger':Mock(),'write_status':Mock()}
            exec((PKG/'advance_music.py').read_text(),scope)
            service=scope['AudioProcessService']();service._music_file='a.mp3';service._music_failed_files={'bad.mp3'};service._music_had_samples=True
            service._start_music=lambda name:setattr(service,'_music_file',name) or True
            played=['a.mp3']
            for _ in range(2):service._advance_music();played.append(service._music_file)
            self.assertEqual(set(played),{'a.mp3','b.mp3','c.mp3'})
            service._advance_music();self.assertNotEqual(service._music_file,played[-1]);self.assertNotEqual(service._music_file,'bad.mp3')

if __name__=='__main__':unittest.main()
