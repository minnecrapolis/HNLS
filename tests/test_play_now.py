import ast
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('schedule_manual',ROOT/'src/controller/server/libs/show_schedule.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from datetime import datetime,timezone

def utc(t):return datetime.fromisoformat(t).replace(tzinfo=timezone.utc)

class ManualShowTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.path=Path(tmp.name)/'show_schedule.json'
        self.settings={**m.DEFAULT,'enabled':True,'days':list(range(7)),'timezone':'UTC','start':'17:00','end':'22:00'}
        self.path.write_text(json.dumps(self.settings));self.start=Mock(return_value=True);self.stop=Mock();self.now=utc('2026-10-31T12:00:00')
        self.engine=m.ShowSchedule(self.start,self.stop,self.path,lambda:self.now)
    def test_outside_start_survives_scheduler_and_retains_schedule_bytes(self):
        before=self.path.read_bytes();result=self.engine.play_now();self.engine.tick();self.engine.tick()
        self.start.assert_called_once();self.stop.assert_not_called();self.assertEqual(self.path.read_bytes(),before);self.assertEqual(result['manual_state'],'playing');self.assertIn('outside show hours',result['message'])
    def test_opening_boundary_returns_to_schedule_then_closing_stops(self):
        self.engine.play_now();self.engine.tick(utc('2026-10-31T17:00:00'));self.engine.tick(utc('2026-10-31T17:00:02'))
        self.assertEqual(self.start.call_count,2);self.assertEqual(self.stop.call_count,1);self.assertIsNone(self.engine.manual_state)
        self.engine.tick(utc('2026-10-31T22:00:00'));self.assertEqual(self.stop.call_count,2)
    def test_start_inside_window_still_stops_at_closing(self):
        self.now=utc('2026-10-31T18:00:00');result=self.engine.play_now();self.engine.tick();self.start.assert_called_once()
        self.assertIn('scheduled closing',result['message']);self.engine.tick(utc('2026-10-31T22:00:00'));self.stop.assert_called_once()
    def test_stop_now_inside_window_does_not_restart_until_next_opening(self):
        self.now=utc('2026-10-31T18:00:00');self.engine.play_now();self.engine.stop_now();self.engine.tick();self.engine.tick(utc('2026-10-31T21:59:00'))
        self.start.assert_called_once();self.stop.assert_called_once();self.assertEqual(self.engine.manual_state,'stopped')
        self.engine.tick(utc('2026-11-01T17:00:00'));self.assertEqual(self.start.call_count,2)
    def test_disabled_schedule_manual_show_runs_until_explicit_stop(self):
        self.settings['enabled']=False;self.path.write_text(json.dumps(self.settings));self.engine.play_now()
        for t in ('2026-10-31T17:00:00','2026-10-31T22:00:00','2026-11-01T12:00:00'):self.engine.tick(utc(t))
        self.start.assert_called_once();self.stop.assert_not_called();self.engine.stop_now();self.stop.assert_called_once()
    def test_empty_library_is_actionable_and_does_not_disturb_existing_source(self):
        self.start.return_value=False;before=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'Upload at least one song'):self.engine.play_now()
        self.stop.assert_not_called();self.assertIsNone(self.engine.manual_state);self.assertEqual(self.path.read_bytes(),before)
    def test_partial_start_failure_uses_fail_dark_without_modifying_schedule(self):
        self.start.side_effect=OSError('audio queue failed');before=self.path.read_bytes()
        with self.assertRaises(OSError):self.engine.play_now()
        self.stop.assert_called_once();self.assertFalse(self.engine.owned);self.assertEqual(self.path.read_bytes(),before)
    def test_stop_remains_available_with_bad_schedule(self):
        self.path.write_text('{broken');result=self.engine.stop_now();self.stop.assert_called_once();self.assertTrue(result['ok']);self.assertEqual(result['manual_state'],'stopped');self.assertIsNone(result['settings'])
    def test_manual_override_does_not_survive_process_restart(self):
        self.engine.play_now();reboot=m.ShowSchedule(self.start,self.stop,self.path,lambda:self.now);reboot.tick()
        self.stop.assert_called_once();self.assertIsNone(reboot.manual_state)
    def test_overnight_closing_respects_start_day(self):
        self.settings.update(days=[5],start='22:00',end='02:00');self.path.write_text(json.dumps(self.settings));self.now=utc('2026-10-31T23:00:00');self.engine.play_now()
        self.engine.tick(utc('2026-11-01T01:59:59'));self.stop.assert_not_called();self.engine.tick(utc('2026-11-01T02:00:00'));self.stop.assert_called_once()
    def test_api_requires_login_validates_action_and_uses_shared_scheduler(self):
        tree=ast.parse((ROOT/'src/controller/server/libs/webserver/blueprints/music_library_api.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='show_now')
        self.assertTrue(any(isinstance(d,ast.Name) and d.id=='login_required' for d in node.decorator_list));node.decorator_list=[]
        request=NS(get_json=Mock(return_value={'action':'play'}));schedule=NS(play_now=Mock(return_value={'ok':True}),stop_now=Mock(return_value={'ok':True}))
        scope={'request':request,'Executer':NS(instance=NS(show_schedule=schedule)),'jsonify':lambda *args,**kw:args[0] if args else kw}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'show_now.py','exec'),scope);self.assertTrue(scope['show_now']()['ok']);schedule.play_now.assert_called_once()
        request.get_json.return_value={'action':'stop'};scope['show_now']();schedule.stop_now.assert_called_once()
        request.get_json.return_value={'action':'other'};result,code=scope['show_now']();self.assertEqual(code,400);self.assertIn('error',result)

if __name__=='__main__':unittest.main()
