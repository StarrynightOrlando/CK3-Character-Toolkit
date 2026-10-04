"""Blender subprocess. Reads private source; writes only the job directory."""
import sys,json,logging,copy,math,shutil,re,xml.etree.ElementTree as X
from pathlib import Path
import bpy
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bridge.core import load,save,remap,digest
from bridge.pds import entries,fields
from bridge.adapters import ADAPTERS
request=load(sys.argv[sys.argv.index('--')+1]);p=request['profile'];s=request['settings'];OUT=Path(request['output']);sys.path.insert(0,s['pdx_tools'])
from io_pdx_mesh import pdx_data
from io_pdx_mesh.pdx_blender import blender_import_export as pdx
logging.getLogger('io_pdx.data').setLevel(logging.WARNING)
old='csc_'+p['reference_slot'];new='char_'+p['id'];ref=Path(p['reference_mod'])/'gfx/models/portraits'/old
source=Path(p['prepared_blend']);source_hash=digest(source);bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.frame_set(1)
rigs=[o for o in scene.objects if o.type=='ARMATURE'];objects=[o for o in scene.objects if o.type=='MESH']
audit={'adapter':p['adapter'],'prepared_source':str(source),'source_sha256':source_hash,'rigs':[{'name':o.name,'bones':len(o.data.bones),'scale':list(o.scale)} for o in rigs],'parts':[],'warnings':[],'errors':[],'runtime_tested':False}
for o in objects:
 o.data.calc_loop_triangles()
 used={poly.material_index for poly in o.data.polygons}
 audit['parts'].append({'object':o.name,'shape':o.data.name,'vertices':len(o.data.vertices),'triangles_before_export':len(o.data.loop_triangles),'polygons':len(o.data.polygons),'materials':[m.name if m else None for m in o.data.materials],'unused_material_slots':[i for i in range(len(o.data.materials)) if i not in used],'shape_keys':len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,'active_shape_keys':{k.name:float(k.value) for k in o.data.shape_keys.key_blocks if k.value} if o.data.shape_keys else {},'negative_transform':o.matrix_world.determinant()<0,'visible':not o.hide_render,'dimensions':list(o.dimensions)})
 if o.matrix_world.determinant()<0:audit['warnings'].append('负变换/镜像需确认：'+o.name)
if len(rigs)!=1:audit['errors'].append('RIG_COUNT：需要确认并准备一个最终骨架；当前 '+str(len(rigs)))
rig=rigs[0] if rigs else None
body_asset=entries((ref/(old+'.asset')).read_text(encoding='utf-8-sig'));pm=next(e for e in body_asset if e['key']=='pdxmesh')
bindings=[fields(e['inner']) for e in entries(pm['inner']) if e['key']=='meshsettings'];expected={b['name'] for b in bindings};present={o.data.name for o in objects};allowed=set(p.get('exclude_shapes',[]))
if expected-present:audit['errors'].append('MISSING_PARTS：'+str(sorted(expected-present)))
if present-expected-allowed:audit['errors'].append('UNREVIEWED_PARTS：'+str(sorted(present-expected-allowed)))
for shape in expected:
 if sum(o.data.name==shape for o in objects)>1:audit['errors'].append('DUPLICATE_SHAPE：'+shape)
reference=pdx_data.read_meshfile(str(ref/(old+'.mesh')));refsk=reference.find('object')[0].find('skeleton');names=[b.tag for b in refsk]
helpers=set(p.get('add_reference_helpers',[]));have=set(rig.data.bones.keys()) if rig else set()
if set(names)-have-helpers:audit['errors'].append('BONE_MAP_REQUIRED：'+str(sorted(set(names)-have-helpers)))
if have-set(names):audit['errors'].append('EXTRA_BONES_REVIEW：'+str(sorted(have-set(names))))
adapter=ADAPTERS[p['adapter']]();adapter.audit(p,audit,rig)
save(OUT/'audit.json',audit)
if request['action']=='audit':print('AUDIT_COMPLETE');raise SystemExit(0)
if audit['errors']:raise RuntimeError('; '.join(audit['errors']))
if request['action']=='preview':
 from bridge.preview import render
 render(p,OUT,objects,expected,rig);raise SystemExit(0)
