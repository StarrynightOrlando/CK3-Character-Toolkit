from pathlib import Path
import uuid
from . import core
from .hardening import audit
from .checklists import emit_checklist,emit_paths
from .pds import entries
def inspect_package(path):
 path=Path(path).resolve();s=core.settings();mod=path/'models' if (path/'models').is_dir() else path/'mod' if (path/'mod').is_dir() else path;runtime=path/'runtime' if (path/'runtime').is_dir() else None
 report=audit(mod,s['game'],s['pdx_tools'],runtime);out=core.ROOT/'builds'/('inspection_'+uuid.uuid4().hex[:10]);out.mkdir(parents=True)
 core.save(out/'自动检查报告.json',report);emit_checklist(out,path.name,report)
 from .action_trace import state_map
 core.save(out/'姿势到动画文件.json',{'game_visual_verified':False,'states':state_map(mod)})
 records=[];mod_root=Path(s['mod_root'])
 for descriptor in mod_root.glob('*.mod'):
  values={e['key']:e.get('value','').strip('"') for e in entries(descriptor.read_text(encoding='utf-8-sig',errors='replace'))}
  if not values.get('path'):continue
  target=Path(values['path']);target=target if target.is_absolute() else mod_root.parent/target
  for role,expected in [('models',mod),('runtime',runtime)]:
   if expected is not None and target.resolve()==expected.resolve():records.append({'kind':role,'target':str(target),'descriptor':str(descriptor)})
 emit_paths(out,path.name,mod_root,records if records else [],'installed' if records else 'inspected_or_planned');return out,report
