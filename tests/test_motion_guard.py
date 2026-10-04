import unittest,copy,xml.etree.ElementTree as X,math
from bridge.motion_guard import preserve_length,correct_clip,origin_from_inverse
class MotionGuardTests(unittest.TestCase):
 def test_preserves_direction_and_target_length(self):
  fixed,changed=preserve_length([3,24,4],[0,16,0]);self.assertTrue(changed);self.assertAlmostEqual(sum(x*x for x in fixed),256);self.assertAlmostEqual(fixed[0]/3,fixed[1]/24)
 def test_leaves_normal_motion_untouched(self):
  v=[1,16,0];self.assertEqual(preserve_length(v,[0,16,0]),(v,False))
 def test_changes_only_neck_translation(self):
  r=X.Element('File');info=X.SubElement(r,'info',{'sa':[2]});X.SubElement(info,'body_root',{'sa':['t'],'t':[0,80,0],'q':[0,0,0,1],'s':[1]});X.SubElement(info,'bn_sp_cervical',{'sa':['t'],'t':[0,22,0],'q':[0,0,0,1],'s':[1]});data=X.SubElement(r,'samples',{'t':[0,80,0,0,22,0,3,81,0,0,23,0]});original=copy.deepcopy(r)
  result=correct_clip(r,{'bn_sp_cervical':[0,16,0]},write=True);self.assertTrue(result);self.assertEqual(data.get('t'),[0,80,0,0,16,0,3,81,0,0,16,0]);self.assertEqual(info[0].attrib,original.find('info')[0].attrib);self.assertEqual(info[1].get('q'),[0,0,0,1]);self.assertNotIn('q',data.attrib)
 def test_inverse_bind_origin(self):
  self.assertEqual(origin_from_inverse([1,0,0,0,1,0,0,0,1,0,-16,0]),(0,16,0))
if __name__=='__main__':unittest.main()
