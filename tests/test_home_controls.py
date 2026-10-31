import ast,copy,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src/controller/server'))
from libs.home_look import view,apply
from libs.section_sync import DEFAULT_SYNC
from test_play_now import m as schedule_module

class HomeLookTests(unittest.TestCase):
 def setUp(self):
  self.config={'device_configs':{k:{'device_name':name,'led_count':count,'led_brightness':brightness,'output':{'secret':'not for the Home response'},'effects':{'last_effect':'effect_off','effect_song_show':{**copy.deepcopy(DEFAULT_SYNC),'max_lit_leds':limit}}} for k,name,count,brightness,limit in [('device_0','Main',1200,20,100),('device_1','Slave',350,30,40)]}}
  def effect(key,kind,settings):self.config['device_configs'][key]['effects'][kind].update(settings);return {'settings':settings}
  def device(key,settings):self.config['device_configs'][key].update(settings);return {'settings':settings}
  self.ex=NS(effect_settings_executer=NS(_config=self.config,set_effect_settings=Mock(side_effect=effect)),device_settings_executer=NS(set_device_settings=Mock(side_effect=device)),effect_executer=Mock())
 def test_view_is_small_and_does_not_expose_output_configuration(self):
  data=view(self.config);self.assertEqual(len(data['devices']),2);self.assertEqual(len(data['palettes']),14);self.assertNotIn('not for the Home response',json.dumps(data))
 def test_palette_and_mode_preserve_groups_limits_brightness_and_off_state(self):
  before=copy.deepcopy(self.config);result=apply({'target':'*','palette':'christmas','mode':'auto'},self.ex);self.assertTrue(result['ok'])
  for key,d in self.config['device_configs'].items():
   old=before['device_configs'][key];settings=d['effects']['effect_song_show'];self.assertEqual(settings['palette_preset'],'christmas');self.assertEqual(settings['show_mode'],'auto');self.assertEqual(settings['max_lit_leds'],old['effects']['effect_song_show']['max_lit_leds']);self.assertEqual(d['led_brightness'],old['led_brightness']);self.assertEqual(d['effects']['last_effect'],'effect_off')
  self.ex.effect_executer.set_active_effect.assert_not_called();self.ex.device_settings_executer.set_device_settings.assert_not_called()
 def test_brightness_changes_only_selected_string_and_no_color_settings(self):
  before=copy.deepcopy(self.config);apply({'target':'device_1','brightness':12},self.ex)
  self.assertEqual(self.config['device_configs']['device_0'],before['device_configs']['device_0']);self.assertEqual(self.config['device_configs']['device_1']['led_brightness'],12);self.assertEqual(self.config['device_configs']['device_1']['effects'],before['device_configs']['device_1']['effects']);self.ex.effect_settings_executer.set_effect_settings.assert_not_called()
 def test_invalid_requests_do_not_make_any_writes(self):
  for data in [{'target':'bad','mode':'auto'},{'target':'*','palette':'unknown'},{'target':'*','mode':'flashing'},{'target':'*','brightness':True},{'target':'*','brightness':101},{'target':'*','brightness':-1},{'target':'*'},{'target':'*','gpio':18}]:
   with self.subTest(data=data),self.assertRaises(ValueError):apply(data,self.ex)
  self.ex.effect_settings_executer.set_effect_settings.assert_not_called();self.ex.device_settings_executer.set_device_settings.assert_not_called()
 def test_partial_failure_reports_actual_successes_and_keeps_failed_target(self):
  before=copy.deepcopy(self.config['device_configs']['device_1']);save=self.ex.effect_settings_executer.set_effect_settings.side_effect
  def fail(key,kind,settings):
   if key=='device_1':raise OSError('write failed')
   return save(key,kind,settings)
  self.ex.effect_settings_executer.set_effect_settings.side_effect=fail;result=apply({'target':'*','mode':'auto'},self.ex)
  self.assertFalse(result['ok']);self.assertEqual([d['name'] for d in result['applied']],['Main']);self.assertEqual([d['name'] for d in result['failed']],['Slave']);self.assertEqual(self.config['device_configs']['device_1'],before)
 def test_all_selected_settings_validate_before_first_write(self):
  self.config['device_configs']['device_1']['effects']['effect_song_show']['section_size']=0
  with self.assertRaises(ValueError):apply({'target':'*','mode':'auto'},self.ex)
  self.ex.effect_settings_executer.set_effect_settings.assert_not_called()
 def test_home_apis_are_authenticated(self):
  tree=ast.parse((ROOT/'src/controller/server/libs/webserver/blueprints/music_library_api.py').read_text())
  for name in ['home_look_get','home_look_save','playlist_settings_get']:
   node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);self.assertTrue(any(isinstance(d,ast.Name) and d.id=='login_required' for d in node.decorator_list))

