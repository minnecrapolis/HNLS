import importlib.util
from pathlib import Path
import tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('export_installation',ROOT/'tools/export_installation.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ExportTests(unittest.TestCase):
    def test_excludes_state_music_keys_and_environment(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for n,t in {'main.py':'print(1)','config.json':'{}','song.mp3':'media','.env':'secret','password.key':'secret','requirements.txt':'numpy==1.0'}.items():(p/n).write_text(t)
            approved,skipped=m.collect(p)
            self.assertEqual({n for n,_ in approved},{'main.py','requirements.txt'})
            self.assertEqual(len(skipped),4)
    def test_excludes_private_key_embedded_in_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'bad.py').write_text('x="-----BEGIN OPENSSH PRIVATE KEY-----"')
            self.assertEqual(m.collect(p)[0],[])
    def test_does_not_export_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'a.py').write_text('pass');(p/'link.py').symlink_to(p/'a.py')
            self.assertEqual([n for n,_ in m.collect(p)[0]],['a.py'])
if __name__=='__main__':unittest.main()
