import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('easy_ui_update',ROOT/'updates/easy-ui/install_update.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class UIUpdateTests(unittest.TestCase):
    def fixture(self,d):
        root=Path(d)/'installed';root.mkdir();package=Path(d)/'update';meta={}
        for n in m.FILES:
            data=(ROOT/'src/controller'/n).read_bytes();p=package/'files'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            old=None if 'hnls-guide.' in n else b'<div>Previous interface</div>'
            if old is not None:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(old)
            meta[n]={'sha256':hashlib.sha256(data).hexdigest(),'supported':[hashlib.sha256(old).hexdigest() if old is not None else None]}
        (package/'manifest.json').write_text(json.dumps(meta))
        for n,data in [('server/main.py',b'working runtime'),('server/libs/config_template.json',b'local template'),('server/libs/outputs/output_raspi.py',b'working native driver')]:
            p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        settings=root.parent/'.mlsc';settings.mkdir();(settings/'config.json').write_text('private settings');(settings/'song_moments.json').write_text('private moments')
        return root,package
    def snapshot(self,p):
        return {str(n.relative_to(p)):n.read_bytes() for n in p.rglob('*') if n.is_file()}
    def test_ui_only_no_service_commands_private_state_or_runtime_changes_and_exact_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);before=self.snapshot(root);private=self.snapshot(root.parent/'.mlsc')
            with patch.object(m,'PACKAGE',package),patch('subprocess.run',side_effect=AssertionError('No service commands allowed')):
                backup=m.install(root,True);m.install(root,True);m.restore(root,backup)
            self.assertEqual(before,self.snapshot(root));self.assertEqual(private,self.snapshot(root.parent/'.mlsc'))
    def test_unknown_template_refused_before_backup_and_any_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);p=root/'server/libs/app/templates/layouts/base.html';p.write_text('customized interface');before=self.snapshot(root)
            with patch.object(m,'PACKAGE',package),self.assertRaisesRegex(ValueError,'differs'):m.install(root,True)
            self.assertEqual(before,self.snapshot(root));self.assertFalse(list(root.parent.glob('hnls-easy-ui-backup-*')))
    def test_partial_failure_restores_all_assets(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);before=self.snapshot(root);replace=Path.replace
            def fail(p,target):
                if p.name.endswith('.hnls-ui-tmp') and str(target).endswith('song_show.js'):raise OSError('disk full')
                return replace(p,target)
            with patch.object(m,'PACKAGE',package),patch.object(Path,'replace',fail),self.assertRaises(OSError):m.install(root,True)
            self.assertEqual(before,self.snapshot(root))
    def test_real_validation_parses_every_template_without_service_actions(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);parser=Mock()
            with patch.object(m,'PACKAGE',package),patch.dict(sys.modules,{'jinja2':NS(Environment=lambda:parser)}),patch('subprocess.run',side_effect=AssertionError('No commands')):m.install(root,False)
            self.assertEqual(parser.parse.call_count,sum(n.endswith('.html') for n in m.FILES))
    def test_parser_error_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);parser=Mock();parser.parse.side_effect=ValueError('template error');before=self.snapshot(root)
            with patch.object(m,'PACKAGE',package),patch.dict(sys.modules,{'jinja2':NS(Environment=lambda:parser)}),self.assertRaises(ValueError):m.install(root,False)
            self.assertEqual(before,self.snapshot(root));self.assertFalse(list(root.parent.glob('hnls-easy-ui-backup-*')))
    def test_published_payload_current_and_base_activated_last(self):
        meta=json.loads((m.PACKAGE/'manifest.json').read_text());self.assertEqual(set(meta),m.FILES)
        self.assertEqual(list(meta)[-1],'server/libs/app/templates/layouts/base.html')
        for n,item in meta.items():
            self.assertTrue(n.startswith('server/libs/app/'));self.assertIn(Path(n).suffix,('.html','.js','.css'))
            from update_lineage import assert_lineage
            assert_lineage(self,ROOT,n,item['sha256'])
            self.assertEqual(hashlib.sha256((m.PACKAGE/'files'/n).read_bytes()).hexdigest(),item['sha256'])
    def test_outside_symlink_target_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root,package=self.fixture(d);p=root/'server/libs/app/templates/layouts/base.html';p.unlink();outside=root.parent/'outside';outside.write_text('keep');p.symlink_to(outside)
            with patch.object(m,'PACKAGE',package),self.assertRaisesRegex(ValueError,'path'):m.install(root,True)
            self.assertEqual(outside.read_text(),'keep')

if __name__=='__main__':unittest.main()
