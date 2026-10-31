import hashlib,importlib.util,json,os,stat,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bootstrap_release',ROOT/'tools/bootstrap_release.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class BootstrapTests(unittest.TestCase):
 def fixture(self,d,entries=None,checksum=True):
  root=Path(d);bin=root/'bin';bin.mkdir();downloads=root/'downloads';downloads.mkdir();version='0.1.0-test.1';asset='HNLS-'+version+'-source.zip'
  files={'HNLS/VERSION':version,'HNLS/install.sh':'#!/bin/sh\n','HNLS/release-manifest.json':'{}','HNLS/install.py':'import os,json,sys\nfrom pathlib import Path\np=Path(os.environ["HNLS_TEST_MARKER"])\nwith p.open("a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n'}
  files.update(entries or {})
  with zipfile.ZipFile(downloads/asset,'w') as z:
   for name,data in files.items():z.writestr(name,data)
  digest=hashlib.sha256((downloads/asset).read_bytes()).hexdigest() if checksum else '0'*64
  (downloads/'SHA256SUMS.txt').write_text(digest+'  '+asset+'\n')
  curl=bin/'curl';curl.write_text('#!'+sys.executable+'\nimport os,sys,shutil\nfrom pathlib import Path\nfrom urllib.parse import urlsplit\na=sys.argv[1:];url=next(v for v in a if v.startswith("https://"));name=Path(urlsplit(url).path).name\nwith Path(os.environ["HNLS_TEST_FETCHES"]).open("a") as f:f.write(url+"\\n")\nshutil.copyfile(Path(os.environ["HNLS_TEST_DOWNLOADS"])/name,a[a.index("-o")+1])\n');curl.chmod(0o755)
  sudo=bin/'sudo';sudo.write_text('#!/bin/sh\nexec "$@"\n');sudo.chmod(0o755)
  env=dict(os.environ,PATH=str(bin)+os.pathsep+os.environ['PATH'],TMPDIR=str(root),HNLS_TEST_DOWNLOADS=str(downloads),HNLS_TEST_MARKER=str(root/'calls'),HNLS_TEST_FETCHES=str(root/'fetches'))
  return root,env,version
 def run_script(self,env,version,*args,source=None):
  argv=['bash','-s','--','--repo','TestOwner/HNLS','--version',version,*args]
  return subprocess.run(argv,input=source or (ROOT/'setup.sh').read_text(),text=True,env=env,capture_output=True,timeout=15)
 def test_pipe_check_verifies_download_without_installing_and_cleans_temp(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d);r=self.run_script(env,version,'--check');self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual([json.loads(x) for x in (root/'calls').read_text().splitlines()],[['--check']]);self.assertEqual(list(root.glob('hnls-install.*')),[])
   urls=(root/'fetches').read_text();self.assertIn('/releases/download/v'+version+'/',urls);self.assertEqual(len(urls.splitlines()),2)
 def test_baked_published_installer_accepts_no_repo_or_version_flags(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d);source=m.render(ROOT,'TestOwner/HNLS',version)
   r=subprocess.run(['bash','-s','--','--check'],input=source,text=True,env=env,capture_output=True,timeout=15);self.assertEqual(r.returncode,0,r.stderr)
 def test_receiver_role_is_forwarded_to_full_fresh_installer(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d);r=self.run_script(env,version,'--role','receiver');self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual([json.loads(x) for x in (root/'calls').read_text().splitlines()],[['--check'],['--role','receiver']])
 def test_checksum_mismatch_runs_no_code(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d,checksum=False);r=self.run_script(env,version,'--check');self.assertNotEqual(r.returncode,0);self.assertIn('checksum mismatch',r.stderr);self.assertFalse((root/'calls').exists());self.assertEqual(list(root.glob('hnls-install.*')),[])
 def test_unsafe_archive_paths_and_symlinks_run_no_code(self):
  for name in ['HNLS/../../escape','/absolute','HNLS\\escape','HNLS/a/../b','outside/file']:
   with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
    root,env,version=self.fixture(d,{name:'bad'});r=self.run_script(env,version,'--check');self.assertNotEqual(r.returncode,0);self.assertFalse((root/'calls').exists())
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d);archive=root/'downloads'/('HNLS-'+version+'-source.zip')
   with zipfile.ZipFile(archive,'a') as z:
    info=zipfile.ZipInfo('HNLS/link');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'../../escape')
   (archive.parent/'SHA256SUMS.txt').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
   r=self.run_script(env,version,'--check');self.assertNotEqual(r.returncode,0);self.assertFalse((root/'calls').exists())
 def test_wrong_release_version_runs_no_installer(self):
  with tempfile.TemporaryDirectory() as d:
   root,env,version=self.fixture(d,{'HNLS/VERSION':'9.9.9'});r=self.run_script(env,version,'--check');self.assertNotEqual(r.returncode,0);self.assertIn('version does not match',r.stderr);self.assertFalse((root/'calls').exists())
 def test_invalid_arguments_never_download(self):
  for args in [('a/b/../../c','1.0.0'),('a/b','../../x'),('a/$(id)','1.0.0')]:
   with self.subTest(args=args),tempfile.TemporaryDirectory() as d:
    root,env,version=self.fixture(d);r=subprocess.run(['bash','-s','--','--repo',args[0],'--version',args[1],'--check'],input=(ROOT/'setup.sh').read_text(),text=True,env=env,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertFalse((root/'fetches').exists())
 def test_release_renderer_and_commands_reject_untrusted_fields(self):
  for repo,version in [('a/b;id','1.0.0'),('a/b','v1.0.0'),('a/b','$(id)')]:
   with self.assertRaises(ValueError):m.render(ROOT,repo,version)
  self.assertIn('hnls-setup.sh | bash',m.command('HourNerd/HNLS','1.0.0'))
  self.assertTrue(m.command('HourNerd/HNLS','1.0.0','receiver').endswith('--role receiver'))
 def test_syntax_and_help_work_without_network_or_configuration(self):
  subprocess.run(['bash','-n',str(ROOT/'setup.sh')],check=True)
  r=subprocess.run(['bash',str(ROOT/'setup.sh'),'--help'],text=True,capture_output=True);self.assertEqual(r.returncode,0);self.assertIn('Main Pi',r.stdout)
