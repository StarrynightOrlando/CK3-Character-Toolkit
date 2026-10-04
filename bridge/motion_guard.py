"""Proportion guard for fixed-shape avatars; rotations/root motion stay intact."""
from pathlib import Path
import math,copy,hashlib,logging
def origin_from_inverse(tx):
 a,b,c,d,e,f,g,h,i=tx[0],tx[3],tx[6],tx[1],tx[4],tx[7],tx[2],tx[5],tx[8]
 det=a*(e*i-f*h)-b*(d*i-f*g)+c*(d*h-e*g)
 if abs(det)<1e-10:raise ValueError('Singular inverse bind matrix')
 inv=((e*i-f*h,c*h-b*i,b*f-c*e),(f*g-d*i,a*i-c*g,c*d-a*f),(d*h-e*g,b*g-a*h,a*e-b*d))
 return tuple(-sum(inv[r][j]*tx[9+j] for j in range(3))/det for r in range(3))
def rest_translations(sk):
 rows=[]
 for bone in sk:
  p=origin_from_inverse(bone.get('tx'))
  if bone.get('pa'):
   parent=sk[bone.get('pa')[0]].get('tx');p=tuple(sum(parent[r+3*c]*p[c] for c in range(3))+parent[9+r] for r in range(3))
  rows.append(p)
 return {bone.tag:p for bone,p in zip(sk,rows)}
def preserve_length(value,reference,tolerance=.15):
 length=math.sqrt(sum(x*x for x in value));rest=math.sqrt(sum(x*x for x in reference))
 if rest<1e-6 or (1-tolerance)*rest<=length<=(1+tolerance)*rest:return list(value),False
 if length<1e-6:return list(reference),True
 return [float(v*rest/length) for v in value],True
def correct_clip(tree,rest,nodes=('bn_sp_cervical',),tolerance=.15,write=False):
 info=tree.find('info');samples=tree.find('samples');count=info.get('sa')[0];active=[b.tag for b in info if 't' in b.get('sa',[''])[0]];offsets={n:i for i,n in enumerate(active)};raw=list(samples.get('t',[]));changes=[]
 for bone in info:
  n=bone.tag
  if n not in nodes or n not in rest:continue
  baseline=math.sqrt(sum(v*v for v in rest[n]));lengths=[];changed=0
  initial=list(bone.get('t'));fixed,initial_changed=preserve_length(initial,rest[n],tolerance)
  if write and initial_changed:bone.set('t',fixed)
  if n in offsets:
   for frame in range(count):
    start=(frame*len(active)+offsets[n])*3;v=raw[start:start+3];lengths.append(math.sqrt(sum(x*x for x in v)));new,altered=preserve_length(v,rest[n],tolerance)
    if altered:
     changed+=1
     if write:raw[start:start+3]=new
  else:
   lengths=[math.sqrt(sum(x*x for x in initial))];changed=count if initial_changed else 0
  if initial_changed or changed:changes.append({'joint':n,'rest_length':baseline,'source_min_length':min(lengths),'source_max_length':max(lengths),'frames_corrected':changed,'initial_corrected':initial_changed})
 if write and 't' in samples.attrib:samples.set('t',raw)
 return changes
def process_folder(folder,prefix,policy=None,write=True):
 from io_pdx_mesh import pdx_data
 logging.getLogger('io_pdx.data').setLevel(logging.WARNING)
 from .pds import entries,fields
 folder=Path(folder);policy=policy or {};enabled=policy.get('enabled',True);nodes=tuple(policy.get('joints',['bn_sp_cervical']));tolerance=float(policy.get('tolerance',.15))
 if not 0<tolerance<1:raise ValueError('Motion guard tolerance must be between 0 and 1')
 if set(nodes)&{'ground_joint','body_root','bn_l_prop','bn_r_prop','camera_torso_look_at'}:raise ValueError('Root motion and prop/camera attachments must not be length-clamped')
 mesh=pdx_data.read_meshfile(str(folder/(prefix+'.mesh')));rest=rest_translations(mesh.find('object')[0].find('skeleton'))
 pm=next(e for e in entries((folder/(prefix+'.asset')).read_text(encoding='utf-8-sig')) if e['key']=='pdxmesh');files=sorted({fields(e['inner'])['type'] for e in entries(pm['inner']) if e['key'] in ('animation','additive_animation')});rows=[]
 for rel in files:
  path=folder/rel;tree=pdx_data.read_meshfile(str(path));before=hashlib.sha256(path.read_bytes()).hexdigest();q=copy.deepcopy(tree.find('samples').get('q'));scale=copy.deepcopy(tree.find('samples').get('s'));initial_qs={b.tag:(list(b.get('q')),list(b.get('s'))) for b in tree.find('info')}
  changes=correct_clip(tree,rest,nodes,tolerance,write and enabled)
  if not changes:continue
  if write and enabled:
   assert q==tree.find('samples').get('q') and scale==tree.find('samples').get('s')
   assert all(initial_qs[b.tag]==(b.get('q'),b.get('s')) for b in tree.find('info'))
   pdx_data.write_animfile(str(path),tree)
  rows.append({'file':rel,'sha256_before':before,'sha256_after':hashlib.sha256(path.read_bytes()).hexdigest(),'changes':changes})
 return {'enabled':enabled,'joints':nodes,'tolerance':tolerance,'clips_scanned':len(files),'clips_changed' if write and enabled else 'clips_flagged':len(rows),'rotations_and_scales_preserved':True,'root_motion_preserved':True,'runtime_verified':False,'changes':rows}
