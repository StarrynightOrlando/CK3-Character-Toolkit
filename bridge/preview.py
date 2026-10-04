"""Offline geometry/pose preview only; no CK3 shader or game execution."""
from pathlib import Path
import math,json,re
def render(profile,out,objects,expected,rig):
 import bpy
 from mathutils import Matrix,Vector,Quaternion
 from io_pdx_mesh import pdx_data
 from io_pdx_mesh.pdx_blender import blender_import_export as pdx
 from .pds import entries,fields
 scene=bpy.context.scene;out=Path(out);pack=out/'package/mod/gfx/models/portraits'/('char_'+profile['id'])
 for o in list(scene.objects):
  if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
 for o in objects:o.hide_render=o.data.name not in expected
 world=bpy.data.worlds.new('Bridge preview');world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.13,.15,.19,1);bg.inputs[1].default_value=.6;scene.world=world
 scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=700;scene.render.resolution_y=850;scene.render.resolution_percentage=100
 animations={}
 if profile['adapter']=='character':
  asset=entries((pack/('char_'+profile['id']+'.asset')).read_text());pm=next(e for e in asset if e['key']=='pdxmesh')
  for e in entries(pm['inner']):
   if e['key']=='animation':f=fields(e['inner']);animations[f['id']]=pack/f['type']
 variants=[('source_preview.png',None)] if not animations else [('source_preview.png','body_idle_1'),('preview_seated_pose.png','body_throneRoom_ruler2_1'),('preview_sword_pose.png','body_council_marshal')]
 if profile.get('preview_actions'):
  if not all(re.fullmatch(r'[A-Za-z0-9_]+',a) for a in profile['preview_actions']):raise ValueError('Invalid preview action id')
  variants=[('preview_'+a+'.png',a) for a in profile['preview_actions']]
 contract_path=out/'camera_contract.json';reverse={}
 if contract_path.is_file():reverse={v:k for k,v in json.loads(contract_path.read_text(encoding='utf-8-sig')).get('renamed_internal_anchors',{}).items()}
 for filename,action in variants:
  if action and action not in animations:continue
  if action:
   clip=pdx_data.read_meshfile(str(animations[action]));info=clip.find('info');data=clip.find('samples');frame=min(info.get('sa')[0]-1,120);width={'t':3,'q':4,'s':1};counts={k:sum(k in b.get('sa',[''])[0] for b in info) for k in width}
   if counts['s']:width['s']=len(data.get('s'))//(counts['s']*info.get('sa')[0])
   cursor={k:frame*counts[k]*width[k] for k in width}
   for bone in info:
    values={}
    for k,w in width.items():
     if k in bone.get('sa',[''])[0]:values[k]=data.get(k)[cursor[k]:cursor[k]+w];cursor[k]+=w
     else:values[k]=bone.get(k)
    name=reverse.get(bone.tag,bone.tag)
    if name not in rig.pose.bones:continue
    t,q,scale=values['t'],values['q'],values['s'];scale=scale*3 if len(scale)==1 else scale
    local=pdx.swap_coord_space(Matrix.LocRotScale(Vector(t),Quaternion((q[3],q[0],q[1],q[2])),Vector(scale)));b=rig.data.bones[name]
    bind=b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local
    if not b.parent:local=rig.matrix_world.inverted()@local
    rig.pose.bones[name].matrix_basis=bind.inverted()@local
   bpy.context.view_layer.update()
  points=[];deps=bpy.context.evaluated_depsgraph_get()
  for o in objects:
   if o.data.name in expected:
    e=o.evaluated_get(deps);points.extend(e.matrix_world@v.co for v in e.data.vertices)
  lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));center=(lo+hi)/2;span=max((hi-lo).x*850/700,(hi-lo).z)*1.25
  for o in list(scene.objects):
   if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
  for pos,power in [((-1,-2,2),180),((2,1,1),120)]:
   bpy.ops.object.light_add(type='AREA',location=center+Vector(pos)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
  bpy.ops.object.camera_add(location=center+Vector((span*.12,-span*2,span*.025)));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=span;cam.data.clip_end=10000;scene.camera=cam
  scene.render.filepath=str(out/filename);bpy.ops.render.render(write_still=True)
