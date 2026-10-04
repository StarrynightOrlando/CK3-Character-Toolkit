from pathlib import Path
import json,hashlib,re,shutil,subprocess,datetime,uuid,zipfile,os
from .pds import entries,fields,block
from .guidance import handoff
from .runtime import build_runtime,RUNTIME_NAME
from .product import ADAPTER,PRODUCT_ID,WRITE_SELECTORS
from .versioning import TOOL_VERSION,game_version,supported_version
ROOT=Path(__file__).resolve().parents[1]
class BridgeError(Exception):pass
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,obj):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
 return h.hexdigest()
def safe_id(value):
 if not re.fullmatch(r'[a-z][a-z0-9_]{2,47}',value):raise BridgeError('ID 必须为 3–48 个小写字母、数字或下划线，以字母开头。')
 return value
def inside(root,path):
 root=Path(root).resolve();path=Path(path).resolve()
 if not path.is_relative_to(root) or path==root:raise BridgeError('目标超出工作目录：'+str(path))
 return path
def settings():return load(ROOT/'settings.local.json')
def profile(name):
 p=load(inside(ROOT/'profiles.local',ROOT/'profiles.local'/(safe_id(name)+'.json')))
 safe_id(p['id'])
 if p['id']!=name:raise BridgeError('配置 ID 必须与文件名一致')
 if p['adapter']!=ADAPTER:raise BridgeError('未知适配器')
 if p.get('schema_version')!=1:raise BridgeError('不支持的配置版本')
 return p
def doctor():
 s=settings();checks={}
 for key in ('blender','pdx_tools','game'):
  checks[key]={'path':s.get(key,''),'exists':Path(s.get(key,'/__missing__')).exists()}
 checks['pdx_reader']={'exists':(Path(s['pdx_tools'])/'io_pdx_mesh/pdx_data.py').exists()}
 checks['ck3_shader']={'exists':(Path(s['game'])/'gfx/FX/court_scene.shader').exists()}
 return {'ok':all(x['exists'] for x in checks.values()),'checks':checks,'game_version':game_version(s['game']),'tool_version':TOOL_VERSION,'runtime_tested':False}
