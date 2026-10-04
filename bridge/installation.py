"""Versioned physical installs with small launcher links, verified before publish."""
from pathlib import Path
import os,shutil,subprocess,uuid
from . import core

MARKER='.ck3char-owned.json'

def linked(path):
 return path.is_symlink() or bool(getattr(path,'is_junction',lambda:False)())

def exists(path):return os.path.lexists(path)

def make_link(path,target):
 if exists(path):raise core.BridgeError('兼容入口已存在：'+str(path))
 if os.name=='nt':
  env=os.environ.copy();env['CK3CHAR_LINK_PATH']=str(path);env['CK3CHAR_LINK_TARGET']=str(target)
  subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:CK3CHAR_LINK_PATH -Target $env:CK3CHAR_LINK_TARGET | Out-Null"],env=env,check=True,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 else:path.symlink_to(target,target_is_directory=True)
 if not linked(path) or path.resolve()!=target.resolve():raise core.BridgeError('兼容入口验证失败：'+str(path))

def remove_link(path,expected):
 if not linked(path) or path.resolve()!=Path(expected).resolve():raise core.BridgeError('兼容入口指向已变化，拒绝移除：'+str(path))
 if path.is_symlink():path.unlink()
 else:os.rmdir(path)  # Removes only the junction, never its target tree.

def inventory(root):
 root=Path(root);result={}
 for p in root.rglob('*'):
  if linked(p):raise core.BridgeError('安装资源不能含目录链接：'+str(p))
  if p.is_file() and p.name!=MARKER:result[p.relative_to(root).as_posix()]=core.digest(p)
 return result

def verify_bundle(bundle):
 manifest=core.load(bundle/'bundle.json');core.safe_id(manifest['bundle_id'])
 declared=manifest.get('files',{});actual={}
 for kind in ('runtime','models'):
  if not (bundle/kind/'descriptor.mod').is_file():raise core.BridgeError('缺少模组描述文件：'+kind)
  if (bundle/kind/MARKER).exists():raise core.BridgeError('输入组合包包含安装归属标记')
  actual.update({kind+'/'+rel:h for rel,h in inventory(bundle/kind).items()})
 if actual!=declared:raise core.BridgeError('组合包清单与实际文件不一致；含缺失、改动或未登记文件')
 return manifest

def verify(txn):
 txn=core.inside(core.ROOT/'state/installs',txn);m=core.load(txn/'transaction.json');issues=[];count=0
 if m.get('layout')!='linked_v1':raise core.BridgeError('旧安装事务不支持此核验；使用 check 检查现有模组')
 if m.get('status')!='installed':issues.append('事务尚未安装或已回退')
 for r in m['records']:
  link=Path(r['target']);physical=Path(r['physical']);descriptor=Path(r['descriptor'])
  if not linked(link) or link.resolve()!=physical.resolve():issues.append('入口未指向本次安装：'+str(link));continue
  marker=physical/MARKER
  if not marker.is_file() or core.load(marker).get('transaction')!=txn.name:issues.append('归属标记已变化：'+str(physical))
  if not descriptor.is_file() or core.digest(descriptor)!=r['descriptor_sha256']:issues.append('启动器描述文件已变化：'+str(descriptor))
  try:
   expected={rel.split('/',1)[1]:h for rel,h in m['files'].items() if rel.startswith(r['kind']+'/')}
   if inventory(link)!=expected:issues.append('实际安装文件与本次组合包不一致：'+str(link))
   count+=len(expected)
  except (OSError,ValueError) as exc:issues.append(str(exc))
 return {'installed_files_verified':not issues,'files_checked':count,'transaction':str(txn),'issues':issues,'game_loaded':False,'game_visual_verified':False,'requires_full_game_restart':True}

