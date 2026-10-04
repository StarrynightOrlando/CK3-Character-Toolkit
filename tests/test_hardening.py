import unittest,tempfile,json
from pathlib import Path
from bridge.runtime import without_effects,effect_names
from bridge.hardening import scalar_refs,repair_accessory_names
from bridge.checklists import emit_checklist,emit_paths
from bridge.versioning import supported_version
from bridge.pds import entries
class HardeningTests(unittest.TestCase):
 def test_utf8_bom_does_not_change_first_block_name(self):
  self.assertEqual(entries('\ufeffpdxmesh = { name = "avatar" }')[0]['key'],'pdxmesh')
 def test_effect_scope_ignores_comment_and_string_braces(self):
  source='''VertexShader = { Code = "keep } here" }
// Effect fake { }
Effect portrait_skin { Defines = { "}" } /* } */ }
Effect portrait_attachment { A = { X = 1 } // }
}
'''
  result=without_effects(source);self.assertEqual(effect_names(result),[]);self.assertIn('keep } here',result)
 def test_quoted_nodes_and_comments(self):
  self.assertEqual(scalar_refs('node="ground_joint" # node=bad\nnode = bn_r_prop','node'),['ground_joint','bn_r_prop'])
 def test_quoted_direct_accessory_is_namespaced(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);a=root/'gfx/portraits/accessories/x.txt';p=root/'gfx/portraits/portrait_modifiers/char_demo_props.txt';a.parent.mkdir(parents=True);p.parent.mkdir(parents=True);a.write_text('char_demo_native_horse = { }');p.write_text('x={ accessory = "horse" } # accessory = horse\ny={ accessory = horse }')
   changes=repair_accessory_names(root,'char_demo');self.assertEqual(len(changes),2);self.assertIn('# accessory = horse',p.read_text(encoding='utf-8-sig'))
 def test_matrix_starts_unverified_for_both_sexes_age_boundary(self):
  with tempfile.TemporaryDirectory() as d:
   report=emit_checklist(d,'sample');self.assertFalse(report['game_visual_verified']);self.assertEqual({r['status'] for r in report['checks']},{'未测'});self.assertTrue(all(any(r['id']==f'C-{s}-{a}' for r in report['checks']) for s in ('男','女') for a in (17,18,70)))
 def test_path_notes_include_descriptors_and_physical_locations(self):
  with tempfile.TemporaryDirectory() as d:
   r=emit_paths(Path(d)/'output','demo',Path(d)/'user/mod');self.assertEqual(len(r['entries']),2);self.assertTrue(all(x['launcher_descriptor'].endswith('.mod') for x in r['entries']));self.assertTrue((Path(d)/'output/测试模组位置.txt').exists())
 def test_version_is_detected_not_hardcoded(self):
  with tempfile.TemporaryDirectory() as d:
   game=Path(d)/'game';p=Path(d)/'launcher/launcher-settings.json';p.parent.mkdir();p.write_text(json.dumps({'rawVersion':'1.20.0.2'}));self.assertEqual(supported_version(game),'1.20.*')
if __name__=='__main__':unittest.main()