def new_job(p,action):
 out=ROOT/'builds'/(datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+p['id']+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 save(out/'job.json',{'profile':p,'action':action,'status':'created','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'game_tested':False});return out
def worker(p,out,action,log=None):
 s=settings();request={'profile':p,'settings':s,'action':action,'output':str(out)};save(out/'request.local.json',request)
 cmd=[s['blender'],'--background','--disable-autoexec','--python-exit-code','7','--python',str(ROOT/'bridge/blender_worker.py'),'--',str(out/'request.local.json')]
 with (out/'worker.log').open('a',encoding='utf-8') as f:
  proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));code=proc.wait()
 if code:raise BridgeError(f'Blender 阶段失败（{code}）；查看 {out / "worker.log"}')
 if log:log('Blender 阶段完成')
def replacements(p):
 old='csc_'+p['reference_slot'];new='char_'+p['id']
 return [(f'gfx/FX/{old}_v013.shader','gfx/FX/ck3char_avatar.shader'),('csc_orlando_v013_','ck3char_avatar_'),(old,new),('csc_blank',new+'_blank'),('csc_flat_normal',new+'_flat_normal'),('csc_flat_properties',new+'_flat_properties')]
def remap(text,p):
 for old,new in replacements(p):text=text.replace(old,new)
 return text
def package_controls(p,out):
 ref=Path(p['reference_mod']);mod=out/'package/mod';new='char_'+p['id'];old='csc_'+p['reference_slot'];ptype=new+'_3d'
 def write(rel,text,bom=False):
  dest=mod/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text,encoding='utf-8-sig' if bom else 'utf-8')
 types=entries((ref/'common/portrait_types/csc_personal_types.txt').read_text(encoding='utf-8-sig'));chosen=next(e for e in types if e['key']==old+'_3d')
 write(f'common/portrait_types/{new}.txt',remap(chosen['raw'],p))
 contract=out/'camera_contract.json'
 if contract.is_file():
  from .camera_contract import rewrite_types
  path=mod/f'common/portrait_types/{new}.txt';path.write_text(rewrite_types(path.read_text(encoding='utf-8'),load(contract)['attachments']),encoding='utf-8-sig')
 write(f'common/ethnicities/{new}.txt',new+'_ethnicity = { portrait_group = '+ptype+' }\n')
 decision=new+'_appearance_decision'
 write(f'common/decisions/{new}.txt',block(decision,'is_shown = { is_ai = no }\nis_valid = { is_adult = yes }\neffect = { set_ethnicity = '+new+'_ethnicity }\nai_check_interval = 0'))
 title=p['display_name'].replace('"','').replace('\n',' ')
 for lang in ('english','simp_chinese'):
  strings={decision:title,decision+'_desc':'Apply this model appearance.' if lang=='english' else '将当前统治者切换为此模型外观。',decision+'_confirm':'Apply' if lang=='english' else '应用外观',decision+'_tooltip':title}
  write(f'localization/{lang}/{new}_l_{lang}.yml','l_'+lang+':\n'+''.join(f' {k}:0 "{v}"\n' for k,v in strings.items()),True)
 selectors={}
 if p['adapter']=='character':
  for rel in ('common/genes','gfx/portraits/accessories','gfx/portraits/portrait_modifiers','gfx/portraits/portrait_animations'):
   for src in (ref/rel).glob(old+'_native*'):
    if src.is_file():write(rel+'/'+remap(src.name,p),remap(src.read_text(encoding='utf-8-sig'),p))
  for e in entries((ref/'gfx/portraits/portrait_animations/animations.txt').read_text(encoding='utf-8-sig')):
   if e['block']:
    parts=[remap(x['raw'],p) for x in entries(e['inner']) if x['key'].startswith(old+'_3d_')]
    if parts:selectors[e['key']]='\n'.join(parts)
 save(out/'package/selectors.json',selectors)
 from .hardening import repair_accessory_names
 from .checklists import emit_checklist
 save(out/'accessory_reference_repairs.json',repair_accessory_names(mod,new))
 emit_checklist(out,p['display_name'])
 manifest={'schema_version':1,'id':p['id'],'display_name':p['display_name'],'adapter':p['adapter'],'runtime_api':1,'product_id':PRODUCT_ID,'requires_runtime':RUNTIME_NAME,'namespace':new,'portrait_group':ptype,'source_private':True,'runtime_tested':False,'selectors_sha256':digest(out/'package/selectors.json'),'files':{q.relative_to(mod).as_posix():digest(q) for q in mod.rglob('*') if q.is_file()}}
 manifest['part_roles']={remap(k,p):v for k,v in p.get('part_roles',{}).items()};manifest['author_notes']=p.get('author_notes',[])
 if (out/'stance_report.json').exists():manifest['stance']=load(out/'stance_report.json')
 save(out/'package/manifest.json',manifest)
def run(name,action='audit',log=print):
 if action not in ('audit','build'):raise BridgeError('未知操作')
 p=profile(name);out=new_job(p,action)
 try:
  if not doctor()['ok']:raise BridgeError('依赖检查未通过')
  if not Path(p['prepared_blend']).is_file():raise BridgeError('准备后的 Blender 文件不存在')
  log(f'{p["adapter"]} / {p["display_name"]}：{action}');worker(p,out,action,log)
  audit=load(out/'audit.json')
  if action=='build':
   if audit['errors']:raise BridgeError('; '.join(audit['errors']))
   package_controls(p,out)
   if not load(out/'validation.json')['passed']:raise BridgeError('模型包校验失败')
  j=load(out/'job.json');j.update(status='complete',runtime_tested=False);save(out/'job.json',j)
  (out/'AI交接报告.txt').write_text(handoff(p,'构建通过；待游戏验收' if action=='build' else '检查完成',out,audit['warnings']+audit['errors']),encoding='utf-8')
  log('完成：'+str(out));return out
 except Exception as exc:
  j=load(out/'job.json');j.update(status='failed',error=str(exc));save(out/'job.json',j)
  (out/'AI交接报告.txt').write_text(handoff(p,'失败',out,[str(exc)]),encoding='utf-8');raise
def build_batch(names,log=print):
 results=[]
 for name in names:
  try:results.append({'profile':name,'ok':True,'output':str(run(name,'build',log))})
  except Exception as exc:results.append({'profile':name,'ok':False,'error':str(exc)});log(str(exc))
 return results
