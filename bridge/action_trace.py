"""Static entity/state -> clip map. Screenshots do not identify runtime states."""
from pathlib import Path
from .pds import entries,fields
from . import core

def locate(path):
 path=Path(path).resolve()
 return path/'models' if (path/'models').is_dir() else path/'mod' if (path/'mod').is_dir() else path

def state_map(path):
 mod=locate(path);meshes={};entities=[];result=[]
 for asset in mod.rglob('*.asset'):
  for entry in entries(asset.read_text(encoding='utf-8-sig')):
   if entry['key']=='pdxmesh':
    f=fields(entry['inner']);clips={}
    for child in entries(entry['inner']):
     if child['key'] in ('animation','additive_animation'):
      c=fields(child['inner']);clips[c.get('id')]=c.get('type')
    meshes[f.get('name')]=(asset,clips)
   elif entry['key']=='entity':entities.append((asset,entry))
 for asset,entry in entities:
  f=fields(entry['inner']);mesh=f.get('pdxmesh');clipasset,clips=meshes.get(mesh,(asset,{}))
  for child in entries(entry['inner']):
   if child['key']!='state':continue
   st=fields(child['inner']);anim=st.get('animation');rel=clips.get(anim);file=(clipasset.parent/rel).resolve() if rel else None
   result.append({'entity':f.get('name'),'state':st.get('name'),'animation_id':anim,'file':str(file) if file else None,'file_exists':bool(file and file.is_file()),'next_state':st.get('next_state'),'chance':st.get('chance'),'asset':str(asset),'mesh':mesh})
 return result

def trace(path,state):
 rows=state_map(path);matches=[r for r in rows if r['state']==state or r['animation_id']==state]
 for row in matches:
  if row['file_exists']:row['sha256']=core.digest(Path(row['file']))
 return {'query':state,'matches':matches,'query_matched':bool(matches),'game_visual_verified':False,'note':'静态映射可能有多个候选；不能从截图推断当前运行时状态。请记录理发器动作名称/事件/人物类型，再对照实体状态与动画 ID。'}
