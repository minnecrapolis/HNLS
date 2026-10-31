import ast,copy,importlib.util,json,multiprocessing as mp,queue,sys,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'src/controller/server/libs';sys.path.insert(0,str(LIB.parent))
from libs import song_moments as m,music_library
from test_gpio_strings import configuration

def hold(lock,ready):
 lock.acquire();ready.set();time.sleep(30)

def method(filename,cls,name,scope):
 tree=ast.parse((LIB/filename).read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls);fn=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[fn],type_ignores=[]),str(LIB/filename),'exec'),scope);return scope[name]

class DesignerEffects(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name);music=root/'music';music.mkdir();(music/'song.mp3').write_bytes(b'fake')
  self.path=root/'moments.json';self.addCleanup(patch.stopall);patch.object(m,'store_path',return_value=self.path).start();patch.object(music_library,'MUSIC_DIR',music).start();m._CACHE.update(checked=-1.,stamp=None,cues=[])
  self.config=configuration();d=self.config['device_configs']['device_0'];d['led_count']=750
  self.device=NS(config=self.config,device_config=d,song_moment_clock=mp.Value('d',10),song_moment_token=mp.Value('Q',m.song_token('song.mp3'),lock=False),song_moment_position=mp.Value('d',20,lock=False),song_moment_paused=mp.Value('b',False,lock=False))
  self.base=np.full((3,750),[17],dtype=np.uint8)
 def cue(self,**kw):return m.save_moment({'file':'song.mp3','start':20,'end':30,'targets':['device_0'],'first':700,'last':750,'effect':'color_blocks','color':'#ff0000','color2':'#0000ff','brightness':100,'speed':1,'reserve':False,'cycle_seconds':8,'band_width':8,'direction':'forward',**kw},self.config)
 def position(self,n):self.device.song_moment_position.value=n
 def test_all_effects_touch_only_700_through_750_and_never_mutate_base(self):
  for effect in m.EFFECTS:
   with self.subTest(effect=effect):
    c=self.cue(effect=effect);out,active=m.overlay(self.base,self.device,10)
    self.assertTrue(active);np.testing.assert_array_equal(out[:,:699],self.base[:,:699]);np.testing.assert_array_equal(self.base,17);self.assertEqual(out.shape,(3,750));m.delete_moment(c['id'])
 def test_bold_scroll_has_full_primary_color_extremes_and_slow_motion(self):
  self.cue();a,_=m.overlay(self.base,self.device,10);self.position(20.2);b,_=m.overlay(self.base,self.device,10)
  colors=np.unique(a[:,699:].T,axis=0);self.assertEqual({tuple(x) for x in colors},{(255,0,0),(0,0,255)})
  self.assertLess(np.count_nonzero(np.any(a[:,699:]!=b[:,699:],axis=0)),15)
 def test_new_scroll_period_returns_same_frame_after_eight_seconds(self):
  c=self.cue(effect='color_scroll');a=m.render_cue(c,51,0);b=m.render_cue(c,51,8);np.testing.assert_allclose(a,b)
 def test_dark_gaps_do_not_contain_automatic_green_or_white(self):
  for effect in ['chase','comet','bounce','twinkle','wipe']:
   c=self.cue(effect=effect);out,_=m.overlay(self.base,self.device,10);self.assertTrue(np.any(np.all(out[:,699:]==0,axis=0)));self.assertFalse(np.any(out[1,699:]>0));m.delete_moment(c['id'])
 def test_reserved_range_black_before_after_and_only_effect_inside(self):
  self.cue(reserve=True)
  for pos in [0,19.9,30,300]:
   self.position(pos);out,_=m.overlay(self.base,self.device,10);np.testing.assert_array_equal(out[:,699:],0);np.testing.assert_array_equal(out[:,:699],17)
  self.position(20);out,_=m.overlay(self.base,self.device,10);self.assertTrue(np.any(out[:,699:]>0))
 def test_without_reservation_base_returns_at_end(self):
  self.cue();self.position(30);out,active=m.overlay(self.base,self.device,10);self.assertFalse(active);np.testing.assert_array_equal(out,self.base)
 def test_clock_jitter_keeps_cue_exclusive_and_long_stall_blacks_controlled_range(self):
  self.cue();out,active=m.overlay(self.base,self.device,10.3);self.assertTrue(active);self.assertFalse(np.any(out[1,699:]>0))
  out,_=m.overlay(self.base,self.device,11);np.testing.assert_array_equal(out[:,699:],0);np.testing.assert_array_equal(out[:,:699],17)
 def test_paused_clock_freezes_animation(self):
  self.cue();self.device.song_moment_paused.value=True;a,_=m.overlay(self.base,self.device,10.1);b,_=m.overlay(self.base,self.device,10.6);np.testing.assert_array_equal(a,b)
 def test_direction_reverses_only_selected_effect(self):
  c=self.cue();forward=m.render_cue(c,51,1);reverse=m.render_cue({**c,'direction':'reverse'},51,1);np.testing.assert_array_equal(reverse,forward[:,::-1])
 def test_wipe_reaches_the_last_led_before_restarting(self):
  c=self.cue(effect='wipe');out=m.render_cue(c,51,7.999);np.testing.assert_array_equal(out,np.tile([[255],[0],[0]],(1,51)))
 def test_twinkle_and_rainbow_are_repeatable_on_seek(self):
  for effect in ['twinkle','rainbow']:
   c=self.cue(effect=effect);a=m.render_cue(c,51,1.2);m.render_cue(c,51,5);np.testing.assert_array_equal(a,m.render_cue(c,51,1.2))
 def test_invalid_saved_row_does_not_kill_other_valid_reserved_cue(self):
  self.cue(reserve=True);doc=m.read();doc['cues'] += [None,{'file':1,'reserve':True},{**doc['cues'][0],'color':'bad'}];m.write(doc);self.position(0);out,_=m.overlay(self.base,self.device,10);np.testing.assert_array_equal(out[:,699:],0)
 def test_failed_file_read_retains_last_good_reservation(self):
  self.cue(reserve=True);self.position(0);m.overlay(self.base,self.device,10);self.path.write_text('{broken');out,_=m.overlay(self.base,self.device,10.3);np.testing.assert_array_equal(out[:,699:],0)
 def test_two_color_choice_persists_and_renders_on_only_selected_range(self):
  cue=self.cue(effect='bounce',use_color2=True);self.assertTrue(cue['use_color2']);self.assertTrue(m.read()['cues'][0]['use_color2'])
  out,_=m.overlay(self.base,self.device,10);self.assertTrue(np.any(out[2,699:]>0));self.assertTrue(np.any(out[0,699:]>0));np.testing.assert_array_equal(out[:,:699],17)
 def test_invalid_motion_fields_do_not_save(self):
  self.cue();before=self.path.read_bytes()
  for field in [{'cycle_seconds':0},{'cycle_seconds':float('nan')},{'band_width':0},{'band_width':True},{'direction':'shell'}]:
   with self.assertRaises(ValueError):self.cue(**field)
  self.assertEqual(self.path.read_bytes(),before)
 def test_real_output_loop_reserves_and_restores_cached_base_without_new_frame(self):
  from libs.notification_enum import NotificationEnum
  Q=FreezeRegressions().queue_class();frames=Q(queue.Queue(2));notifications=Q(queue.Queue(2));frames.queue.put(self.base)
  self.device.playback_blackout=NS(value=False);self.device.playback_epoch=NS(value=0);self.device.playback_ready_epoch=NS(value=0)
  service=NS(_fps_limiter=Mock(),_device_notification_queue_in=notifications,_output_queue=frames,_skip_output=False,_device=self.device,_led_strip='ws2811_strip_grb',_current_output=Mock(),ten_seconds_counter=100,start_time=100)
  run=method('output_service.py','OutputService','output_routine',{'np':np,'os':NS(environ={}), 'time':lambda:100.,'logger':Mock(),'NotificationEnum':NotificationEnum})
  cue=self.cue(reserve=True);self.position(0)
  with patch.object(m.time,'monotonic',return_value=10):
   run(service);np.testing.assert_array_equal(service._current_output.show.call_args.args[0][:,699:],0)
   self.position(20);run(service);self.assertFalse(np.any(service._current_output.show.call_args.args[0][1,699:]>0))
   m.delete_moment(cue['id']);run(service);np.testing.assert_array_equal(service._current_output.show.call_args.args[0],self.base)
   self.device.playback_blackout.value=True;run(service);np.testing.assert_array_equal(service._current_output.show.call_args.args[0],0)
 def test_rgbw_extra_channel_is_black_on_whole_owned_range(self):
  self.cue(effect='comet');out,_=m.overlay(np.full((4,750),17,dtype=np.uint8),self.device,10);np.testing.assert_array_equal(out[3,699:],0)