def compile_bundle(packages,bundle_id,log=print):
 safe_id(bundle_id);s=settings();dest=ROOT/'builds'/('bundle_'+bundle_id+'_'+uuid.uuid4().hex[:8]);dest.mkdir(parents=True);mod=dest/'models';runtime=dest/'runtime';mod.mkdir();seen=set();fragments={};inventory=[]
 for package in packages:
  package=Path(package).resolve();m=load(package/'manifest.json');safe_id(m['id'])
  if m.get('adapter')!=ADAPTER or m.get('requires_runtime')!=RUNTIME_NAME:raise BridgeError('模型包不属于本工具或前置依赖不符')
  if m.get('schema_version')!=1 or m.get('runtime_api')!=1:raise BridgeError('不支持的模型包契约')
  if m.get('namespace')!='char_'+m['id'] or m.get('portrait_group')!='char_'+m['id']+'_3d':raise BridgeError('模型包命名空间不匹配')
  if digest(package/'selectors.json')!=m.get('selectors_sha256'):raise BridgeError('动作片段哈希不符')
  if m['id'] in seen:raise BridgeError('重复模型 ID：'+m['id'])
  seen.add(m['id'])
  for rel,h in m['files'].items():
   src=inside(package/'mod',package/'mod'/rel);target=inside(mod,mod/rel)
   if not src.is_file() or digest(src)!=h:raise BridgeError('模型包文件哈希不符：'+rel)
   if target.exists():raise BridgeError('模型包文件冲突：'+rel)
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
  for key,value in load(package/'selectors.json').items():
   allowed={m['portrait_group']+'_'+s for s in ('male','female','boy','girl')}
   if any(e['key'] not in allowed for e in entries(value)):raise BridgeError('选择器尝试覆盖其他模型或原版人物：'+key)
   fragments.setdefault(key,[]).append(value)
  inventory.append(m)
 fallbacks={m['id']:[] for m in inventory}
 if WRITE_SELECTORS:
  selectors=[];fallbacks={m['id']:[] for m in inventory};vanilla=entries((Path(s['game'])/'gfx/portraits/portrait_animations/animations.txt').read_text(encoding='utf-8-sig'));known={e['key'] for e in vanilla}
  if set(fragments)-known:raise BridgeError('游戏版本缺少动作选择器：'+str(set(fragments)-known))
  for e in vanilla:
   if not e['block']:selectors.append(e['raw']);continue
   additions=list(fragments.get(e['key'],[]));present={x['key'] for text in additions for x in entries(text)}
   for m in inventory:
    ptype=m['portrait_group']
    if ptype+'_male' not in present:
     additions.append(block(ptype+'_male','default = { head = "idle" torso = "idle" }')+''.join(ptype+'_'+suffix+' = '+ptype+'_male\n' for suffix in ('female','boy','girl')));fallbacks[m['id']].append(e['key'])
   selectors.append(block(e['key'],e['inner']+'\n'+'\n'.join(additions)))
  selector=mod/'gfx/portraits/portrait_animations/animations.txt';selector.parent.mkdir(parents=True,exist_ok=True);selector.write_text('\n'.join(selectors),encoding='utf-8')
 build_runtime(s['game'],runtime)
 (mod/'descriptor.mod').write_text(f'version="{TOOL_VERSION}"\nname="CK3 Character Toolkit Models - {bundle_id}"\nsupported_version="{supported_version(s["game"])}"\ndependencies={{ "{RUNTIME_NAME}" }}\ntags={{ "Portraits" }}\n',encoding='utf-8')
 from .hardening import audit
 from .checklists import emit_checklist,emit_paths
 roles={k:v for m in inventory for k,v in m.get('part_roles',{}).items()};check=audit(mod,s['game'],s.get('pdx_tools',''),runtime,roles);check['author_notes']=[note for m in inventory for note in m.get('author_notes',[])];save(dest/'自动检查报告.json',check);emit_checklist(dest,bundle_id,check)
 emit_paths(dest,bundle_id,s.get('mod_root',Path.home()/'Documents/Paradox Interactive/Crusader Kings III/mod'))
 from .action_trace import state_map
 save(dest/'姿势到动画文件.json',{'game_visual_verified':False,'states':state_map(mod)})
 save(dest/'姿势修正范围.json',{'experimental':True,'game_visual_verified':False,'models':{m['id']:m.get('stance',{'enabled':False}) for m in inventory},'note':'未选中动作及所有运行时混合仍需实际验收；离线并腿结果不能证明抱臂等其他姿势已修复。'})
 if not check['passed']:raise BridgeError('模型包自动检查未通过：'+str(dest/'自动检查报告.json'))
 save(dest/'bundle.json',{'schema_version':1,'bundle_id':bundle_id,'packages':[x['id'] for x in inventory],'runtime_api':1,'runtime_tested':False,'idle_fallbacks':fallbacks,'game_selector_sha256':digest(Path(s['game'])/'gfx/portraits/portrait_animations/animations.txt'),'files':{p.relative_to(dest).as_posix():digest(p) for tree in (mod,runtime) for p in tree.rglob('*') if p.is_file()}})
 for model,names in fallbacks.items():
  if names:log(f'兼容提示：{model} 有 {len(names)} 个入口未提供动作映射，已显式回退待机；详见 bundle.json 的 idle_fallbacks。')
 (dest/'安装与测试.txt').write_text('这是未通过游戏验收的候选组合包。runtime 是公共前置，models 是选中模型的组合模组。\n通过工具 install 命令安装到新的本地模组目录，再在启动器中手动启用。\n不要同时启用另一份由此工具生成的组合模组；需要多个模型时先一起 compile。\n依次验证人物面板、理发器、皇家宫廷和自身动作。不要把文件校验通过当成游戏验收。',encoding='utf-8')
 log('组合包：'+str(dest));return dest
