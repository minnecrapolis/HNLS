import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('show_schedule_tested',ROOT/'src/controller/server/libs/show_schedule.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def settings(**kw):return m.validate({**m.DEFAULT,'days':list(range(7)),**kw})
def utc(value):return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
class ScheduleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'schedule.json';self.start=Mock(return_value=True);self.stop=Mock();self.now=utc('2026-10-30T22:00:00');self.engine=m.ShowSchedule(self.start,self.stop,self.path,lambda:self.now)
 def write(self,**kw):self.path.write_text(json.dumps(settings(**kw)))
 def test_disabled_default_does_not_interrupt_manual_playback(self):
  self.engine.tick();self.start.assert_not_called();self.stop.assert_not_called()
 def test_local_start_inclusive_stop_exclusive(self):
  s=settings(enabled=True)
  self.assertIsNone(m.window_key(s,utc('2026-10-30T21:59:00')))
  self.assertIsNotNone(m.window_key(s,utc('2026-10-30T22:00:00')))
  self.assertIsNone(m.window_key(s,utc('2026-10-31T03:00:00')))
 def test_overnight_uses_start_day(self):
  s=settings(enabled=True,days=[4],start='22:00',end='02:00',timezone='UTC')
  self.assertIsNotNone(m.window_key(s,utc('2026-10-31T01:59:00')))
  self.assertIsNone(m.window_key(s,utc('2026-10-31T02:00:00')))
  self.assertIsNone(m.window_key(s,utc('2026-10-31T23:00:00')))
 def test_reboot_during_window_starts_once(self):
  self.write(enabled=True);self.engine.tick();self.engine.tick();self.start.assert_called_once();self.stop.assert_not_called()
 def test_enabled_reboot_outside_window_forces_dark_once(self):
  self.write(enabled=True);self.now=utc('2026-10-30T17:00:00');self.engine.tick();self.engine.tick();self.stop.assert_called_once();self.start.assert_not_called()
 def test_closing_stops_once_and_next_day_starts(self):
  self.write(enabled=True);self.engine.tick();self.engine.tick(utc('2026-10-31T03:00:00'));self.engine.tick(utc('2026-10-31T03:01:00'));self.stop.assert_called_once();self.engine.tick(utc('2026-10-31T22:00:00'));self.assertEqual(self.start.call_count,2)
 def test_manual_stop_does_not_get_restarted_each_poll(self):
  self.write(enabled=True);self.engine.tick();self.engine.tick(utc('2026-10-30T22:15:00'));self.start.assert_called_once()
 def test_save_is_persistent_and_enable_inside_window_starts(self):
  self.engine.save(settings(enabled=True));self.assertTrue(json.loads(self.path.read_text())['enabled']);self.start.assert_called_once();self.assertEqual(self.path.stat().st_mode&0o777,0o600)
 def test_disable_stops_owned_show(self):
  self.engine.save(settings(enabled=True));self.engine.save(settings(enabled=False));self.stop.assert_called_once()
 def test_empty_library_retries_without_busy_start_loop(self):
  self.start.return_value=False;self.write(enabled=True);self.engine.tick();self.engine.tick();self.start.assert_called_once();self.assertIn('Waiting',self.engine.message)
  self.engine.retry_after=0;self.start.return_value=True;self.engine.tick();self.assertEqual(self.start.call_count,2)
 def test_stop_failure_retries_boundary(self):
  self.write(enabled=True);self.engine.tick();self.stop.side_effect=[OSError('temporary'),None];self.engine.tick(utc('2026-10-31T03:00:00'));self.assertIn('temporary',self.engine.error);self.engine.tick(utc('2026-10-31T03:00:02'));self.assertFalse(self.engine.owned);self.assertEqual(self.stop.call_count,2)
 def test_partial_start_failure_blacks_out(self):
  self.write(enabled=True);self.start.side_effect=OSError('queue failed');self.engine.tick();self.stop.assert_called_once();self.assertIn('queue failed',self.engine.error);self.assertFalse(self.engine.owned)
 def test_bad_schedule_file_shows_error_and_stops_owned_show(self):
  self.write(enabled=True);self.engine.tick();self.path.write_text('{broken');self.engine.tick();self.stop.assert_called_once();self.assertTrue(self.engine.view()['error'])
 def test_dst_fall_back_does_not_start_twice(self):
  self.write(enabled=True,start='00:30',end='02:30',timezone='America/New_York');self.engine.tick(utc('2026-11-01T05:30:00'));self.engine.tick(utc('2026-11-01T06:30:00'));self.start.assert_called_once()
 def test_dst_spring_forward_missed_hour_starts_when_inside_window(self):
  s=settings(enabled=True,start='02:15',end='04:00',timezone='America/New_York');self.assertIsNotNone(m.window_key(s,utc('2027-03-14T07:05:00')))
 def test_invalid_inputs_rejected_without_changing_file(self):
  self.write();before=self.path.read_bytes()
  for change in [{'enabled':'yes'},{'days':[]},{'days':[True]},{'days':[1,1]},{'start':'25:00'},{'end':'17:00'},{'timezone':'Made/Up'}]:
   with self.subTest(change=change),self.assertRaises(ValueError):self.engine.save({**settings(),**change})
  self.assertEqual(self.path.read_bytes(),before)
class ScheduleActionTests(unittest.TestCase):
 def test_start_uses_main_show_and_random_song_with_shuffle(self):
  import sys
  from types import SimpleNamespace as NS
  ex=Mock();actions=m.ScheduleActions(ex)
  with patch.object(actions,'release_studio'),patch.dict(sys.modules,{'libs.hnls_playlist':NS(save_settings=Mock()),'libs.music_library':NS(list_music_files=lambda:[{'name':'a.mp3'}])}) as modules:
   self.assertTrue(actions.start());modules['libs.hnls_playlist'].save_settings.assert_called_once_with({'shuffle':True})
  ex.effect_executer.set_active_effect_for_all.assert_called_once_with('effect_song_show');ex.music_library_executer.play.assert_called_once_with('a.mp3')
 def test_stop_sets_all_outputs_off_and_stops_music(self):
  ex=Mock();actions=m.ScheduleActions(ex)
  with patch.object(actions,'release_studio'):actions.stop()
  ex.effect_executer.set_active_effect_for_all.assert_called_once_with('effect_off');ex.music_library_executer.stop.assert_called_once()
if __name__=='__main__':unittest.main()
