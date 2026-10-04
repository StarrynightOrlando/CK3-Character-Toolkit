"""Opt-in, clip-atomic standing stance IK. Runs inside Blender (mathutils).

Hip/knee/ankle rotations change; an explicit bounded pelvis drop is optional.
Unknown, additive, moving or unsupported
clips are left byte-for-byte intact. This is not cloth collision correction.
"""
import copy, math, hashlib
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

DEFAULT_ACTIONS=('body_idle_1','body_idle_2','body_idle_3',
 'body_council_chancellor','body_council_steward','body_council_spymaster',
 'body_council_bishop','body_praying_standing','body_praying_standing_eyes')
CHAINS=tuple(tuple('bn_'+side+'_'+joint for joint in ('hip','knee','ankle')) for side in ('l','r'))
JOINTS={n for chain in CHAINS for n in chain}

def policy_values(policy):
 p={'enabled':False,'strength':.65,'max_width_ratio':.8,'min_width_ratio':.65,'max_pelvis_drop_ratio':0.,'actions':list(DEFAULT_ACTIONS)}
 if policy:p.update(policy)
 if type(p['enabled']) is not bool:raise ValueError('stance.enabled must be boolean')
 for key,lo,hi in [('strength',0,1),('max_width_ratio',.25,2),('min_width_ratio',.2,1.5),('max_pelvis_drop_ratio',0,.05)]:
  if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or not lo<=p[key]<=hi:raise ValueError('Invalid stance.'+key)
 if p['min_width_ratio']>p['max_width_ratio']:raise ValueError('stance minimum width exceeds maximum')
 if not isinstance(p['actions'],list) or not all(isinstance(a,str) and a.startswith('body_') and a.replace('_','').isalnum() for a in p['actions']):raise ValueError('stance.actions requires explicit body action IDs')
 return p

class Clip:
 def __init__(self,tree,sk):
  self.tree=tree;self.info=tree.find('info');self.samples=tree.find('samples');self.names=[b.tag for b in self.info]
  if self.names!=[b.tag for b in sk]:raise ValueError('Stance skeleton order mismatch')
  self.parents=[b.get('pa',[-1])[0] for b in sk];self.count=self.info.get('sa')[0]
  if self.count<1 or any(parent>=i for i,parent in enumerate(self.parents)):raise ValueError('Invalid stance hierarchy or sample count')
  self.index={n:i for i,n in enumerate(self.names)};self.active={};self.width={'t':3,'q':4,'s':1}
  for k in self.width:
   active=[i for i,b in enumerate(self.info) if k in b.get('sa',[''])[0]];self.active[k]={i:j for j,i in enumerate(active)}
   if k=='s' and active:self.width[k]=len(self.samples.get(k,[]))//(len(active)*self.count)
   if self.width[k] not in ((1,3) if k=='s' else (self.width[k],)):raise ValueError('Invalid scale width')
   if len(self.samples.get(k,[]))!=len(active)*self.count*self.width[k]:raise ValueError('Invalid stance samples')
 def value(self,i,k,f):
  if i not in self.active[k]:return list(self.info[i].get(k))
  start=(f*len(self.active[k])+self.active[k][i])*self.width[k]
  return self.samples.get(k)[start:start+self.width[k]]
 def pose(self,f):
  local=[];world=[]
  for i in range(len(self.names)):
   t=self.value(i,'t',f);q=self.value(i,'q',f);s=self.value(i,'s',f);s=s*3 if len(s)==1 else s
   if not all(math.isfinite(v) for v in t+q+s):raise ValueError('Nonfinite stance transform')
   m=Matrix.LocRotScale(Vector(t),Quaternion((q[3],q[0],q[1],q[2])),Vector(s));local.append(m)
   world.append(world[self.parents[i]]@m if self.parents[i]>=0 else m)
  return local,world
 def set_rotations(self,rotations):
  # Preserve every translation and scale sample, plus all unrelated rotations.
  moving=set(self.active['q']);moving.update(self.index[n] for n in rotations)
  for n,rows in rotations.items():
   b=self.info[self.index[n]];b.set('q',rows[0]);b.set('sa',[''.join(k for k in 'tqs' if k=='q' or k in b.get('sa',[''])[0])])
  self.samples.set('q',[v for f in range(self.count) for i in sorted(moving) for v in (rotations[self.names[i]][f] if self.names[i] in rotations else self.value(i,'q',f))])
 def set_translations(self,translations):
  moving=set(self.active['t']);moving.update(self.index[n] for n in translations)
  for n,rows in translations.items():
   b=self.info[self.index[n]];b.set('t',rows[0]);b.set('sa',[''.join(k for k in 'tqs' if k=='t' or k in b.get('sa',[''])[0])])
  self.samples.set('t',[v for f in range(self.count) for i in sorted(moving) for v in (translations[self.names[i]][f] if self.names[i] in translations else self.value(i,'t',f))])

