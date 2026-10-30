import importlib.util,json,hashlib,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('hours_update',ROOT/'updates/show-hours/install_update.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
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
  driver=root/'server/libs/outputs/output_raspi.py';driver.parent.mkdir(parents=True,exist_ok=True);driver.write_text('working GPIO driver')
  config=root.parent/'.mlsc';config.mkdir();(config/'config.json').write_text('private config');(config/'song_moments.json').write_text('private cues')
  return root,package
 def test_install_idempotent_restore_preserves_driver_config_and_cues(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   with patch.object(m,'PACKAGE',package):backup=m.install(root,True);m.install(root,True);m.restore(root,backup)
   after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   self.assertEqual(before,after);self.assertEqual((root.parent/'.mlsc/config.json').read_text(),'private config');self.assertEqual((root.parent/'.mlsc/song_moments.json').read_text(),'private cues')
 def test_unsupported_source_refused_without_backup_or_changes(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));target=root/'server/libs/webserver/executer.py';target.write_text('custom=1')
   with patch.object(m,'PACKAGE',package),self.assertRaisesRegex(ValueError,'differs'):m.install(root,True)
   self.assertEqual(target.read_text(),'custom=1');self.assertEqual(list(root.parent.glob('hnls-show-hours-backup-*')),[])
 def test_partial_file_failure_rolls_back_all_changed_files(self):
  with tempfile.TemporaryDirectory() as d:
   root,package=self.fixture(Path(d));before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()};replace=Path.replace
   def fail(p,target):
    if str(target).endswith('music.js'):raise OSError('simulated disk failure')
    return replace(p,target)
   with patch.object(m,'PACKAGE',package),patch.object(Path,'replace',fail),self.assertRaises(OSError):m.install(root,True)
   self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()})
if __name__=='__main__':unittest.main()
