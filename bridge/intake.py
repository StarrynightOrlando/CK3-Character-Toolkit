from pathlib import Path
import datetime,uuid,subprocess
from . import core
from .product import ADAPTER
def inspect_source(source,log=print):
 src=Path(source).expanduser().resolve()
 if not src.is_file():raise core.BridgeError('源模型文件不存在：'+str(src))
 if src.suffix.lower() not in ('.blend','.fbx','.gltf','.glb','.obj','.vrm','.unitypackage'):
  raise core.BridgeError('尚未实现此格式导入；支持 Blender、FBX、glTF/GLB、OBJ、VRM 和 UnityPackage 清单检查。')
 out=core.ROOT/'builds'/('intake_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 job={'action':'inspect','status':'running','profile':{'id':'source_intake','adapter':ADAPTER,'display_name':src.name,'prepared_blend':str(src)},'runtime_tested':False}
 core.save(out/'job.json',job);core.save(out/'request.local.json',{'source':str(src),'output':str(out)})
 log('导入检查：'+str(src))
 cmd=[core.settings()['blender'],'--background','--disable-autoexec','--python-exit-code','7','--python',str(core.ROOT/'bridge/intake_worker.py'),'--',str(out/'request.local.json')]
 try:
  with (out/'worker.log').open('w',encoding='utf-8') as f:code=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).returncode
  if code:raise core.BridgeError('源模型导入未通过；查看 '+str(out/'intake.json'))
  job['status']='complete';log('检查完成（尚未完成 CK3 适配）：'+str(out));return out
 except Exception as exc:job['status']='failed';job['error']=str(exc);raise
 finally:core.save(out/'job.json',job)
