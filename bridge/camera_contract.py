"""Integrated-body portrait camera carrier using the native head/body layout.

This aligns node ownership and indices with installed native assets. It does not
claim that a particular engine cache implementation has been established.
Run inside Blender (mathutils), against a disposable build/candidate directory.
"""
from pathlib import Path
import copy,xml.etree.ElementTree as X
from .pds import entries,fields,block

def normalize(folder,prefix,game,required_nodes=()):
 from mathutils import Matrix,Vector,Quaternion
 from io_pdx_mesh import pdx_data
 folder=Path(folder);game=Path(game)
 def read(path):return pdx_data.read_meshfile(str(path))
 def world(sk):
  result={}
  for b in sk:
   x=b.get('tx');result[b.tag]=Matrix(((x[0],x[3],x[6],x[9]),(x[1],x[4],x[7],x[10]),(x[2],x[5],x[8],x[11]),(0,0,0,1))).inverted()
  return result
 def parents(sk):
  names=[b.tag for b in sk];return {b.tag:names[b.get('pa')[0]] if b.get('pa') else None for b in sk}
 def bone(name,index,parent,worldmatrix,order):
  inv=worldmatrix.inverted();data={'ix':[index],'tx':[float(inv[r][c]) for c in range(4) for r in range(3)]}
  if parent is not None:data['pa']=[order.index(parent)]
  return X.Element(name,data)
 def neutral(name,local):
  t,q,s=local.decompose();return X.Element(name,{'sa':[''],'t':list(t),'q':[q.x,q.y,q.z,q.w],'s':[s.x]})
 bodyfile=folder/(prefix+'.mesh');headfile=folder/(prefix+'_camera.mesh');body=read(bodyfile);head=read(headfile)
 oldsk=body.find('object')[0].find('skeleton');oldnames=[b.tag for b in oldsk];oldparents=parents(oldsk);oldworld=world(oldsk)
 # Never replace visible face geometry using this proxy-specific adapter.
 if sum(len(m.get('p',[]))//3 for o in head.find('object') for m in o.findall('mesh'))>3:
  raise ValueError('CAMERA_PROXY_CONTRACT: expected the invisible three-vertex carrier')
 nativebody=read(game/'gfx/models/portraits/female_body/female_body.mesh').find('object')[0].find('skeleton')
 nativehead=read(game/'gfx/models/portraits/female_head/female_head.mesh').find('object')[0].find('skeleton')
 base=[b.tag for b in nativebody];bp=parents(nativebody);bw=world(nativebody);horder=[b.tag for b in nativehead];hp=parents(nativehead);hw=world(nativehead)
 reparent={}
 for n in base:
  if n in oldparents and oldparents[n]!=bp[n]:
   if n=='camera_torso_look_at':reparent[n]=bp[n]
   else:raise ValueError('NATIVE_PARENT_MISMATCH: '+n+': '+str(oldparents[n])+' vs '+str(bp[n]))
 rename={n:prefix+'_'+n+'_anchor' for n in ('bn_h_head','bn_h_head_mid') if n in oldnames}
 if len(rename)!=2:raise ValueError('HEAD_ANCHOR_REQUIRED: explicit integrated-body head and mid anchors are required')
 keep=set(base)|set(rename)|set(required_nodes)
 for shape in body.find('object'):
  for mesh in shape.findall('mesh'):
   skin=mesh.find('skin')
   if skin is not None:keep.update(oldnames[i] for i,w in zip(skin.get('ix'),skin.get('w')) if i>=0 and w>0)
 for n in list(keep):
  while n in oldparents and oldparents[n]:n=oldparents[n];keep.add(n)
 order=base+[rename.get(n,n) for n in oldnames if n not in base and n in keep]
 nw={rename.get(n,n):m.copy() for n,m in oldworld.items()};np={rename.get(n,n):rename.get(p,p) for n,p in oldparents.items()}
 np.update(reparent)
 inserted=[]
 for n in base:
  if n not in nw:
   parent=bp[n];nw[n]=nw[parent]@bw[parent].inverted()@bw[n] if parent else bw[n];np[n]=parent;inserted.append(n)
 for i,n in enumerate(order):
  if np[n] is not None and order.index(np[n])>=i:raise ValueError('FORWARD_PARENT: '+n)
 sk=X.Element('skeleton')
 original_bones={rename.get(b.tag,b.tag):b for b in oldsk}
 for i,n in enumerate(order):
  b=bone(n,i,np[n],nw[n],order)
  if n in original_bones:b.set('tx',list(original_bones[n].get('tx')))
  sk.append(b)
 old_to_new={i:order.index(rename.get(n,n)) for i,n in enumerate(oldnames) if rename.get(n,n) in order}
 for o in body.find('object'):
  assert [b.tag for b in o.find('skeleton')]==oldnames
  for mesh in o.findall('mesh'):
   skin=mesh.find('skin')
   if skin is not None:skin.set('ix',[old_to_new.get(i,-1) if i>=0 else -1 for i in skin.get('ix')])
  o.remove(o.find('skeleton'));o.append(copy.deepcopy(sk))
 loc=body.find('locator')
 if loc is not None:
  for locator in loc:
   if locator.tag in rename:locator.tag=rename[locator.tag]
   if locator.get('pa'):locator.set('pa',[rename.get(v,v) for v in locator.get('pa')])
 # Body geometry, inverse binds of existing joints, and every retained track
 # remain unchanged. Only index packing and private anchor names are changed.
 pdx_data.write_meshfile(str(bodyfile),body)
 pm=next(e for e in entries((folder/(prefix+'.asset')).read_text(encoding='utf-8-sig')) if e['key']=='pdxmesh')
 clips=sorted({fields(e['inner'])['type'] for e in entries(pm['inner']) if e['key'] in ('animation','additive_animation')})
 local={n:nw[np[n]].inverted()@nw[n] if np[n] else nw[n] for n in order}
 for ci,rel in enumerate(clips):
  path=folder/rel;t=read(path);info=t.find('info');samples=t.find('samples');assert [b.tag for b in info]==oldnames
  count=info.get('sa')[0];root=X.Element('File',dict(t.attrib));di=X.SubElement(root,'info',dict(info.attrib));di.set('j',[len(order)]);ds=X.SubElement(root,'samples')
  lookup={rename.get(b.tag,b.tag):b for b in info}
  overrides={}
  if reparent:
   byname={b.tag:b for b in info};active={k:[b.tag for b in info if k in b.get('sa',[''])[0]] for k in ('t','q','s')};widths={'t':3,'q':4,'s':1}
   if active['s']:widths['s']=len(samples.get('s'))//(len(active['s'])*count)
   offsets={k:{n:i for i,n in enumerate(active[k])} for k in active}
   for n in reparent:overrides[n]=[]
   for frame in range(count):
    cache={}
    def posed_world(n):
     if n in cache:return cache[n]
     b=byname[n];v={}
     for k,w in widths.items():
      if n in offsets[k]:start=(frame*len(active[k])+offsets[k][n])*w;v[k]=samples.get(k)[start:start+w]
      else:v[k]=b.get(k)
     q=v['q'];s_=v['s']*3 if len(v['s'])==1 else v['s'];m=Matrix.LocRotScale(Vector(v['t']),Quaternion((q[3],q[0],q[1],q[2])),Vector(s_));parent=oldparents[n];cache[n]=posed_world(parent)@m if parent else m;return cache[n]
    for n,newparent in reparent.items():
     mat=posed_world(newparent).inverted()@posed_world(n);tr,qr,sr=mat.decompose();overrides[n].append({'t':list(tr),'q':[qr.x,qr.y,qr.z,qr.w],'s':[sr.x]})
  for n in order:
   b=copy.deepcopy(lookup[n]) if n in lookup else neutral(n,local[n]);b.tag=n
   if n in overrides:b.attrib={'sa':['tq'],'t':overrides[n][0]['t'],'q':overrides[n][0]['q'],'s':overrides[n][0]['s']}
   di.append(b)
  for key,width in [('t',3),('q',4),('s',1)]:
   active=[b.tag for b in info if key in b.get('sa',[''])[0]];raw=samples.get(key,[])
   if key=='s' and active:width=len(raw)//(len(active)*count)
   offsets={rename.get(n,n):i for i,n in enumerate(active)};chosen=[b.tag for b in di if key in b.get('sa',[''])[0]]
   values=[]
   for f in range(count):
    for n in chosen:
     if n in overrides:values.extend(overrides[n][f][key])
     else:values.extend(raw[(f*len(active)+offsets[n])*width:(f*len(active)+offsets[n]+1)*width])
   if values:ds.set(key,values)
  pdx_data.write_animfile(str(path),root)
  if ci%100==0:print('NATIVE_CAMERA_BODY_TRACKS',ci+1,'/',len(clips),flush=True)
 # The camera/light anchors belong to the head at the native indices 3/22;
 # camera_torso_look_at belongs only to the native body slot.
 target={n:nw['bn_sp_thoracic']@hw['head_root'].inverted()@hw[n] for n in horder}
 for n in rename:target[n]=nw[rename[n]]
 hs=X.Element('skeleton')
 for i,n in enumerate(horder):hs.append(bone(n,i,hp[n],target[n],horder))
 for o in head.find('object'):
  for m in o.findall('mesh'):
   skin=m.find('skin')
   if skin is not None:skin.set('ix',[0 if weight>0 else -1 for weight in skin.get('w')])
  o.remove(o.find('skeleton'));o.append(copy.deepcopy(hs))
 if head.find('locator') is not None:head.find('locator').clear()
 pdx_data.write_meshfile(str(headfile),head)
 headpm=next(e for e in entries((folder/(prefix+'_camera.asset')).read_text(encoding='utf-8-sig')) if e['key']=='pdxmesh')
 headclips=sorted({fields(e['inner'])['type'] for e in entries(headpm['inner']) if e['key']=='animation'})
 for rel in headclips:
  path=folder/rel;old=read(path).find('info');r=X.Element('File',{'pdxasset':[1,0]});info=X.SubElement(r,'info',{'fps':old.get('fps'),'sa':old.get('sa'),'j':[len(horder)]});X.SubElement(r,'samples')
  for n in horder:info.append(neutral(n,target[hp[n]].inverted()@target[n] if hp[n] else target[n]))
  pdx_data.write_animfile(str(path),r)
 for filename in (prefix+'.asset',prefix+'_camera.asset'):
  path=folder/filename;es=entries(path.read_text(encoding='utf-8-sig'));out=[]
  for e in es:
   if e['key']=='pdxmesh':out.append(block('pdxmesh','streaming = Never\n'+'\n'.join(x['raw'] for x in entries(e['inner']) if x['key']!='streaming')))
   else:out.append(e['raw'])
  path.write_text('\n'.join(out),encoding='utf-8-sig')
 attachments=[('bn_sp_thoracic','head_root'),(rename['bn_h_head'],'bn_h_head'),(rename['bn_h_head_mid'],'bn_h_head_mid')]
 return {'layout':'native_head_body_v1','body_bones_before':len(oldnames),'body_bones_after':len(order),'head_bones':len(horder),'native_body_prefix':len(base),'inserted_unweighted_native_joints':inserted,'pruned_unweighted_extra_nodes':[n for n in oldnames if n not in keep],'reparented_helpers_preserve_world_motion':reparent,'renamed_internal_anchors':rename,'body_clips':len(clips),'head_clips':len(headclips),'attachments':attachments,'visible_geometry_changed':False,'existing_weighted_bind_transforms_changed':False,'runtime_verified':False}

def attach_block(attachments):
 return block('attach','what = head\nwhere = torso\n'+'\n'.join('joint_attachment = { parent_joint = "'+p+'" child_joint = "'+c+'" }' for p,c in attachments))

def rewrite_types(text,attachments):
 output=[]
 for group in entries(text):
  if not group['block']:output.append(group['raw']);continue
  fields_=[e['raw'] for e in entries(group['inner']) if e['key']!='attach'];output.append(block(group['key'],'\n'.join(fields_)+'\n'+attach_block(attachments)))
 return '\n'.join(output)