class SelectedSongTests(unittest.TestCase):
 def test_selected_song_uses_all_lights_and_preserves_shuffle_choice(self):
  ex=Mock();action=schedule_module.ScheduleActions(ex);prefs=Mock()
  with patch.object(action,'release_studio'),patch.dict(sys.modules,{'libs.hnls_playlist':NS(save_settings=prefs),'libs.music_library':NS(list_music_files=lambda:[{'name':'Garden.mp3'},{'name':'Thriller.mp3'}])}):self.assertTrue(action.start(filename='Garden.mp3'))
  prefs.assert_not_called();ex.music_library_executer.play.assert_called_once_with('Garden.mp3');ex.effect_executer.set_active_effect_for_all.assert_called_once_with('effect_song_show')
 def test_invalid_selected_song_does_not_release_studio_or_change_lights(self):
  ex=Mock();action=schedule_module.ScheduleActions(ex)
  with patch.object(action,'release_studio') as release,patch.dict(sys.modules,{'libs.hnls_playlist':NS(save_settings=Mock()),'libs.music_library':NS(list_music_files=lambda:[{'name':'Garden.mp3'}])}),self.assertRaises(ValueError):action.start(filename='missing.mp3')
  release.assert_not_called();ex.effect_executer.set_active_effect_for_all.assert_not_called()

 def test_selected_file_participates_in_manual_schedule_override(self):
  import tempfile
  from datetime import datetime,timezone
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'schedule.json';path.write_text(json.dumps({**schedule_module.DEFAULT,'enabled':True,'timezone':'UTC'}));before=path.read_bytes()
   start=Mock(return_value=True);stop=Mock();engine=schedule_module.ShowSchedule(start,stop,path,lambda:datetime(2026,10,31,12,tzinfo=timezone.utc))
   result=engine.play_now(filename='Garden.mp3');engine.tick();start.assert_called_once_with(filename='Garden.mp3');stop.assert_not_called();self.assertEqual(result['manual_state'],'playing');self.assertEqual(path.read_bytes(),before)
 def test_home_song_api_validates_file_before_changing_playback(self):
  tree=ast.parse((ROOT/'src/controller/server/libs/webserver/blueprints/music_library_api.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='show_now');node.decorator_list=[]
  request=NS(get_json=Mock(return_value={'action':'play','file':'Garden.mp3'}));engine=Mock();engine.play_now.return_value={'ok':True};path=Mock();path.is_file.return_value=True
  scope={'request':request,'Executer':NS(instance=NS(show_schedule=engine)),'jsonify':lambda *args,**kw:args[0] if args else kw,'safe_music_path':Mock(return_value=path)}
  exec(compile(ast.Module(body=[node],type_ignores=[]),'home_api.py','exec'),scope);self.assertTrue(scope['show_now']()['ok']);engine.play_now.assert_called_once_with(filename='Garden.mp3')
  engine.reset_mock();path.is_file.return_value=False;result,code=scope['show_now']();self.assertEqual(code,400);engine.play_now.assert_not_called()
if __name__=='__main__':unittest.main()
