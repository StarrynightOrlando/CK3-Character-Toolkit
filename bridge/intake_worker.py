"""Multi-format intake; importing geometry does not imply CK3 readiness."""
import sys,json,hashlib,tarfile,collections
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from bridge.core import load,save,digest
from bridge.product import ADAPTER
request=load(sys.argv[sys.argv.index('--')+1]);src=Path(request['source']).resolve();out=Path(request['output']).resolve();out.mkdir(parents=True,exist_ok=True)
report={'source':str(src),'sha256':digest(src),'format':src.suffix.lower(),'product_adapter':ADAPTER,'imported':False,'ck3_ready':False,'warnings':[],'errors':[],'meshes':[],'armatures':[]}
extension=src.suffix.lower()
try:
 if extension=='.unitypackage':
  paths=[]
  with tarfile.open(src,'r:*') as archive:
   for i,item in enumerate(archive):
    if i>50000:raise ValueError('Archive member limit exceeded')
    if item.isfile() and item.name.endswith('/pathname') and item.size<32768:
     paths.append(archive.extractfile(item).read().decode('utf-8',errors='replace').strip())
  report['asset_paths']=paths;report['asset_extensions']=dict(collections.Counter(Path(p).suffix.lower() for p in paths));report['warnings'].append('UnityPackage 仅检查资产清单；没有解包或执行编辑器脚本。最终穿搭与插件装配需要 Unity 中确认。')
 elif extension=='.blend':
  bpy.ops.wm.open_mainfile(filepath=str(src),load_ui=False,use_scripts=False);report['imported']=True
 else:
  bpy.ops.wm.read_factory_settings(use_empty=True)
  if extension=='.fbx':bpy.ops.import_scene.fbx(filepath=str(src),use_anim=True)
  elif extension in ('.gltf','.glb','.vrm'):
   if extension=='.vrm':
    if src.open('rb').read(4)!=b'glTF':raise ValueError('VRM 文件不是二进制 glTF 容器')
    report['warnings'].append('VRM 按 glTF 几何与骨架导入；表情、春骨和 MToon 信息没有转换为 CK3 功能。')
   bpy.ops.import_scene.gltf(filepath=str(src))
  elif extension=='.obj':bpy.ops.wm.obj_import(filepath=str(src));report['warnings'].append('OBJ 不携带可用人物骨架；需要绑定或选择静态用途。')
  else:raise ValueError('当前未实现此格式；请转为 Blender/FBX/glTF/GLB/OBJ。PMX/PMD 需要另外的格式适配器，不能冒充已支持。')
  report['imported']=True
 if report['imported']:
  for obj in bpy.context.scene.objects:
   if obj.type=='ARMATURE':report['armatures'].append({'name':obj.name,'bones':[b.name for b in obj.data.bones]})
   if obj.type=='MESH':
    report['meshes'].append({'name':obj.name,'vertices':len(obj.data.vertices),'polygons':len(obj.data.polygons),'materials':[m.name if m else None for m in obj.data.materials],'uv_layers':len(obj.data.uv_layers),'shape_keys':[k.name for k in obj.data.shape_keys.key_blocks] if obj.data.shape_keys else [],'negative_transform':obj.matrix_world.determinant()<0,'armature_modifiers':[m.object.name for m in obj.modifiers if m.type=='ARMATURE' and m.object]})
  if not report['meshes']:report['errors'].append('NO_MESH：未发现网格')
  if not report['armatures']:report['warnings'].append('NO_ARMATURE：没有骨架，不能直接套用身体动作。')
  if len(report['armatures'])>1:report['warnings'].append('MULTIPLE_RIGS：需要确认主体骨架和附属骨架，不自动删除。')
  if any(not m['uv_layers'] for m in report['meshes']):report['warnings'].append('MISSING_UV：部分部件没有 UV。')
  report['warnings'].append('下一步：确认完整部件、骨骼映射、尺寸、材质烘焙与动作策略，再建立 CK3 导出配置。')
  bpy.ops.wm.save_as_mainfile(filepath=str(out/'imported.blend'));report['normalized_intermediate']=str(out/'imported.blend')
except Exception as exc:report['errors'].append(str(exc))
assert digest(src)==report['sha256'],'Input unexpectedly modified'
save(out/'intake.json',report);save(out/'audit.json',report)
(out/'AI交接报告.txt').write_text('\n'.join(['多格式源模型检查','文件：'+str(src),'格式：'+extension,'成功导入网格：'+str(report['imported']),'CK3 可用：尚未准备完成']+report['warnings']+report['errors']),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('meshes','armatures','asset_paths')},ensure_ascii=False))
if report['errors']:raise RuntimeError('Intake failed; see intake.json')
