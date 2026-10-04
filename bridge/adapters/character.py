"""Prepared character export; Unity/VRC assembly inventory is optional."""
import json
from pathlib import Path
class CharacterAdapter:
 native_human_actions=True
 def audit(self,profile,report,rig):
  from bridge.stance import policy_values
  try:report['stance_policy']=policy_values(profile.get('stance'))
  except ValueError as exc:report['errors'].append('STANCE_POLICY: '+str(exc))
  report['warnings'].append('人物人工确认：完整部件、骨骼映射、表情、透明材质与衣服穿模。非 Unity 来源无需进入 Unity。')
  report['manual_review']=['源模型最终启用部件','服装遮盖与身体裁切','左右方向与负缩放','Shape Keys / 表情','自定义骨骼与物理链','透明/发丝/眼睛材质']
  if profile.get('unity_inventory'):
   inv=json.loads(Path(profile['unity_inventory']).read_text(encoding='utf-8-sig'));report['unity_inventory']={'scene':inv.get('sourceScene'),'parts':len(inv.get('parts',[])),'bones':len(inv.get('bones',[])),'paths':[a.get('path') for a in inv.get('parts',[])]}
 def normalize_bind(self,worlds):return worlds
