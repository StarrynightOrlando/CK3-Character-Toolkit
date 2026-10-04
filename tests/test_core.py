import unittest,tempfile,json,zipfile
from pathlib import Path
from unittest.mock import patch
from bridge import core
from bridge.pds import entries,block
from bridge.adapters import ADAPTERS
from bridge.product import ADAPTER,WRITE_SELECTORS
from bridge.runtime import RUNTIME_NAME
class CoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.patch=patch.object(core,'ROOT',self.root);self.patch.start();self.audit_patch=patch('bridge.hardening.audit',return_value={'passed':True,'issues':[],'runtime_verified':False});self.audit_patch.start()
 def tearDown(self):self.audit_patch.stop();self.patch.stop();self.temp.cleanup()
 def write(self,path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
 def bundle(self,value='v1'):
  p=self.root/('bundle_'+value)
  for kind in ('runtime','models'):
   self.write(p/kind/'descriptor.mod','name="test"\n');self.write(p/kind/'data.txt',value)
  core.save(p/'bundle.json',{'bundle_id':'test_models','files':{q.relative_to(p).as_posix():core.digest(q) for q in p.rglob('*') if q.is_file()}});return p
 def test_parser_handles_braces_in_strings_and_comments(self):
  text='a = { value = "}" # { ignored\n nested = { x = 1 } }\nb = a'
  result=entries(text);self.assertEqual([x['key'] for x in result],['a','b']);self.assertEqual(entries(result[0]['inner'])[0]['value'],'"}"')
 def test_path_escape_is_rejected(self):
  with self.assertRaises(core.BridgeError):core.inside(self.root/'out',self.root/'out/../secret')
 def test_invalid_ids(self):
  for value in ('../x','Aaa','abc-def','ab','x\n../../bad'):
   with self.assertRaises(core.BridgeError):core.safe_id(value)
 def test_only_own_adapter_is_distributed(self):
  self.assertEqual(set(ADAPTERS),{ADAPTER});self.assertEqual(ADAPTERS[ADAPTER].native_human_actions,WRITE_SELECTORS)
 def test_install_then_rollback_preserves_existing(self):
  mods=self.root/'mods';one=core.install_bundle(self.bundle(),mods);two=core.install_bundle(self.bundle('v2'),mods)
  self.assertIn('path="'+(mods.resolve()/'ck3char_test_models').as_posix()+'"',(mods/'ck3char_test_models.mod').read_text(encoding='utf-8-sig'))
  self.assertEqual((mods/'ck3char_test_models/data.txt').read_text(),'v2')
  with self.assertRaises(core.BridgeError):core.rollback(one)
  core.rollback(two);self.assertEqual((mods/'ck3char_test_models/data.txt').read_text(),'v1')
  self.assertEqual(core.load(two/'测试模组位置.json')['installation_state'],'rolled_back')
  core.rollback(one);self.assertFalse((mods/'ck3char_test_models').exists());self.assertFalse((mods/'ck3char_runtime.mod').exists())
 def test_refuses_unowned_directory_before_changes(self):
  mods=self.root/'mods';self.write(mods/'ck3char_test_models/data.txt','mine')
  with self.assertRaises(core.BridgeError):core.install_bundle(self.bundle(),mods)
  self.assertEqual((mods/'ck3char_test_models/data.txt').read_text(),'mine');self.assertFalse((mods/'ck3char_runtime').exists())
 def test_failed_staging_does_not_touch_installed_mod(self):
  mods=self.root/'mods';core.install_bundle(self.bundle(),mods);original=core.shutil.copytree;count=[0]
  def failing(src,dst,*a,**kw):
   count[0]+=1
   if count[0]==2:raise OSError('Injected copy failure')
   return original(src,dst,*a,**kw)
  with patch.object(core.shutil,'copytree',side_effect=failing):
   with self.assertRaises(OSError):core.install_bundle(self.bundle('v2'),mods)
  self.assertEqual((mods/'ck3char_test_models/data.txt').read_text(),'v1');self.assertFalse(list(mods.glob('.ck3char-stage-*')))
 def test_tampered_package_is_not_installed(self):
  b=self.bundle();self.write(b/'models/data.txt','tampered')
  with self.assertRaises(core.BridgeError):core.install_bundle(b,self.root/'mods')
 def test_public_zip_excludes_private_artifacts(self):
  for file in ('bridge/core.py','docs/guide.txt','examples/example.json','tests/test.py','bridge_cli.py','start.ps1'):self.write(self.root/file,'public')
  for file in ('settings.local.json','profiles.local/private.json','state/secret','builds/avatar.blend','first_batch.log','bridge/__pycache__/private.pyc'):self.write(self.root/file,'SECRET')
  with zipfile.ZipFile(core.public_zip()) as z:
   self.assertIn('start.ps1',z.namelist());self.assertTrue(all(b'SECRET' not in z.read(n) for n in z.namelist()))
 def package(self,id,extra=''):
  p=self.root/('pack_'+id);self.write(p/'mod/common/test'/f'{id}.txt',id);core.save(p/'selectors.json',{'idle':block('char_'+id+'_3d_male','default = { torso = "idle" head = "idle" }')});core.save(p/'manifest.json',{'schema_version':1,'adapter':ADAPTER,'requires_runtime':RUNTIME_NAME,'runtime_api':1,'namespace':'char_'+id,'portrait_group':'char_'+id+'_3d','id':id,'selectors_sha256':core.digest(p/'selectors.json'),'files':{f'common/test/{id}.txt':core.digest(p/'mod/common/test'/f'{id}.txt')}});return p
 def test_compiler_merges_two_selectors_and_preserves_vanilla(self):
  game=self.root/'game';self.write(game/'gfx/portraits/portrait_animations/animations.txt','idle = { male = { default = { torso = "vanilla" } } }')
  core.save(self.root/'settings.local.json',{'game':str(game)})
  with patch.object(core,'build_runtime',side_effect=lambda game,out:self.write(out/'descriptor.mod','name="runtime"')):
   result=core.compile_bundle([self.package('alpha'),self.package('beta')],'pair',lambda x:None)
  if not WRITE_SELECTORS:
   self.assertFalse((result/'models/gfx/portraits/portrait_animations/animations.txt').exists());return
  e=entries((result/'models/gfx/portraits/portrait_animations/animations.txt').read_text())[0];self.assertEqual([x['key'] for x in entries(e['inner'])],['male','char_alpha_3d_male','char_beta_3d_male'])
 def test_compiler_rejects_foreign_selector_keys(self):
  core.save(self.root/'settings.local.json',{'game':str(self.root/'game')});p=self.package('alpha');core.save(p/'selectors.json',{'idle':block('male','default = { torso = "hijacked" }')});m=core.load(p/'manifest.json');m['selectors_sha256']=core.digest(p/'selectors.json');core.save(p/'manifest.json',m)
  with self.assertRaises(core.BridgeError):core.compile_bundle([p],'pair',lambda x:None)
 def test_compiler_rejects_duplicate_model_ids(self):
  game=self.root/'game';core.save(self.root/'settings.local.json',{'game':str(game)});p=self.package('alpha')
  with self.assertRaises(core.BridgeError):core.compile_bundle([p,p],'pair',lambda x:None)
 def test_new_game_selector_gets_reported_idle_fallback(self):
  game=self.root/'game';self.write(game/'gfx/portraits/portrait_animations/animations.txt','idle = { default = {} } new_action = { default = {} }');core.save(self.root/'settings.local.json',{'game':str(game)})
  with patch.object(core,'build_runtime',side_effect=lambda game,out:self.write(out/'descriptor.mod','runtime')):
   result=core.compile_bundle([self.package('alpha')],'pair',lambda x:None)
  if not WRITE_SELECTORS:
   self.assertFalse((result/'models/gfx/portraits/portrait_animations/animations.txt').exists());return
  m=core.load(result/'bundle.json');self.assertEqual(m['idle_fallbacks']['alpha'],['new_action'])
  text=(result/'models/gfx/portraits/portrait_animations/animations.txt').read_text();self.assertIn('char_alpha_3d_male',entries(text)[1]['inner'])
 def test_failed_publish_restores_both_previous_trees(self):
  from bridge import installation
  mods=self.root/'mods';core.install_bundle(self.bundle(),mods);original=installation.make_link;count=[0]
  def failing(path,target):
   count[0]+=1
   if count[0]==2:raise OSError('Injected publish failure')
   return original(path,target)
  with patch.object(installation,'make_link',failing):
   with self.assertRaises(OSError):core.install_bundle(self.bundle('v2'),mods)
  for key in ('ck3char_runtime','ck3char_test_models'):self.assertEqual((mods/key/'data.txt').read_text(),'v1')
 def test_linked_install_verifies_and_preserves_manual_changes(self):
  from bridge.installation import verify,linked
  mods=self.root/'mods';storage=self.root/'资源盘';txn=core.install_bundle(self.bundle(),mods,storage)
  self.assertTrue(linked(mods/'ck3char_test_models'));self.assertTrue((mods/'ck3char_test_models').resolve().is_relative_to(storage.resolve()))
  self.assertTrue(verify(txn)['installed_files_verified'])
  (mods/'ck3char_test_models/data.txt').write_text('manual fix')
  self.assertFalse(verify(txn)['installed_files_verified'])
  with self.assertRaises(core.BridgeError):core.rollback(txn)
  self.assertEqual((mods/'ck3char_test_models/data.txt').read_text(),'manual fix')
 def test_install_rejects_unmanifested_files(self):
  b=self.bundle();self.write(b/'models/extra.txt','unexpected')
  with self.assertRaises(core.BridgeError):core.install_bundle(b,self.root/'mods')
 def test_public_zip_rejects_model_in_documentation(self):
  self.write(self.root/'docs/private_avatar.fbx','private model')
  with self.assertRaises(core.BridgeError):core.public_zip()
if __name__=='__main__':unittest.main()
