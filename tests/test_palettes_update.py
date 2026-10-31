import importlib.util,json,hashlib,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hours_update',ROOT/'updates/palettes/install_update.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class UpdateTests(unittest.TestCase):
 def fixture(self,p):
  root=p/'installed';package=p/'update';root.mkdir();package.mkdir();meta={}
  for name in m.FILES:
   data=(ROOT/'src/controller'/name).read_bytes();target=package/'files'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
   old=None if name.endswith(('show_schedule.py','show_schedule.js')) else (b'old=1\n' if name.endswith('.py') else b'old text')
   if old is not None:
    dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
   meta[name]={'sha256':hashlib.sha256(data).hexdigest(),'supported':[hashlib.sha256(old).hexdigest() if old else None]}
  (package/'manifest.json').write_text(json.dumps(meta))
  driver=root/'server/libs/outputs/output_raspi.py';driver.parent.mkdir(parents=True,exist_ok=True);driver.write_text('old=1\n')
  config=root.parent/'.mlsc';config.mkdir();(config/'config.json').write_text('{}');(config/'song_moments.json').write_text('private cues')
  return root,package
 def test_install_idempotent_restore_preserves_driver_config_and_cues(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   with patch.object(m,'PACKAGE',package):backup=m.install(root,True);m.install(root,True);m.restore(root,backup)
   after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   self.assertEqual(before,after);self.assertEqual((root.parent/'.mlsc/config.json').read_text(),'{}');self.assertEqual((root.parent/'.mlsc/song_moments.json').read_text(),'private cues')
 def test_unsupported_source_refused_without_backup_or_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));target=root/'server/libs/audio_process_service.py';target.write_text('custom=1')
   with patch.object(m,'PACKAGE',package),self.assertRaisesRegex(ValueError,'differs'):m.install(root,True)
   self.assertEqual(target.read_text(),'custom=1');self.assertEqual(list(root.parent.glob('hnls-show-hours-backup-*')),[])
 def test_partial_file_failure_rolls_back_all_changed_files(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()};replace=Path.replace
   def fail(p,target):
    if str(target).endswith('song_show.js'):raise OSError('simulated disk failure')
    return replace(p,target)
   with patch.object(m,'PACKAGE',package),patch.object(Path,'replace',fail),self.assertRaises(OSError):m.install(root,True)
   self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
 def test_published_update_payload_and_current_release_lineage(self):
  meta=json.loads((ROOT/'updates/palettes/manifest.json').read_text())
  self.assertEqual(set(meta),m.FILES)
  for name,item in meta.items():
   payload=ROOT/'updates'/'palettes'/'files'/name
   self.assertEqual(hashlib.sha256(payload.read_bytes()).hexdigest(),item['sha256'])
   current=hashlib.sha256((ROOT/'src/controller'/name).read_bytes()).hexdigest()
   from update_lineage import assert_lineage
   assert_lineage(self,ROOT,name,item['sha256'])
 def test_live_validation_checks_only_included_templates_then_restarts(self):
  import sys
  from types import SimpleNamespace
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));environment=Mock();expected=[(package/'files'/n).read_text() for n in m.FILES if n.endswith('.html')]
   with patch.object(m,'PACKAGE',package),patch.object(m,'active',return_value=True),patch.object(m,'service') as service,patch.dict(sys.modules,{'jinja2':SimpleNamespace(Environment=lambda:environment)}):
    m.install(root,False)
   self.assertCountEqual([call.args[0] for call in environment.parse.call_args_list],expected)
   self.assertEqual(len(expected),1);self.assertEqual([call.args[0] for call in service.call_args_list],['stop','start','is-active'])
 def test_template_parse_failure_leaves_service_and_code_untouched(self):
  import sys
  from types import SimpleNamespace
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()};environment=Mock();environment.parse.side_effect=ValueError('Bad template')
   with patch.object(m,'PACKAGE',package),patch.object(m,'service') as service,patch.dict(sys.modules,{'jinja2':SimpleNamespace(Environment=lambda:environment)}),self.assertRaisesRegex(ValueError,'Bad template'):m.install(root,False)
   service.assert_not_called();self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
 def test_rollback_archives_and_removes_only_new_settings(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d))
   with patch.object(m,'PACKAGE',package):backup=m.install(root,True)
   value={'default_device':{'effects':{'effect_song_show':{'show_mode':'auto','bass_color':'#123456','expanded_bands':True}}},'device_configs':{'device_1':{'led_count':750,'effects':{'effect_song_show':{'palette_preset':'christmas','brilliance_color':'#ffffff','max_lit_leds':67}}}}}
   p=root.parent/'.mlsc/config.json';p.write_text(json.dumps(value));m.restore(root,backup);after=json.loads(p.read_text())
   self.assertEqual(after['default_device']['effects']['effect_song_show'],{'bass_color':'#123456'})
   self.assertEqual(after['device_configs']['device_1']['effects']['effect_song_show'],{'max_lit_leds':67});self.assertEqual(after['device_configs']['device_1']['led_count'],750)
   archived=list(backup.glob('settings-before-rollback-*/config.json'));self.assertEqual(len(archived),1);self.assertEqual(json.loads(archived[0].read_text()),value)
 def test_real_rc8_baseline_with_custom_template_installs_and_rolls_back(self):
  import zipfile
  # Model the reported Pi: original rc.8 code plus a different local template.
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'installed';root.mkdir()
   for name,item in json.loads((m.PACKAGE/'manifest.json').read_text()).items():
    if item['supported']==[None]:continue
    golden=ROOT/'tests/fixtures/palettes_rc8'/(name+'.txt')
    data=golden.read_bytes()
    self.assertIn(hashlib.sha256(data).hexdigest(),item['supported'])
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   template=root/'server/libs/config_template.json';original=b'{"local_template":"preserve exactly","device_configs":{}}\n';template.write_bytes(original)
   backup=m.install(root,True)
   self.assertEqual(template.read_bytes(),original)
   self.assertNotIn('server/libs/config_template.json',json.loads((backup/'backup.json').read_text()))
   for name,item in json.loads((m.PACKAGE/'manifest.json').read_text()).items():
    self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),item['sha256'])
   m.restore(root,backup);self.assertEqual(template.read_bytes(),original)
 def test_misplaced_future_import_refused_before_service_stop_or_file_changes(self):
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));name='server/libs/webserver/schemas/config_validator_service.py'
   malformed=b'x=1\nfrom __future__ import annotations\n'
   (package/'files'/name).write_bytes(malformed)
   meta=json.loads((package/'manifest.json').read_text());meta[name]['sha256']=hashlib.sha256(malformed).hexdigest();(package/'manifest.json').write_text(json.dumps(meta))
   before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   with patch.object(m,'PACKAGE',package),patch.object(m,'service') as service,self.assertRaises(SyntaxError):m.install(root,False)
   service.assert_not_called();self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
 def test_targeted_startup_repair_backs_up_and_is_idempotent(self):
  spec=importlib.util.spec_from_file_location('repair',ROOT/'maintenance/repair_palette_startup.py');repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config_validator_service.py';original=(ROOT/'tests/fixtures/palettes_rc8/server/libs/webserver/schemas/config_validator_service.py.txt').read_text()
   bad='from libs.show_palettes import EXTRA_COLORS, SHOW_MODES, PALETTE_IDS\n'+original;p.write_text(bad)
   with self.assertRaises(SyntaxError):compile(bad,str(p),'exec')
   repair.repair(p);fixed=p.read_text();compile(fixed,str(p),'exec');repair.repair(p)
   self.assertEqual(p.read_text(),fixed);backups=list(Path(d).glob('*.before-import-fix-*'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(),bad)
 def test_targeted_repair_refuses_unknown_contents(self):
  spec=importlib.util.spec_from_file_location('repair',ROOT/'maintenance/repair_palette_startup.py');repair=importlib.util.module_from_spec(spec);spec.loader.exec_module(repair)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'config_validator_service.py';p.write_text('custom = True\n')
   with self.assertRaises(SystemExit):repair.repair(p)
   self.assertEqual(p.read_text(),'custom = True\n')
if __name__=='__main__':unittest.main()