raw=OUT/'intermediate';raw.mkdir();bpy.ops.object.select_all(action='DESELECT')
slot_maps={};removed_slots=[]
for o in objects:
 if o.data.name not in expected:continue
 used=sorted({poly.material_index for poly in o.data.polygons})
 if not used:raise RuntimeError('EMPTY_GEOMETRY: '+o.name)
 if len(used)!=len(o.data.materials):
  old_slots=list(o.data.materials);old_indices=[poly.material_index for poly in o.data.polygons];mapping={old:new for new,old in enumerate(used)};slot_maps[o.data.name]=mapping
  o.data.materials.clear()
  for old_index in used:o.data.materials.append(old_slots[old_index])
  for poly,old_index in zip(o.data.polygons,old_indices):poly.material_index=mapping[old_index]
  removed_slots.append({'shape':o.data.name,'removed_unused_slots':[i for i in range(len(old_slots)) if i not in mapping],'visible_faces_removed':0})
new_bindings=[]
for item in bindings:
 if item['name'] in slot_maps:
  mapping=slot_maps[item['name']]
  if int(item['index']) not in mapping:continue
  item=dict(item);item['index']=str(mapping[int(item['index'])])
 new_bindings.append(item)
bindings=new_bindings;save(OUT/'empty_slot_cleanup.json',removed_slots)
for o in objects:
 if o.data.name in expected:o.select_set(True)
bpy.context.view_layer.objects.active=rig
for item in bindings:
 o=next(o for o in objects if o.data.name==item['name']);mat=o.data.materials[int(item['index'])]
 mat['shader']=item['shader'];mat['csc_diffuse']=str(ref/item['texture_diffuse']);mat['csc_normal']=str(ref/item['texture_normal']);mat['csc_properties']=str(ref/item['texture_specular'])
pdx.get_material_textures=lambda m:{'diff':m['csc_diffuse'],'n':m['csc_normal'],'spec':m['csc_properties']}
print('EXPORT_GEOMETRY',flush=True);pdx.export_meshfile(str(raw/'body.mesh'),exp_locs=False,exp_selected=True)
mesh=pdx_data.read_meshfile(str(raw/'body.mesh'))
def world(sk):
 result={}
 for b in sk:
  x=b.get('tx');result[b.tag]=Matrix(((x[0],x[3],x[6],x[9]),(x[1],x[4],x[7],x[10]),(x[2],x[5],x[8],x[11]),(0,0,0,1))).inverted()
 return result
refworld=world(refsk);rawsk=mesh.find('object')[0].find('skeleton');newworld=world(rawsk);parents={b.tag:names[b.get('pa')[0]] if b.get('pa') else None for b in refsk}
newworld=adapter.normalize_bind(newworld)
for n in names:
 if n not in newworld:
  parent=parents[n];newworld[n]=newworld[parent]@refworld[parent].inverted()@refworld[n] if parent else refworld[n]
canonical=X.Element('skeleton')
for i,n in enumerate(names):
 inv=newworld[n].inverted();attrs={'ix':[i],'tx':[float(inv[r][c]) for c in range(4) for r in range(3)]}
 if parents[n]:attrs['pa']=[names.index(parents[n])]
 X.SubElement(canonical,n,attrs)
for shape in mesh.find('object'):
 sk=shape.find('skeleton');oldnames=[b.tag for b in sk]
 for m in shape.findall('mesh'):
  skin=m.find('skin')
  if skin is not None:skin.set('ix',[names.index(oldnames[i]) if i>=0 else -1 for i in skin.get('ix')])
 shape.remove(sk);shape.append(copy.deepcopy(canonical))
