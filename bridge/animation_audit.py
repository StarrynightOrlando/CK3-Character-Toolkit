"""Validate actual decoded tracks without requiring Blender."""
import math

def clip_errors(tree,names):
 errors=[];info=tree.find('info');samples=tree.find('samples')
 if info is None or samples is None:return ['missing info or samples']
 if [b.tag for b in info]!=names:errors.append('bone name/order mismatch')
 if info.get('j')!=[len(names)]:errors.append('joint count mismatch')
 count=info.get('sa',[0])[0]
 if not isinstance(count,int) or count<1:return errors+['invalid sample count']
 for key,width in [('t',3),('q',4),('s',1)]:
  vals=samples.get(key,[]);active=sum(key in b.get('sa',[''])[0] for b in info);expected=count*active*width
  if len(vals)!=expected and not (key=='s' and len(vals)==count*active*3):errors.append(key+' sample length mismatch')
  if key in samples.attrib and not vals:errors.append(key+' empty sample attribute')
  if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals):errors.append(key+' nonfinite sample')
  for b in info:
   initial=b.get(key,[])
   if len(initial) not in ((1,3) if key=='s' else (width,)):errors.append(b.tag+' invalid '+key+' initial width')
   if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in initial):errors.append(b.tag+' nonfinite '+key+' initial')
 return errors