def knee_target(hip,knee,foot,target):
 a=(knee-hip).length;b=(foot-knee).length;d=(target-hip).length
 if min(a,b,d)<1e-6 or not abs(a-b)+1e-5<d<a+b-1e-5:raise ValueError('Unreachable foot target')
 axis=(target-hip)/d;along=(a*a-b*b+d*d)/(2*d)
 pole=knee-hip;pole-=axis*pole.dot(axis)
 if pole.length<1e-5:
  pole=Vector((0,0,-1));pole-=axis*pole.dot(axis)
 if pole.length<1e-5:raise ValueError('Ambiguous knee bend plane')
 return hip+axis*along+pole.normalized()*math.sqrt(max(0,a*a-along*along))

def narrow_clip(tree,sk,policy):
 p=policy_values(policy);clip=Clip(tree,sk)
 if not JOINTS<=set(clip.names):return None,{'status':'skipped','reason':'missing_leg_joints'}
 for h,k,a in CHAINS:
  if clip.parents[clip.index[k]]!=clip.index[h] or clip.parents[clip.index[a]]!=clip.index[k]:return None,{'status':'skipped','reason':'unsupported_leg_chain'}
 frames=[];widths=[];hipwidths=[];min_leg=float('inf');footpaths=[[],[]]
 for f in range(clip.count):
  local,world=clip.pose(f);pts=[[world[clip.index[n]].translation for n in chain] for chain in CHAINS]
  for side,(h,k,a) in enumerate(pts):
   length=(k-h).length+(a-k).length;min_leg=min(min_leg,length);footpaths[side].append(a.copy())
   if h.y-a.y<.78*length:return None,{'status':'skipped','reason':'non_standing_geometry'}
   for n in CHAINS[side]:
    scale=world[clip.index[n]].to_scale()
    if world[clip.index[n]].determinant()<=0 or min(scale)<=0 or max(scale)-min(scale)>1e-4:return None,{'status':'skipped','reason':'nonuniform_or_mirrored_leg_scale'}
  if abs(pts[0][2].y-pts[1][2].y)>.12*min_leg:return None,{'status':'skipped','reason':'uneven_feet'}
  widths.append(abs(pts[0][2].x-pts[1][2].x));hipwidths.append(abs(pts[0][0].x-pts[1][0].x));frames.append((local,world,pts))
 for path in footpaths:
  if max((v-path[0]).length for v in path)>.12*min_leg:return None,{'status':'skipped','reason':'moving_feet_requires_contact_solver'}
 if min(hipwidths)<.05*min_leg:return None,{'status':'skipped','reason':'sideways_or_crossed_pose'}
 # A constant reduction per clip preserves the foot motion trajectory without
 # introducing a threshold discontinuity at any sample.
 available=min(w-h*p['min_width_ratio'] for w,h in zip(widths,hipwidths))
 excess=min(w-h*p['max_width_ratio'] for w,h in zip(widths,hipwidths))
 reduction=min(max(0,excess)*p['strength'],max(0,available))
 if reduction<.001*min_leg:return None,{'status':'unchanged','reason':'already_within_stance_limit','width_before_mean':sum(widths)/len(widths),'hip_width_mean':sum(hipwidths)/len(hipwidths)}
 # Near-straight legs may need a small constant pelvis drop to reach a close
 # stance without stretching. This is explicit, bounded and never moves ground.
 drop=0.
 for local,world,pts in frames:
  for side,(h,k,a) in enumerate(pts):
   tx=a.x+(-1 if a.x>pts[1-side][2].x else 1)*reduction/2
   reach=(h-k).length+(k-a).length-1e-3
   horizontal=(tx-h.x)**2+(a.z-h.z)**2
   if horizontal>=reach*reach:return None,{'status':'skipped','reason':'unreachable_horizontal_target'}
   drop=max(drop,h.y-a.y-math.sqrt(reach*reach-horizontal))
 if drop>p['max_pelvis_drop_ratio']*min_leg:return None,{'status':'skipped','reason':'pelvis_drop_exceeds_limit','required_pelvis_drop':drop}
 pelvis=clip.index.get('body_root')
 if drop and pelvis is None:return None,{'status':'skipped','reason':'pelvis_node_missing'}
 if drop:
  for chain in CHAINS:
   i=clip.index[chain[0]]
   while i>=0 and i!=pelvis:i=clip.parents[i]
   if i<0:return None,{'status':'skipped','reason':'leg_outside_pelvis_hierarchy'}
 translations={'body_root':[]} if drop else {}
 rotations={n:[] for n in JOINTS};maxerror=0.;before=[];after=[]
 try:
  for f,(local,world,pts) in enumerate(frames):
   original_pts=pts
   if drop:
    local=[m.copy() for m in local];parent=clip.parents[pelvis]
    local[pelvis].translation+=(world[parent].to_3x3().inverted()@Vector((0,-drop,0))) if parent>=0 else Vector((0,-drop,0))
    translations['body_root'].append(list(local[pelvis].translation));world=[]
    for i,m in enumerate(local):world.append(world[clip.parents[i]]@m if clip.parents[i]>=0 else m)
    pts=[[world[clip.index[n]].translation for n in chain] for chain in CHAINS]
   newfeet=[]
   for side,chain in enumerate(CHAINS):
    h,k,a=pts[side];indices=[clip.index[n] for n in chain];ih,ik,ia=indices
    target=original_pts[side][2].copy();target.x+=(-1 if target.x>original_pts[1-side][2].x else 1)*reduction/2
    kn=knee_target(h,k,a,target)
    qhip=(k-h).rotation_difference(kn-h)@world[ih].to_quaternion()
    qknee=(a-k).rotation_difference(target-kn)@world[ik].to_quaternion()
    desired=[qhip,qknee,world[ia].to_quaternion()];newworld={}
    for idx,q in zip(indices,desired):
     parent=clip.parents[idx];parentworld=newworld.get(parent,world[parent]) if parent>=0 else Matrix.Identity(4)
     qlocal=(parentworld.to_quaternion().inverted()@q).normalized();name=clip.names[idx]
     if rotations[name]:
      prev=rotations[name][-1]
      if qlocal.dot(Quaternion((prev[3],prev[0],prev[1],prev[2])))<0:qlocal.negate()
     rotations[name].append([qlocal.x,qlocal.y,qlocal.z,qlocal.w])
     t,_,s=local[idx].decompose();newworld[idx]=parentworld@Matrix.LocRotScale(t,qlocal,s)
    error=(newworld[ia].translation-target).length;maxerror=max(maxerror,error)
    if error>1e-4*min_leg:raise ValueError('IK contact verification failed')
    newfeet.append(newworld[ia].translation)
   before.append(widths[f]);after.append(abs(newfeet[0].x-newfeet[1].x))
 except ValueError as exc:return None,{'status':'skipped','reason':str(exc)}
 output=copy.deepcopy(tree);outclip=Clip(output,sk);outclip.set_rotations(rotations)
 if translations:outclip.set_translations(translations)
 return output,{'status':'corrected','frames':clip.count,'width_before_mean':sum(before)/len(before),'width_after_mean':sum(after)/len(after),'width_reduction':reduction,'pelvis_drop':drop,'pelvis_drop_leg_ratio':drop/min_leg,'max_foot_position_error':maxerror,'changed_joints':sorted(JOINTS),'translation_joints':list(translations)}