def local_decompose(worlds):return {n:(worlds[parents[n]].inverted()@worlds[n] if parents[n] else worlds[n]).decompose() for n in names}
sourcebind=local_decompose(refworld);targetbind=local_decompose(newworld)
max_bind_delta=max(abs(refworld[n][r][c]-newworld[n][r][c]) for n in names for r in range(4) for c in range(4))
pack=OUT/'package/mod/gfx/models/portraits'/new;pack.mkdir(parents=True)
needed=set();assets=[ref/(old+'.asset'),ref/(old+'_camera.asset')]
for asset in assets:
 text=asset.read_text(encoding='utf-8-sig');es=entries(text);meshblock=next(e for e in es if e['key']=='pdxmesh')
 if any(e['key']=='import' for e in entries(meshblock['inner'])):raise RuntimeError('UNBAKED_IMPORT：参考包依赖未转换的原版动画库。')
 for e in entries(meshblock['inner']):
  if e['key']=='file':needed.add(e['value'].strip('"'))
  elif e['key'] in ('animation','additive_animation'):needed.add(fields(e['inner'])['type'])
  elif e['key']=='meshsettings':
   for k,v in fields(e['inner']).items():
    if k in ('texture_diffuse','texture_normal','texture_specular'):needed.add(v)
 if slot_maps and asset.name==old+'.asset':
  from bridge.pds import block
  result=[]
  for item in es:
   if item['key']!='pdxmesh':result.append(item['raw']);continue
   inner=[]
   for setting in entries(item['inner']):
    if setting['key']=='meshsettings':
     f=fields(setting['inner']);mapping=slot_maps.get(f['name'])
     if mapping is not None:
      if int(f['index']) not in mapping:continue
      setting=dict(setting);setting['raw']=re.sub(r'\bindex\s*=\s*\d+','index = '+str(mapping[int(f['index'])]),setting['raw'],count=1)
    inner.append(setting['raw'])
   result.append(block('pdxmesh','\n'.join(inner)))
  text='\n'.join(result)
 (pack/remap(asset.name,p)).write_text(remap(text,p),encoding='utf-8')
def rewrite_mesh(tree):
 for shape in tree.find('object'):
  shape.tag=remap(shape.tag,p)
  for m in shape.findall('mesh'):
   mat=m.find('material')
   if mat is not None:
    for key,val in list(mat.attrib.items()):
     if val and isinstance(val[0],str):mat.set(key,[remap(v,p) for v in val])
 return tree
pdx_data.write_meshfile(str(pack/(new+'.mesh')),rewrite_mesh(mesh))
def retarget_clip(root):
 info=root.find('info');samples=root.find('samples');count=info.get('sa')[0]
 if [b.tag for b in info]!=names:raise RuntimeError('ANIM_BONE_ORDER：参考动作与参考网格顺序不同')
 dst=X.Element('File',{'pdxasset':[1,0]});di=X.SubElement(dst,'info',dict(info.attrib));ds=X.SubElement(dst,'samples');tracks={};width={'t':3,'q':4,'s':1}
 for k in width:
  active=[b for b in info if k in b.get('sa',[''])[0]];num=len(active);idx={b.tag:i for i,b in enumerate(active)};data=samples.get(k,[])
  if k=='s' and num:width[k]=len(data)//(count*num)
  w=width[k]
  for b in info:tracks.setdefault(b.tag,{})[k]=[data[(f*num+idx[b.tag])*w:(f*num+idx[b.tag]+1)*w] for f in range(count)] if b.tag in idx else [b.get(k)]*count
 rows={};flags={}
 for n in names:
  tt,tq,ts=targetbind[n];bt,bq,bs=sourcebind[n];dt=tt-bt;dq=tq@bq.inverted();rows[n]=[]
  for f in range(count):
   t=Vector(tracks[n]['t'][f])+dt;q=tracks[n]['q'][f];q=(dq@Quaternion((q[3],q[0],q[1],q[2]))).normalized();scale=tracks[n]['s'][f][0]*ts.x/bs.x
   rows[n].append({'t':tuple(round(float(x),6) for x in t),'q':tuple(round(float(x),7) for x in (q.x,q.y,q.z,q.w)),'s':(float(scale),)})
  flags[n]=''.join(k for k in ('t','q','s') if len({r[k] for r in rows[n]})>1)
  X.SubElement(di,n,{'sa':[flags[n]],**{k:list(rows[n][0][k]) for k in ('t','q','s')}})
 for k in ('t','q','s'):
  moving=[n for n in names if k in flags[n]]
  if moving:ds.set(k,[v for f in range(count) for n in moving for v in rows[n][f][k]])
 return dst