def install(bundle,mod_root,storage_root=None):
 bundle=Path(bundle).resolve();m=verify_bundle(bundle);mods=Path(mod_root).resolve();storage=Path(storage_root or core.ROOT/'installed').resolve()
 if storage==mods or storage.is_relative_to(mods) or mods.is_relative_to(storage):raise core.BridgeError('资源目录与启动器 mod 目录必须分离且互不嵌套')
 if storage==bundle or storage.is_relative_to(bundle) or bundle.is_relative_to(storage):raise core.BridgeError('资源目录与候选组合包必须分离且互不嵌套')
 mods.mkdir(parents=True,exist_ok=True);storage.mkdir(parents=True,exist_ok=True)
 txn=core.ROOT/'state/installs'/uuid.uuid4().hex;records=[]
 for kind,key in [('runtime','ck3char_runtime'),('models','ck3char_'+m['bundle_id'])]:
  target=mods/key;desc=mods/(key+'.mod');old=None
  if exists(target):
   if not linked(target) or not (target/MARKER).is_file():raise core.BridgeError('拒绝覆盖已有实体目录或非本工具入口：'+str(target))
   owned=core.load(target/MARKER)
   if owned.get('tool')!='CK3 Character Toolkit' or owned.get('key')!=key:raise core.BridgeError('安装入口归属不符：'+str(target))
   old=str(target.resolve())
  if desc.exists() and old is None:raise core.BridgeError('拒绝覆盖已有启动器描述文件：'+str(desc))
  if linked(desc):raise core.BridgeError('描述文件不能是链接')
  physical=core.inside(storage,storage/(key+'_'+txn.name))
  records.append({'key':key,'kind':kind,'target':str(target),'descriptor':str(desc),'physical':str(physical),'old_target':old,'descriptor_existed':desc.exists()})
 txn.mkdir(parents=True);(txn/'before').mkdir()
 for r in records:
  if r['descriptor_existed']:shutil.copy2(r['descriptor'],txn/'before'/(r['key']+'.mod'))
 state={'layout':'linked_v1','status':'prepared','bundle_id':m['bundle_id'],'bundle':str(bundle),'mod_root':str(mods),'storage_root':str(storage),'files':m['files'],'records':records}
 core.save(txn/'transaction.json',state);applied=[]
 try:
  for r in records:
   dest=Path(r['physical']);shutil.copytree(bundle/r['kind'],dest)
   expected={rel.split('/',1)[1]:h for rel,h in m['files'].items() if rel.startswith(r['kind']+'/')}
   if inventory(dest)!=expected:raise core.BridgeError('资源复制校验失败：'+str(dest))
   core.save(dest/MARKER,{'tool':'CK3 Character Toolkit','transaction':txn.name,'key':r['key']})
  for r in records:
   link=Path(r['target']);dest=Path(r['physical']);applied.append(r)
   if r['old_target']:remove_link(link,r['old_target'])
   make_link(link,dest)
   text=(dest/'descriptor.mod').read_text(encoding='utf-8-sig')
   # Absolute compatibility entry avoids Chinese physical paths and assumptions
   # about which CK3 user-data directory is active.
   text+='\npath="'+link.as_posix()+'"\n'
   Path(r['descriptor']).write_text(text,encoding='utf-8-sig');r['descriptor_sha256']=core.digest(Path(r['descriptor']))
  state['status']='installed';core.save(txn/'transaction.json',state);check=verify(txn)
  if not check['installed_files_verified']:raise core.BridgeError('安装读回核验失败：'+str(check['issues']))
  core.save(txn/'安装核验.json',check)
 except Exception:
  # Restore every entry touched during this transaction. Keep physical versions
  # for recovery; never recursively delete through a launcher junction.
  for r in reversed(applied):
   link=Path(r['target']);desc=Path(r['descriptor'])
   if exists(link) and link.resolve()==Path(r['physical']).resolve():remove_link(link,r['physical'])
   if r['old_target'] and not exists(link):make_link(link,Path(r['old_target']))
   if r['descriptor_existed']:shutil.copy2(txn/'before'/(r['key']+'.mod'),desc)
   elif desc.exists():desc.unlink()
  state['status']='failed_restored';core.save(txn/'transaction.json',state);raise
 from .checklists import emit_paths
 emit_paths(bundle,m['bundle_id'],mods,records,'installed');emit_paths(txn,m['bundle_id'],mods,records,'installed')
 return txn

def rollback(txn):
 txn=core.inside(core.ROOT/'state/installs',txn);m=core.load(txn/'transaction.json');check=verify(txn)
 if not check['installed_files_verified']:raise core.BridgeError('回退前核验失败；拒绝覆盖后续安装或人工修改：'+str(check['issues']))
 for r in m['records']:
  if r['old_target'] and not (Path(r['old_target'])/MARKER).is_file():raise core.BridgeError('前一版本已不存在，无法回退')
  if r['descriptor_existed'] and not (txn/'before'/(r['key']+'.mod')).is_file():raise core.BridgeError('缺少前一版本描述文件')
 for r in reversed(m['records']):
  link=Path(r['target']);desc=Path(r['descriptor']);remove_link(link,r['physical'])
  if r['old_target']:make_link(link,Path(r['old_target']))
  if r['descriptor_existed']:shutil.copy2(txn/'before'/(r['key']+'.mod'),desc)
  else:desc.unlink()
 m['status']='rolled_back';core.save(txn/'transaction.json',m)
 from .checklists import emit_paths
 emit_paths(txn,m['bundle_id'],m['mod_root'],m['records'],'rolled_back')
 if Path(m['bundle']).is_dir():emit_paths(m['bundle'],m['bundle_id'],m['mod_root'],m['records'],'rolled_back')