def process_folder(folder,prefix,policy=None):
 p=policy_values(policy);report={'enabled':p['enabled'],'policy':p,'runtime_verified':False,'changes':[],'limits':['Standing clips only; no cloth collision solver.','Review transitions and full animation cycles in game.']}
 if not p['enabled']:return report
 from io_pdx_mesh import pdx_data
 from .pds import entries,fields
 folder=Path(folder);sk=pdx_data.read_meshfile(str(folder/(prefix+'.mesh'))).find('object')[0].find('skeleton')
 asset=next(e for e in entries((folder/(prefix+'.asset')).read_text(encoding='utf-8-sig')) if e['key']=='pdxmesh');references={}
 for e in entries(asset['inner']):
  if e['key'] in ('animation','additive_animation'):
   f=fields(e['inner']);references.setdefault(f['type'],[]).append((e['key'],f['id']))
 for rel,uses in references.items():
  selected=[name for kind,name in uses if name in p['actions']]
  if not selected:continue
  row={'file':rel,'actions':selected}
  if any(kind!='animation' or name not in p['actions'] for kind,name in uses):row.update(status='skipped',reason='shared_with_unselected_or_additive_action');report['changes'].append(row);continue
  path=(folder/rel).resolve()
  if not path.is_relative_to(folder.resolve()):raise ValueError('Stance path escape')
  before=hashlib.sha256(path.read_bytes()).hexdigest();tree=pdx_data.read_meshfile(str(path));output,metrics=narrow_clip(tree,sk,p)
  if output is not None:pdx_data.write_animfile(str(path),output)
  row.update(metrics,sha256_before=before,sha256_after=hashlib.sha256(path.read_bytes()).hexdigest());report['changes'].append(row)
 report['missing_actions']=sorted(set(p['actions'])-{name for uses in references.values() for _,name in uses})
 report['clips_changed']=sum(r['status']=='corrected' for r in report['changes'])
 return report