retargeted=0;copied=0
for i,rel in enumerate(sorted(needed)):
 src=(ref/rel).resolve()
 if not src.is_relative_to(ref.resolve()):raise RuntimeError('ASSET_PATH_ESCAPE：'+rel)
 dst=pack/remap(rel,p);dst.parent.mkdir(parents=True,exist_ok=True)
 if rel==old+'.mesh':continue
 if src.suffix=='.mesh':pdx_data.write_meshfile(str(dst),rewrite_mesh(pdx_data.read_meshfile(str(src))))
 elif src.suffix=='.anim':
  tree=pdx_data.read_meshfile(str(src));bone_names=[b.tag for b in tree.find('info')]
  if bone_names==names and max_bind_delta>.0001:
   tree=retarget_clip(tree);pdx_data.write_animfile(str(dst),tree);retargeted+=1
  else:shutil.copy2(src,dst);copied+=1
 else:shutil.copy2(src,dst)
 if i%100==0:print('PACKAGE_FILES',i+1,'/',len(needed),flush=True)
# Material shaders and mesh/animation contracts are checked on actual exported files.
from bridge.camera_contract import normalize
from bridge.hardening import scalar_refs
required=set(p.get('attachment_nodes',[]))
for accessories in (Path(p['reference_mod'])/'gfx/portraits/accessories').glob('*.txt'):required.update(scalar_refs(accessories.read_text(encoding='utf-8-sig'),'node'))
camera_contract=normalize(pack,new,s['game'],required);save(OUT/'camera_contract.json',camera_contract)
from bridge.motion_guard import process_folder
save(OUT/'motion_guard.json',process_folder(pack,new,p.get('motion_guard')))
from bridge.stance import process_folder as process_stance
save(OUT/'stance_report.json',process_stance(pack,new,p.get('stance')))
checks=[];animation_count=0
for asset in pack.glob('*.asset'):
 es=entries(asset.read_text(encoding='utf-8'));mp=next(e for e in es if e['key']=='pdxmesh');data=fields(mp['inner']);tree=pdx_data.read_meshfile(str(pack/data['file']));sk=tree.find('object')[0].find('skeleton');bone_names=[b.tag for b in sk]
 for shape in tree.find('object'):
  assert [b.tag for b in shape.find('skeleton')]==bone_names
  for m in shape.findall('mesh'):
   skin=m.find('skin')
   if skin is not None:assert all(v==-1 or 0<=v<len(sk) for v in skin.get('ix'))
 for entry in entries(mp['inner']):
  if entry['key']=='meshsettings':
   f=fields(entry['inner']);shape=tree.find('object').find(f['name']);assert shape is not None,f['name'];mat=shape.findall('mesh')[int(f['index'])].find('material');assert mat.get('shader')==[f['shader']],f
   for k in ('texture_diffuse','texture_normal','texture_specular'):assert (pack/f[k]).is_file(),f[k]
  if entry['key'] not in ('animation','additive_animation'):continue
  f=fields(entry['inner']);clip=pdx_data.read_meshfile(str(pack/f['type']));info=clip.find('info');sample=clip.find('samples');count=info.get('sa')[0]
  assert [b.tag for b in info]==bone_names,(f['id'],'ANIM_BONE_ORDER');assert info.get('j')==[len(sk)] and count>=1
  for k,w in [('t',3),('q',4),('s',1)]:
   total=sum(k in b.get('sa',[''])[0] for b in info)*count;values=sample.get(k,[]);assert len(values)==total*w or k=='s' and len(values)==total*3
   assert all(math.isfinite(v) for v in values);assert k not in sample.attrib or values
  animation_count+=1
assert digest(source)==source_hash,'Source file unexpectedly changed'
save(OUT/'validation.json',{'passed':True,'runtime_tested':False,'source_unchanged':True,'body_bones':camera_contract['body_bones_after'],'head_bones':camera_contract['head_bones'],'camera_layout':camera_contract['layout'],'animation_bindings_checked':animation_count,'clips_retargeted':retargeted,'clips_copied':copied,'maximum_bind_difference':max_bind_delta,'reference_contract':'Prepared-source adapter, not automatic raw Avatar conversion'})
print('MODEL_PACKAGE_VALID',flush=True)
from bridge.preview import render
render(p,OUT,objects,expected,rig)
print('BUILD_COMPLETE')