class FreezeRegressions(unittest.TestCase):
 def queue_class(self):
  tree=ast.parse((LIB/'queue_wrapper.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef));scope={'queue':queue,'logger':Mock()};exec(compile(ast.Module(body=[node],type_ignores=[]),'queue_wrapper.py','exec'),scope);return scope['QueueWrapper']
 def test_competing_consumer_empty_queue_returns_without_blocking(self):
  Q=self.queue_class();q=queue.Queue(2);wrapped=Q(q);q.put('frame');q.get_nowait();self.assertIsNone(wrapped.get_available())
 def test_discard_loop_is_bounded_even_with_continuous_producer(self):
  Q=self.queue_class();fake=Mock();fake.get_nowait.return_value='always another frame';Q(fake).discard_available();self.assertEqual(fake.get_nowait.call_count,16)
 def test_output_and_effect_realtime_consumers_have_no_blocking_frame_reads(self):
  for filename,cls,name in [('output_service.py','OutputService','output_routine'),('effect_service.py','EffectService','effect_routine')]:
   tree=ast.parse((LIB/filename).read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='get_blocking' for n in ast.walk(node)))
 def test_clock_writer_skips_busy_lock_without_stalling_other_state(self):
  lock=Mock();lock.acquire.return_value=False
  device=NS(song_moment_clock=NS(get_lock=lambda:lock),playback_epoch=NS(value=0),playback_blackout=NS(value=True))
  manager=NS(_devices={'device_0':device});run=method('device_manager.py','DeviceManager','refresh_audio_queues',{'copy':copy})
  run(manager,{'_playback':{'file':'song.mp3','position':2,'epoch':7,'blackout':False}})
  lock.acquire.assert_called_once_with(False);self.assertEqual(device.playback_epoch.value,7);self.assertFalse(device.playback_blackout.value)
 def test_paused_heartbeat_publishes_file_position_and_paused_state(self):
  publish=method('audio_process_service.py','AudioProcessService','_publish_playback',{})
  audio=NS(_audio_queue=Mock(),_playback_epoch=3,_music_file='song.mp3',_source_mode='music',_music_position=21.5,_music_paused=True)
  publish(audio,False);payload=audio._audio_queue.put_none_blocking.call_args.args[0]['_playback']
  self.assertTrue(payload['paused']);self.assertEqual(payload['file'],'song.mp3');self.assertEqual(payload['position'],21.5)
 def test_pause_clock_heartbeat_is_rate_limited_without_changing_audio_output(self):
  now=[10.];run=method('audio_process_service.py','AudioProcessService','_music_routine',{'monotonic':lambda:now[0],'sleep':Mock()})
  audio=NS(_music_paused=True,_music_gap_until=None,_publish_playback=Mock())
  for value in [10.,10.05,10.11]:now[0]=value;run(audio)
  self.assertEqual(audio._publish_playback.call_count,2);audio._publish_playback.assert_called_with(False)
 @unittest.skipUnless('fork' in mp.get_all_start_methods(),'Requires fork for orphaned-lock reproduction')
 def test_orphaned_clock_cannot_hang_overlay_and_refresh_recreates_shared_state(self):
  tree=ast.parse((LIB/'device.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Device');reset=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='reset_playback_state');skeleton=ast.ClassDef(name='Device',bases=[],keywords=[],body=[reset],decorator_list=[]);scope={'Value':mp.Value};exec(compile(ast.fix_missing_locations(ast.Module(body=[skeleton],type_ignores=[])),'device.py','exec'),scope)
  device=scope['Device']();device._Device__device_config={'effects':{}};device.reset_playback_state();old=device.song_moment_clock;ctx=mp.get_context('fork');ready=ctx.Event();process=ctx.Process(target=hold,args=(old.get_lock(),ready));process.start()
  try:
   self.assertTrue(ready.wait(2));process.terminate();process.join(2);self.assertFalse(old.get_lock().acquire(False))
   start=time.monotonic();out,active=m.overlay(np.full((3,51),99,dtype=np.uint8),device,10);self.assertLess(time.monotonic()-start,.2);self.assertTrue(active);np.testing.assert_array_equal(out,0)
   device.reset_playback_state();self.assertIsNot(device.song_moment_clock,old);self.assertTrue(device.song_moment_clock.get_lock().acquire(False));device.song_moment_clock.get_lock().release()
  finally:
   if process.is_alive():process.terminate();process.join(2)
if __name__=='__main__':unittest.main()
