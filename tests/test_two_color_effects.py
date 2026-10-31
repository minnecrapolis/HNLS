import copy,unittest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/controller/server'))
from libs import song_moments as m
class TwoColorEffects(unittest.TestCase):
 def cue(self,effect,enabled=True):return {'effect':effect,'color':'#ff0000','color2':'#0000ff','speed':1,'cycle_seconds':8,'band_width':8,'direction':'forward','brightness':100,'use_color2':enabled}
 def test_flash_alternates_both_colors(self):
  c=self.cue('flash');np.testing.assert_array_equal(m.render_cue(c,51,0),np.tile([[255],[0],[0]],(1,51)));np.testing.assert_array_equal(m.render_cue(c,51,4),np.tile([[0],[0],[255]],(1,51)))
 def test_bounce_comet_chase_wipe_use_second_color_background(self):
  for effect in ['bounce','comet','chase','wipe']:
   with self.subTest(effect=effect):
    out=m.render_cue(self.cue(effect),51,2)
    self.assertTrue(np.any(out[0]>0));self.assertTrue(np.any(out[2]>0));np.testing.assert_array_equal(out[1],0)
    np.testing.assert_allclose(out[0]+out[2],255)
 def test_pulse_reaches_both_colors_and_blends_between(self):
  c=self.cue('pulse');np.testing.assert_array_equal(m.render_cue(c,3,0),np.tile([[0],[0],[255]],(1,3)));np.testing.assert_array_equal(m.render_cue(c,3,4),np.tile([[255],[0],[0]],(1,3)));np.testing.assert_allclose(m.render_cue(c,3,2),np.tile([[127.5],[0],[127.5]],(1,3)))
 def test_rainbow_can_use_selected_palette_or_full_spectrum(self):
  palette=m.render_cue(self.cue('rainbow'),51,0);np.testing.assert_array_equal(palette[1],0);self.assertEqual(palette[0].max(),255);self.assertEqual(palette[2].max(),255)
  rainbow=m.render_cue(self.cue('rainbow',False),51,0);self.assertTrue(np.any(rainbow[1]>0))
 def test_unchecked_restores_black_background_and_off_flash(self):
  for effect in ['chase','comet','bounce','wipe']:
   out=m.render_cue(self.cue(effect,False),51,0);self.assertTrue(np.any(np.all(out==0,axis=0)));np.testing.assert_array_equal(out[2],0)
  np.testing.assert_array_equal(m.render_cue(self.cue('flash',False),51,4),0)
 def test_legacy_single_color_effects_do_not_change_without_save(self):
  for effect in ['flash','bounce','comet','pulse','chase','wipe','rainbow']:
   old=self.cue(effect);old.pop('use_color2');np.testing.assert_array_equal(m.render_cue(old,51,2),m.render_cue(self.cue(effect,False),51,2))
 def test_legacy_scroll_blocks_and_twinkle_keep_two_colors(self):
  for effect in ['color_scroll','color_blocks','twinkle']:
   old=self.cue(effect);old.pop('use_color2');np.testing.assert_array_equal(m.render_cue(old,51,2),m.render_cue(self.cue(effect,True),51,2))
 def test_motion_flag_rejects_non_boolean(self):
  for flag in ['true',1,None,{}]:
   with self.assertRaises(ValueError):m.motion_settings({'use_color2':flag})
 def test_both_colors_respect_brightness(self):
  c=self.cue('bounce');c['brightness']=20;self.assertLessEqual(m.render_cue(c,51,2).max(),51)
