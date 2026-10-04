from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from pathlib import Path
import json,threading,secrets,traceback,os,webbrowser
from . import core
from .guidance import GUIDES
REPORT_FILES=('audit.json','validation.json','camera_contract.json','motion_guard.json','stance_report.json','姿势修正范围.json','姿势到动画文件.json','自动检查报告.json','人工验收检查表.html','人工验收检查表.txt','测试模组位置.txt','测试模组位置.json','AI交接报告.txt','worker.log')
def serve():
 token=secrets.token_urlsafe(32);lock=threading.Lock();status={'busy':False,'messages':[],'last_bundle':None,'last_install':None,'last_error':None}
 if (core.ROOT/'state/ui-state.json').exists():
  old=core.load(core.ROOT/'state/ui-state.json');status.update({k:old[k] for k in ('messages','last_bundle','last_install','last_error') if k in old})
 if status['last_bundle'] and not (Path(status['last_bundle'])/'bundle.json').is_file():status['last_bundle']=None
 if status['last_install'] and not (Path(status['last_install'])/'transaction.json').is_file():status['last_install']=None
 def log(message):
  status['messages'].append(str(message));status['messages']=status['messages'][-100:]
 def profiles():return [core.profile(p.stem) for p in (core.ROOT/'profiles.local').glob('*.json')]
 def jobs(limit=35):
  result=[]
  for path in sorted((core.ROOT/'builds').glob('*/job.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:limit]:
   try:
    data=core.load(path);data['folder']=path.parent.name;data['has_preview']=(path.parent/'source_preview.png').is_file();data['previews']=[f for f in ('source_preview.png','preview_seated_pose.png','preview_sword_pose.png') if (path.parent/f).is_file()];data['has_package']=(path.parent/'package/manifest.json').is_file();data['report_files']=[f for f in REPORT_FILES if (path.parent/f).is_file()];result.append(data)
   except (OSError,ValueError):pass
  return result
 def execute(data):
  try:
   status['last_error']=None;action=data['action'];names=data.get('profiles',[])
   if action=='inspect':
    from .intake import inspect_source
    inspect_source(data.get('source',''),log)
   elif action in ('audit','build'):
    if not names:raise core.BridgeError('请先选择配置')
    if action=='build':status['last_bundle']=None
    for name in names:
     try:core.run(name,action,log)
     except Exception as exc:log('失败：'+str(exc));status['last_error']=str(exc)
   elif action=='compile':
    status['last_bundle']=None
    packages=[]
    for name in names:
     core.profile(name);matches=[j for j in jobs(None) if j['profile']['id']==name and j['action']=='build' and j['status']=='complete' and j['has_package']]
     if not matches:raise core.BridgeError('没有成功构建：'+name)
     packages.append(core.ROOT/'builds'/matches[0]['folder']/'package')
    if not packages:raise core.BridgeError('请先选择模型')
    status['last_bundle']=str(core.compile_bundle(packages,'selected_models',log))
   elif action=='install':
    if not status['last_bundle']:raise core.BridgeError('请先编译组合包')
    mod_root=core.settings().get('mod_root')
    if not mod_root:raise core.BridgeError('settings.local.json 尚未配置 mod_root')
    status['last_install']=str(core.install_bundle(status['last_bundle'],mod_root,core.settings().get('storage_root')));log('已安装并核对实际入口文件。资源在物理目录，游戏 mod 目录保留兼容链接；工具管理的同名候选已切换至本次版本。仍需手动启用播放集并完整重启，游戏效果未验收。')
   elif action=='verify-install':
    if not status['last_install']:raise core.BridgeError('没有本工具安装事务；已启用的外部/手工模组请用 check 检查')
    from .installation import verify
    result=verify(status['last_install']);status['last_verification']=result;log('安装文件核验：'+('一致；游戏加载与效果仍需验证' if result['installed_files_verified'] else '不一致：'+str(result['issues'])))
   elif action=='rollback':
    if not status['last_install']:raise core.BridgeError('本会话没有可回退的安装')
    core.rollback(status['last_install']);status['last_install']=None;log('已回退工具安装')
   elif action=='public-zip':log('公开工具源码包：'+str(core.public_zip()))
   else:raise core.BridgeError('未知操作')
  except Exception as exc:status['last_error']=str(exc);log('失败：'+str(exc))
  finally:
   status['busy']=False;core.save(core.ROOT/'state/ui-state.json',status);lock.release()
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def reply(self,data,kind='application/json; charset=utf-8',code=200):
   content=json.dumps(data,ensure_ascii=False).encode('utf-8') if not isinstance(data,bytes) else data
   self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
  def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
  def do_GET(self):
   if not self.valid_host():return self.reply({'error':'Host rejected'},code=403)
   route=urlparse(self.path)
   try:
    if route.path=='/':return self.reply((core.ROOT/'bridge/ui.html').read_text(encoding='utf-8').replace('__TOKEN__',token).encode('utf-8'),'text/html; charset=utf-8')
    if route.path=='/api/state':
     bundle=Path(status['last_bundle']) if status['last_bundle'] else None
     docs={'folder':bundle.name,'files':[f for f in REPORT_FILES if (bundle/f).is_file()]} if bundle and bundle.is_relative_to(core.ROOT/'builds') else None
     install_status=None
     if status['last_install'] and (Path(status['last_install'])/'transaction.json').is_file():
      tx=core.load(Path(status['last_install'])/'transaction.json');install_status={'transaction_status':tx['status'],'bundle_matches':str(bundle)==tx.get('bundle'),'records':tx['records'],'game_visual_verified':False}
     return self.reply({'status':status,'profiles':profiles(),'jobs':jobs(),'doctor':core.doctor(),'guides':GUIDES,'bundle_docs':docs,'installation':install_status})
    if route.path=='/artifact':
     args=parse_qs(route.query);name=args['job'][0];file=args['file'][0]
     if file not in ('source_preview.png','preview_seated_pose.png','preview_sword_pose.png')+REPORT_FILES:raise ValueError('文件不可通过预览访问')
     path=core.inside(core.ROOT/'builds',core.ROOT/'builds'/name/file)
     return self.reply(path.read_bytes(),'image/png' if file.endswith('.png') else 'text/html; charset=utf-8' if file.endswith('.html') else 'text/plain; charset=utf-8')
    return self.reply({'error':'Not found'},code=404)
   except Exception as exc:return self.reply({'error':str(exc)},code=400)
  def do_POST(self):
   if not self.valid_host() or self.headers.get('X-Bridge-Token')!=token:return self.reply({'error':'Invalid token'},code=403)
   origin=self.headers.get('Origin')
   if origin and origin!=f'http://127.0.0.1:{self.server.server_port}':return self.reply({'error':'Origin rejected'},code=403)
   if self.path!='/api/action':return self.reply({'error':'Not found'},code=404)
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=65536:raise ValueError('请求过大')
    data=json.loads(self.rfile.read(length))
    if not lock.acquire(blocking=False):return self.reply({'error':'队列仍在运行'},code=409)
    status['busy']=True;threading.Thread(target=execute,args=(data,),daemon=True).start();return self.reply({'queued':True})
   except Exception as exc:return self.reply({'error':str(exc)},code=400)
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);url=f'http://127.0.0.1:{server.server_port}/';core.save(core.ROOT/'state/server.local.json',{'url':url,'pid':os.getpid()});print(url,flush=True)
 if os.environ.get('BRIDGE_NO_BROWSER')!='1':webbrowser.open(url)
 server.serve_forever()
