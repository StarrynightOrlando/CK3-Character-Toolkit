"""Run with Blender --background --python (stdlib suite skips outside Blender)."""
import unittest,sys,copy,xml.etree.ElementTree as X
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
 from mathutils import Matrix,Vector
 from bridge.stance import narrow_clip,Clip,policy_values,CHAINS,JOINTS
 HAS_MATH=True
except ImportError:HAS_MATH=False

@unittest.skipUnless(HAS_MATH,'Requires Blender mathutils')
class StanceTests(unittest.TestCase):
 def fixture(self):
  names=['root','bn_l_hip','bn_l_knee','bn_l_ankle','bn_r_hip','bn_r_knee','bn_r_ankle','bn_r_prop']
  parents=[-1,0,1,2,0,4,5,0];positions=[[0,0,0],[1,10,0],[1,-4,-1],[0,-4,1],[-1,10,0],[-1,-4,-1],[0,-4,1],[1,8,2]]
  sk=X.Element('skeleton');tree=X.Element('File');info=X.SubElement(tree,'info',{'sa':[3],'j':[8],'fps':[30]});X.SubElement(tree,'samples')
  for i,(name,t,parent) in enumerate(zip(names,positions,parents)):
   X.SubElement(sk,name,{'pa':[parent]} if parent>=0 else {})
   X.SubElement(info,name,{'sa':[''],'t':t,'q':[0,0,0,1],'s':[1]})
  return tree,sk
 def test_contacts_lengths_and_unrelated_tracks(self):
  tree,sk=self.fixture();original=copy.deepcopy(tree);new,r=narrow_clip(tree,sk,{'enabled':True});self.assertEqual(r['status'],'corrected');self.assertEqual(tree.find('info')[0].attrib,original.find('info')[0].attrib)
  a=Clip(tree,sk);b=Clip(new,sk)
  for f in range(3):
   _,wa=a.pose(f);_,wb=b.pose(f)
   for n in a.names:
    i=a.index[n]
    self.assertEqual(a.value(i,'t',f),b.value(i,'t',f));self.assertEqual(a.value(i,'s',f),b.value(i,'s',f))
    if n not in JOINTS:self.assertEqual(a.value(i,'q',f),b.value(i,'q',f))
   for chain in CHAINS:
    h,k,foot=[a.index[n] for n in chain]
    self.assertAlmostEqual(wa[foot].translation.y,wb[foot].translation.y,places=5)
    self.assertAlmostEqual(wa[foot].translation.z,wb[foot].translation.z,places=5)
    self.assertAlmostEqual(abs(wa[foot].to_quaternion().dot(wb[foot].to_quaternion())),1,places=5)
    for i,j in [(h,k),(k,foot)]:self.assertAlmostEqual((wa[i].translation-wa[j].translation).length,(wb[i].translation-wb[j].translation).length,places=5)
 def test_seated_clip_rejected_atomically(self):
  tree,sk=self.fixture();tree.find('info').find('bn_l_knee').set('t',[4,0,1]);new,r=narrow_clip(tree,sk,{'enabled':True});self.assertIsNone(new);self.assertEqual(r['status'],'skipped')
 def test_zero_strength_no_change(self):
  tree,sk=self.fixture();new,r=narrow_clip(tree,sk,{'enabled':True,'strength':0});self.assertIsNone(new)
 def test_moving_feet_rejected(self):
  tree,sk=self.fixture();tree.find('info')[0].set('sa',['t']);tree.find('samples').set('t',[0,0,0,2,0,0,4,0,0]);new,r=narrow_clip(tree,sk,{'enabled':True});self.assertIsNone(new);self.assertEqual(r['reason'],'moving_feet_requires_contact_solver')
 def test_invalid_policy(self):
  for p in [{'strength':float('nan')},{'strength':2},{'enabled':'yes'},{'min_width_ratio':1.5,'max_width_ratio':1.}]:
   with self.assertRaises(ValueError):policy_values(p)
 def test_explicit_pelvis_drop_preserves_foot_height(self):
  tree,sk=self.fixture();sk[0].tag='body_root';tree.find('info')[0].tag='body_root'
  for n,x in [('bn_l_knee',.1),('bn_r_knee',-.1)]:tree.find('info').find(n).set('t',[x,-4,0])
  for n in ['bn_l_ankle','bn_r_ankle']:tree.find('info').find(n).set('t',[0,-4,0])
  p={'enabled':True,'strength':1.,'max_width_ratio':.45,'min_width_ratio':.35}
  untouched,r=narrow_clip(tree,sk,p);self.assertIsNone(untouched)
  p['max_pelvis_drop_ratio']=.03;new,r=narrow_clip(tree,sk,p);self.assertEqual(r['status'],'corrected');self.assertGreater(r['pelvis_drop'],0)
  a=Clip(tree,sk);b=Clip(new,sk);_,wa=a.pose(0);_,wb=b.pose(0)
  for chain in CHAINS:
   i=a.index[chain[-1]];self.assertAlmostEqual(wa[i].translation.y,wb[i].translation.y,places=5)
  self.assertAlmostEqual(wa[0].translation.y-wb[0].translation.y,r['pelvis_drop'],places=5)

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(StanceTests))
 if not result.wasSuccessful():raise RuntimeError('Stance tests failed')
