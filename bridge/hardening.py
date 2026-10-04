"""Read-only contract audits for authors and AI. Findings are not gameplay QA."""
from pathlib import Path
import re,sys,json,collections,math,logging
from .pds import entries,fields,TOKEN
def scalar_refs(text,key):
 tokens=[m[0] for m in TOKEN.finditer(text) if not m[0].startswith('#')]
 return [tokens[i+2].strip('"') for i in range(len(tokens)-2) if tokens[i]==key and tokens[i+1]=='=' and tokens[i+2] not in ('{','}')]
def repair_accessory_names(mod,prefix):
 mod=Path(mod);defs={e['key'] for p in (mod/'gfx/portraits/accessories').glob('*.txt') for e in entries(p.read_text(encoding='utf-8-sig'))};stem=prefix+'_native_';mapping={name[len(stem):]:name for name in defs if name.startswith(stem)};changes=[]
 for p in (mod/'gfx/portraits/portrait_modifiers').glob(prefix+'*.txt'):
  text=p.read_text(encoding='utf-8-sig')
  tokens=[m for m in TOKEN.finditer(text) if not m[0].startswith('#')];edits=[]
  for i in range(len(tokens)-2):
   if tokens[i][0]!='accessory' or tokens[i+1][0]!='=':continue
   value=tokens[i+2];name=value[0].strip('"')
   if name in mapping:changes.append({'file':str(p.relative_to(mod)),'from':name,'to':mapping[name]});edits.append((value.start(),value.end(),'"'+mapping[name]+'"'))
  for start,end,value in reversed(edits):text=text[:start]+value+text[end:]
  p.write_text(text,encoding='utf-8-sig')
 return changes
