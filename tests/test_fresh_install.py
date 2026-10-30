import importlib.util,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hnls_install',ROOT/'install.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FreshInstallTests(unittest.TestCase):
 def test_existing_installation_refused_before_any_system_commands(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);target=root/'existing';target.mkdir()
   with patch.object(m,'paths',return_value=(target,root/'venv',root/'unit','mlsc')),patch.object(m,'run') as run:
    with self.assertRaisesRegex(ValueError,'Existing installation'):m.preflight('controller')
    run.assert_not_called()
 def test_service_uses_expected_cwd_interpreter_and_boot_target(self):
  text=m.unit_text('controller')
  self.assertIn('WorkingDirectory=/share/music_led_strip_control/server',text)
  self.assertIn('ExecStart=/share/.venv/bin/python3 main.py',text)
  self.assertIn('WantedBy=multi-user.target',text)
  self.assertNotIn('Environment=',text)
 def test_release_tampering_rejected(self):
  import hashlib,json
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'payload.py').write_text('pass')
   (root/'release-manifest.json').write_text(json.dumps({'payload.py':hashlib.sha256(b'pass').hexdigest()}))
   with patch.object(m,'ROOT',root):
    self.assertEqual(m.check_payload(),1);(root/'payload.py').write_text('changed')
    with self.assertRaisesRegex(ValueError,'changed'):m.check_payload()
 def test_failed_dependency_install_removes_new_venv_and_staging(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'package/src/controller';source.mkdir(parents=True);(source/'server').mkdir();(source/'server/main.py').write_text('pass')
   target=root/'app';venv=root/'venv';unit=root/'unit'
   def run(argv,**kw):
    if '-m' in argv and 'venv' in argv:venv.mkdir()
    if '-m' in argv and 'pip' in argv:raise subprocess.CalledProcessError(1,argv)
   with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'ROOT',root/'package'),patch.object(m,'preflight',return_value=(target,venv,unit,'mlsc')),patch.object(m,'check_payload',return_value=1),patch.object(m,'run',side_effect=run):
    with self.assertRaises(subprocess.CalledProcessError):m.install('controller')
   self.assertFalse(target.exists());self.assertFalse(venv.exists());self.assertFalse(unit.exists());self.assertEqual(list(root.glob('.hnls-stage-*')),[])
 def test_service_start_failure_removes_new_code_and_unit(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);source=root/'package/src/controller';source.mkdir(parents=True);(source/'server').mkdir();(source/'server/main.py').write_text('pass')
   target=root/'app';venv=root/'venv';unit=root/'unit';calls=[]
   def run(argv,**kw):
    calls.append(argv)
    if '-m' in argv and 'venv' in argv:venv.mkdir()
    if argv[:2]==['systemctl','start']:raise subprocess.CalledProcessError(1,argv)
   with patch.object(m.os,'geteuid',return_value=0),patch.object(m,'ROOT',root/'package'),patch.object(m,'preflight',return_value=(target,venv,unit,'mlsc')),patch.object(m,'check_payload',return_value=1),patch.object(m,'unit_text',return_value='[Service]\n'),patch.object(m,'run',side_effect=run),patch.object(m.subprocess,'run') as cleanup:
    with self.assertRaises(subprocess.CalledProcessError):m.install('controller')
    cleanup.assert_any_call(['systemctl','stop','mlsc'],check=False)
    cleanup.assert_any_call(['systemctl','disable','mlsc'],check=False)
   self.assertFalse(target.exists());self.assertFalse(venv.exists());self.assertFalse(unit.exists())
if __name__=='__main__':unittest.main()
