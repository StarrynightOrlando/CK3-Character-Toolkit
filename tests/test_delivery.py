import tempfile,unittest,xml.etree.ElementTree as X
from pathlib import Path
from bridge.animation_audit import clip_errors
from bridge.action_trace import trace

class DeliveryTests(unittest.TestCase):
 def clip(self):
  tree=X.Element('File');info=X.SubElement(tree,'info',{'j':[1],'sa':[2]});X.SubElement(info,'root',{'sa':['t'],'t':[0,0,0],'q':[0,0,0,1],'s':[1]});X.SubElement(tree,'samples',{'t':[0,0,0,1,0,0]});return tree
 def test_valid_and_truncated_tracks(self):
  t=self.clip();self.assertEqual(clip_errors(t,['root']),[]);t.find('samples').set('t',[1]);self.assertIn('t sample length mismatch',clip_errors(t,['root']))
 def test_order_initial_and_empty_tracks(self):
  t=self.clip();t.find('info')[0].set('q',[float('nan'),0,0,1]);t.find('samples').set('q',[])
  errors=clip_errors(t,['other']);self.assertIn('bone name/order mismatch',errors);self.assertIn('root nonfinite q initial',errors);self.assertIn('q empty sample attribute',errors)
 def test_pose_trace_preserves_alternative_states(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'one.anim').write_bytes(b'clip1');(root/'two.anim').write_bytes(b'clip2')
   (root/'test.asset').write_text('pdxmesh={name="body" animation={id="pose1" type="one.anim"} animation={id="pose2" type="two.anim"}} entity={name="actor" pdxmesh="body" state={name="arms_crossed" animation="pose1" chance=10} state={name="arms_crossed" animation="pose2" chance=5}}')
   result=trace(root,'arms_crossed');self.assertEqual(len(result['matches']),2);self.assertTrue(all(r['sha256'] for r in result['matches']));self.assertFalse(result['game_visual_verified']);self.assertFalse(trace(root,'missing')['query_matched'])