def audit(mod,game,pdx_tools,runtime=None,part_roles=None):
 sys.path.insert(0,str(pdx_tools));from io_pdx_mesh import pdx_data
 logging.getLogger('io_pdx.data').setLevel(logging.WARNING)
 mod=Path(mod);game=Path(game);runtime=Path(runtime) if runtime else mod if (mod/'gfx/FX').is_dir() else None;issues=[];meshes={};entities={};meshdefs={};groups=[];parts=[];motion_reports=[];part_roles=part_roles or {};animation_checks=0;checked_clips=set();shader_effects={}
 def finding(level,code,message,**context):issues.append({'level':level,'code':code,'message':message,**context})
 for p in mod.rglob('*.asset'):
  for e in entries(p.read_text(encoding='utf-8-sig')):
   if e['key'] not in ('pdxmesh','entity'):continue
   f=fields(e['inner']);name=f.get('name')
   if e['key']=='entity':entities[name]=e;continue
   meshdefs[name]=(p,e);path=p.parent/f.get('file','')
   if not path.is_file():finding('error','MESH_MISSING',str(path));continue
   t=pdx_data.read_meshfile(str(path));sk=t.find('object')[0].find('skeleton');names=[b.tag for b in sk];meshes[name]={'path':path,'tree':t,'names':names,'sk':sk}
   if f.get('streaming')!='Never':finding('error','PORTRAIT_STREAMING',f'{name} 缺少 streaming = Never')
   if len(set(names))!=len(names):finding('error','DUPLICATE_BONE',name)
   for i,bone in enumerate(sk):
    parent=bone.get('pa',[-1])[0]
    if parent>=i or parent< -1:finding('error','BONE_PARENT_INDEX',bone.tag)
   from .animation_audit import clip_errors
   for binding in entries(e['inner']):
    if binding['key'] not in ('animation','additive_animation'):continue
    af=fields(binding['inner']);clip_path=(p.parent/af.get('type','')).resolve();signature=(str(clip_path),tuple(names))
    if not clip_path.is_relative_to(mod.resolve()):finding('error','ANIMATION_PATH_ESCAPE',str(clip_path));continue
    if signature in checked_clips:continue
    checked_clips.add(signature)
    if not clip_path.is_file():finding('error','ANIMATION_MISSING',str(clip_path));continue
    try:
     errors=clip_errors(pdx_data.read_meshfile(str(clip_path)),names);animation_checks+=1
     for error in errors:finding('error','ANIMATION_CONTRACT',error,file=str(clip_path))
    except (ValueError,KeyError,IndexError,TypeError,OSError) as exc:finding('error','ANIMATION_READ',str(exc),file=str(clip_path))
   if 'bn_sp_cervical' in names and (path.parent/(path.stem+'.asset')).exists():
    from .motion_guard import process_folder
    try:
     motion=process_folder(path.parent,path.stem,write=False);motion_reports.append({k:v for k,v in motion.items() if k!='changes'})
     for change in motion['changes']:finding('warning','NECK_PROPORTION_VARIATION',change['file'],changes=change['changes'])
    except (OSError,ValueError,IndexError,KeyError,TypeError) as exc:finding('error','MOTION_GUARD_READ',str(exc),file=str(path))
   definitions={fields(x['inner']).get('id') for x in entries(e['inner']) if x['key'] in ('animation','additive_animation')}
   for ent in entries(p.read_text(encoding='utf-8-sig')):
    if ent['key']=='entity':
     for state in entries(ent['inner']):
      if state['key']=='state':
       a=fields(state['inner']).get('animation')
       if a and a not in definitions:finding('error','ANIMATION_REFERENCE',a,asset=str(p))
   for x in entries(e['inner']):
    if x['key']=='meshsettings':
     mf=fields(x['inner']);shape=t.find('object').find(mf['name']);sub=shape.findall('mesh') if shape is not None else [];i=int(mf.get('index',0))
     if i>=len(sub) or sub[i].find('material') is None:finding('error','EMPTY_SUBMESH',mf['name'],index=i);continue
     mat=sub[i].find('material')
     if mat.get('shader')!=[mf.get('shader')]:finding('error','SHADER_BINDING',mf['name'],index=i)
     if runtime and mf.get('shader_file'):
      candidates=[(base/mf['shader_file']).resolve() for base in (mod,runtime,game)]
      valid=[p for p,base in zip(candidates,(mod,runtime,game)) if p.is_relative_to(base.resolve()) and p.is_file()]
      shader_path=valid[0] if valid else None
      if shader_path is None:finding('error','SHADER_FILE_MISSING',mf['shader_file'])
      else:
       from .runtime import effect_names
       if shader_path not in shader_effects:shader_effects[shader_path]=set(effect_names(shader_path.read_text(encoding='utf-8-sig')))
       if mf.get('shader') not in shader_effects[shader_path]:finding('error','SHADER_EFFECT_MISSING',str(mf.get('shader')),file=str(shader_path))
     for key in ('texture_diffuse','texture_normal','texture_specular'):
      if key in mf and not (p.parent/mf[key]).is_file():finding('error','TEXTURE_MISSING',mf[key])
   for shape in t.find('object'):
    if [b.attrib for b in shape.find('skeleton')]!=[b.attrib for b in sk] or [b.tag for b in shape.find('skeleton')]!=names:finding('error','SHAPE_SKELETON_MISMATCH',shape.tag)
    for part_index,part in enumerate(shape.findall('mesh')):
     skin=part.find('skin')
     if skin is None:continue
     ix=skin.get('ix',[]);weights=skin.get('w',[]);width=skin.get('bones',[4])[0]
     totals=collections.Counter()
     for index,weight in zip(ix,weights):
      if weight>0 and 0<=index<len(names):totals[names[index]]+=weight
     total=sum(totals.values()) or 1;skirt=sum(w for n,w in totals.items() if 'skirt' in n.lower())/total;hip=sum(w for n,w in totals.items() if n in ('Hips','body_root'))/total
     parts.append({'shape':shape.tag,'material_index':part_index,'role':part_roles.get(shape.tag,'待作者标注'),'vertices':len(part.get('p',[]))//3,'triangles':len(part.get('tri',[]))//3,'dominant_bones':[{'bone':n,'weight_fraction':round(w/total,5)} for n,w in totals.most_common(8)],'skirt_bone_weight_fraction':round(skirt,5),'hip_weight_fraction':round(hip,5)})
     if part_roles.get(shape.tag)=='skirt' and skirt<.01 and hip>.9:finding('warning','SKIRT_RIGID_HIP',shape.tag)
     if any(w>0 and (i<0 or i>=len(names)) for i,w in zip(ix,weights)):finding('error','SKIN_INDEX',shape.tag)
     if any(abs(sum(weights[i:i+width])-1)>.01 for i in range(0,len(weights),width)):finding('warning','SKIN_WEIGHT_SUM',shape.tag)
 for p in (mod/'common/portrait_types').glob('*.txt'):
  for group in entries(p.read_text(encoding='utf-8-sig')):
   if not group['block']:continue
   types=[(x,fields(x['inner'])) for x in entries(group['inner']) if x['block'] and x['key']!='attach'];used=set();receivers=[]
   for x,f in types:
    if 'head' not in f or 'torso' not in f:continue
    hn=fields(entities[f['head']]['inner']).get('pdxmesh') if f['head'] in entities else None;bn=fields(entities[f['torso']]['inner']).get('pdxmesh') if f['torso'] in entities else None
    if hn not in meshes or bn not in meshes:finding('error','PORTRAIT_ENTITY',x['key']);continue
    head,body=meshes[hn],meshes[bn];used.update(head['names']+body['names']);receivers.append((x['key'],set(head['names']),set(body['names'])))
    for key,target in [('bn_h_head',head),('bn_h_head_mid',head),('camera_torso_look_at',body),('bn_l_prop',body),('bn_r_prop',body),('ground_joint',body)]:
     if key not in target['names']:finding('error','NODE_MISSING',key,portrait_type=x['key'])
    if any(n in body['names'] for n in ('bn_h_head','bn_h_head_mid')) or 'camera_torso_look_at' in head['names']:finding('error','AMBIGUOUS_CAMERA_NODE',x['key'])
    for part,ref in [(head,'female_head'),(body,'female_body')]:
     stock=pdx_data.read_meshfile(str(game/f'gfx/models/portraits/{ref}/{ref}.mesh'));native=[b.tag for b in stock.find('object')[0].find('skeleton')]
     if part['names'][:len(native)]!=native:finding('error','NATIVE_NODE_LAYOUT',x['key'],mesh=str(part['path']))
    groups.append({'type':x['key'],'sex':f.get('sex'),'minimum_age':f.get('minimum_age'),'maximum_age':f.get('maximum_age'),'head':hn,'body':bn})
   for attach in [x for x in entries(group['inner']) if x['key']=='attach']:
    for joint in [x for x in entries(attach['inner']) if x['key']=='joint_attachment']:
     f=fields(joint['inner'])
     for portrait_type,head_nodes,body_nodes in receivers:
      if f.get('parent_joint') not in body_nodes or f.get('child_joint') not in head_nodes:finding('error','ATTACHMENT_NODE',str(f),portrait_type=portrait_type)
 allnodes=set(n for m in meshes.values() for n in m['names']);accessories={}
 for p in (mod/'gfx/portraits/accessories').glob('*.txt'):
  for e in entries(p.read_text(encoding='utf-8-sig')):
   if e['block']:accessories[e['key']]=e
  for node in scalar_refs(p.read_text(encoding='utf-8-sig'),'node'):
   if node not in allnodes:finding('error','PROP_NODE_MISSING',node,file=str(p))
 for p in (mod/'gfx/portraits/portrait_modifiers').glob('*.txt'):
  for ref in scalar_refs(p.read_text(encoding='utf-8-sig'),'accessory'):
   if ref not in accessories and ref not in ('none','default'):finding('error','PROP_ACCESSORY_REFERENCE',ref,file=str(p))
 for section in ('cameras','environments'):
  for p in (mod/'gfx/portraits'/section).glob('*.txt'):
   if (game/p.relative_to(mod)).exists():finding('error','GLOBAL_PORTRAIT_OVERRIDE',str(p.relative_to(mod)))
 selectors=mod/'gfx/portraits/portrait_animations/animations.txt'
 if selectors.is_file():
  original={e['key']:e for e in entries((game/'gfx/portraits/portrait_animations/animations.txt').read_text(encoding='utf-8-sig'))};custom={x['type'] for x in groups}
  def tokens(text):return [m[0] for m in TOKEN.finditer(text) if not m[0].startswith('#')]
  for e in entries(selectors.read_text(encoding='utf-8-sig')):
   if e['block'] and e['key'] in original:
    kept='\n'.join(x['raw'] for x in entries(e['inner']) if x['key'] not in custom)
    if tokens(kept)!=tokens(original[e['key']]['inner']):finding('error','VANILLA_SELECTOR_CHANGED',e['key'])
 if runtime:
  effects=[]
  for p in runtime.rglob('*.shader'):
   if (game/p.relative_to(runtime)).exists():finding('error','GLOBAL_SHADER_FILE_OVERRIDE',str(p.relative_to(runtime)))
   from .runtime import effect_names
   names=effect_names(p.read_text(encoding='utf-8-sig'));effects.extend(names)
   for name in names:
    if not name.startswith('ck3char_'):finding('error','FOREIGN_EFFECT',name,file=str(p))
  for name,count in collections.Counter(effects).items():
   if count>1:finding('error','DUPLICATE_EFFECT',name,count=count)
 if not meshes:finding('error','NO_PORTRAIT_MESH','没有找到可检查的人物网格；空目录不能算检查通过')
 if not groups:finding('error','NO_PORTRAIT_TYPES','没有找到有效人物类型')
 return {'passed':not any(x['level']=='error' for x in issues),'runtime_verified':False,'portrait_types':groups,'mesh_count':len(meshes),'animation_clips_checked':animation_checks,'accessory_count':len(accessories),'mesh_parts':parts,'motion_proportion_checks':motion_reports,'issues':issues,'manual_required':['身体裁切','裙摆蒙皮与过渡','站姿宽度及具体动作状态','特殊动作颈部伸缩','道具实际握持','男女与年龄镜头','原版人物回归']}
