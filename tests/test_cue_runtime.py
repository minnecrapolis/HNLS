import copy, json, tempfile, unittest, sys
from pathlib import Path
from multiprocessing import Value
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import numpy as np
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'src/controller/server'))
from libs import song_moments as moments
from libs import music_library
from test_gpio_strings import configuration
class MomentTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name);self.music=self.root/'music';self.music.mkdir();(self.music/'Thriller.mp3').write_bytes(b'fake');(self.music/'Other.mp3').write_bytes(b'other')
        p=patch.object(music_library,'MUSIC_DIR',self.music);p.start();self.addCleanup(p.stop)
        p=patch.object(moments,'store_path',return_value=self.root/'song_moments.json');p.start();self.addCleanup(p.stop)
        moments._CACHE.update(checked=-1.,stamp=None,cues=[])
        self.config=configuration();self.config['device_configs']['device_1']=copy.deepcopy(self.config['device_configs']['device_0']);self.config['device_configs']['device_1'].update(device_name='Remote',led_count=425,output_type='output_udp')
    def cue(self,**kw):return moments.save_moment({'file':'Thriller.mp3','start':184.,'end':184.2,'effect':'flash','targets':['*'],'first':1,'last':None,'color':'#ffffff','color2':'#ff8000','speed':1.,'brightness':100.,'reserve':False,**kw},self.config)
    def device(self,key='device_0',position=184.,filename='Thriller.mp3',stamp=10.):
        return NS(device_config=self.config['device_configs'][key],config=self.config,song_moment_clock=Value('d',stamp),song_moment_position=Value('d',position),song_moment_token=Value('Q',moments.song_token(filename)))
    def test_exact_thriller_boundaries_full_count_all_outputs_other_song_and_replay(self):
        self.cue()
        for key in self.config['device_configs']:
            n=self.config['device_configs'][key]['led_count'];base=np.full((3,n),7,dtype=np.uint8)
            for t,expected in [(183.999,False),(184.,True),(184.1,True),(184.2,False)]:
                out,active=moments.overlay(base,self.device(key,t),now=10.);self.assertEqual(active,expected)
                np.testing.assert_array_equal(out,255 if expected else base)
            out,active=moments.overlay(base,self.device(key,184.,filename='Other.mp3'),now=10.);self.assertFalse(active);np.testing.assert_array_equal(out,base)
            out,active=moments.overlay(base,self.device(key,184.),now=10.);self.assertTrue(active)
    def test_range_112_to_214_inclusive_affects_103_pixels_only_on_selected_line(self):
        self.cue(first=112,last=214,targets=['device_1'])
        d=self.device('device_1');base=np.full((3,425),7,dtype=np.uint8);out,active=moments.overlay(base,d,10.)
        self.assertTrue(active);self.assertEqual(np.count_nonzero(out[0]==255),103);np.testing.assert_array_equal(out[:,111:214],255);np.testing.assert_array_equal(out[:,:111],7);np.testing.assert_array_equal(out[:,214:],7);np.testing.assert_array_equal(base,7)
        out,active=moments.overlay(np.zeros((3,1200)),self.device(),10.);self.assertFalse(active)
    def test_flash_off_phase_scroll_motion_and_last_created_overlap_priority(self):
        self.cue(start=0,end=2,first=1,last=100,color='#ff0000')
        base=np.ones((3,1200),dtype=np.uint8)
        out,_=moments.overlay(base,self.device(position=.3),10.);np.testing.assert_array_equal(out[:,:100],0)
        self.cue(start=0,end=2,effect='color_scroll',first=1,last=32,color='#ff0000',color2='#0000ff')
        a,_=moments.overlay(base,self.device(position=0),10.);b,_=moments.overlay(base,self.device(position=.125),10.)
        np.testing.assert_array_equal(a[:,0],[255,0,0]);np.testing.assert_array_equal(a[:,16],[0,0,255]);self.assertFalse(np.array_equal(a[:,:32],b[:,:32]))
        np.testing.assert_array_equal(a[:,32:100],np.tile([[255],[0],[0]],(1,68)))
    def test_reservation_stays_off_and_jitter_never_leaks_automatic_frame(self):
        self.cue(first=112,last=214,targets=['device_1'],reserve=True)
        base=np.ones((3,425),dtype=np.uint8)*77
        out,active=moments.overlay(base,self.device('device_1',position=183.),10.);self.assertTrue(active);np.testing.assert_array_equal(out[:,111:214],0)
        out,active=moments.overlay(base,self.device('device_1',position=184.),11.);np.testing.assert_array_equal(out[:,111:214],0)
        moments.write({'version':1,'cues':[]});self.cue()
        out,active=moments.overlay(base,self.device('device_1',position=184.),10.19);self.assertTrue(active);np.testing.assert_array_equal(out,255)
        out,active=moments.overlay(base,self.device('device_1',position=184.),11.);self.assertTrue(active);np.testing.assert_array_equal(out,0)
    def test_update_delete_file_identity_and_invalid_payloads_preserve_prior_data(self):
        cue=self.cue();cue['color']='#ff0000';moments.save_moment(cue,self.config);self.assertEqual(len(moments.read()['cues']),1)
        before=moments.read()
        for kw in ({'first':0},{'first':112,'last':214.5},{'last':426},{'targets':[]},{'targets':['*','device_1']},{'file':'../Thriller.mp3'},{'start':True},{'end':184.05},{'brightness':float('nan')},{'color':'bad'},{'effect':'shell'}):
            with self.assertRaises(ValueError):self.cue(**kw)
        self.assertEqual(moments.read(),before)
        with self.assertRaises(ValueError):moments.save_moment({**cue,'file':'Other.mp3'},self.config)
        moments.delete_moment(cue['id']);self.assertEqual(moments.read()['cues'],[])
    def test_no_clock_microphone_token_and_rgbw_explicit_white_clear(self):
        self.cue();base=np.ones((4,1200),dtype=np.uint8)*80
        out,active=moments.overlay(base,NS(),10.);self.assertFalse(active)
        d=self.device(filename=None);out,active=moments.overlay(base,d,10.);self.assertFalse(active)
        out,active=moments.overlay(base,self.device(),10.);np.testing.assert_array_equal(out[:3],255);np.testing.assert_array_equal(out[3],0)