def _rollback_legacy(txn):
 txn=inside(ROOT/'state/installs',txn);m=load(txn/'transaction.json')
 if m['status'] not in ('installed','partial'):raise BridgeError('该事务不可回退')
 # Preflight every target before any mutation.
 for r in m['records']:
  target=inside(m['mod_root'],r['target']);inside(m['mod_root'],r['descriptor'])
  if target.exists() and (not (target/'.ck3char-owned.json').is_file() or load(target/'.ck3char-owned.json').get('transaction')!=txn.name):raise BridgeError('回退目标归属或安装版本已变化')
 for r in reversed(m['records']):
  target=Path(r['target']);desc=Path(r['descriptor'])
  if target.exists():shutil.rmtree(inside(m['mod_root'],target))
  if r['existed']:shutil.copytree(txn/'before'/r['key'],target)
  if r['descriptor_existed']:shutil.copy2(txn/'before'/(r['key']+'.mod'),desc)
  elif desc.exists():desc.unlink()
 m['status']='rolled_back';save(txn/'transaction.json',m)
 from .checklists import emit_paths
 emit_paths(txn,m.get('bundle_id','previous_install'),m['mod_root'],m['records'],'rolled_back')
 if m.get('bundle'):emit_paths(m['bundle'],m.get('bundle_id','previous_install'),m['mod_root'],m['records'],'rolled_back')
def install_bundle(bundle,mod_root,storage_root=None):
 from .installation import install
 return install(bundle,mod_root,storage_root)

def rollback(txn):
 txn=inside(ROOT/'state/installs',txn)
 if load(txn/'transaction.json').get('layout')=='linked_v1':
  from .installation import rollback as linked_rollback
  return linked_rollback(txn)
 return _rollback_legacy(txn)

def public_zip():
 out=ROOT/'builds/CK3-Character-Toolkit-source.zip';out.parent.mkdir(exist_ok=True)
 allow=['bridge','docs','examples','tests','tools','.github'];files=[ROOT/name for name in ('bridge_cli.py','启动工具.cmd','start.ps1','.gitignore','.gitattributes','README.md','README.txt','LICENSE.md','THIRD_PARTY_NOTICES.md','CHANGELOG.md')]
 for folder in allow:files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
 permitted={'.py','.txt','.json','.html','.ps1','.cmd','.md','.yml','.yaml'}
 for p in files:
  if p.exists() and (not p.resolve().is_relative_to(ROOT.resolve()) or (p.name not in ('.gitignore','.gitattributes') and p.suffix.lower() not in permitted) or '.local.' in p.name):raise BridgeError('公开工具包遇到非源码/私人文件，请先移出公开目录：'+str(p.relative_to(ROOT)))
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for p in files:
   if p.exists():z.write(p,p.relative_to(ROOT).as_posix())
 return out
