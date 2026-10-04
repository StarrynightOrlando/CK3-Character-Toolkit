from pathlib import Path
import json,html,datetime,re

CASES=[
 ('S13','交付状态','区分仅构建、安装后读回一致、游戏已重启加载、用户视觉验收。用 verify-install 核对实际注册入口；不要把候选目录中的修正当成游戏已经更新。'),
 ('S14','具体动作定位','记录理发器动作名称/事件、人物类型及状态；用 trace-state 或姿势到动画文件.json 检查所有同名状态和随机变体。不能仅凭截图猜当前动画是普通待机。'),
 ('S12','站姿与足部接触','查看 stance_report.json 的已改／跳过动作。比较全周期首／中／末帧及最宽帧：双脚间距、脚底高度、膝盖弯曲方向、袜子和鞋帮互穿、裙摆与大腿碰撞。测试动作切换时是否滑步或跳变；坐姿、跪拜、骑马、持武器和跨步分别复查。收窄站姿不等于布料碰撞已解决。'),
 ('S01','源文件','确认使用的是目标穿搭；比较原工程与导出部件清单，检查左右镜像、隐藏身体及空材质槽。'),
 ('S02','身体裁切','检查遮罩依据与可回退副本；从正面、侧面、背面及坐姿低角度检查，不能只按空间范围盲删身体三角面。'),
 ('S03','裙摆蒙皮','检查裙片的主控骨骼与权重；抬腿、分腿、弯腰时确认裙摆没有完全跟随髋部硬折或被大腿拉穿。'),
 ('S04','坐姿形变','检查三个御座坐姿及站坐过渡的首／中／末帧，观察膝部、座面、扶手、长发与袖口。'),
 ('S05','道具','分别检查单手剑、双手剑、权杖、书本、杯子、弓与马；既看节点存在，也看位置、旋转和道具是否实际出现。'),
 ('S06','着色器','核对实际 PS_attachment、私有 Effect 及选择/阴影变体；用原版人物对照确认没有同名声明或视觉回归。'),
 ('S07','原版回归','先原版→自定义→原版，再反向切换；检查原版男女和儿童的头像、半身镜头及灯光，重点观察是否看向脚部。'),
 ('S08','多模型共存','与第二个自定义人物共同启用，分别先打开两者，再切回原版；不要将文件无冲突等同于游戏镜头无冲突。'),
 ('S09','日志与版本','完整重启后确认日志时间、当前版本及生效目录；检查 Unknown object key、invalid node、missing animation、同名 Effect。'),
 ('S10','安装路径','核对描述文件路径、path=、链接路径与最终物理目录；游戏日志不得出现 Folder not found for DLC/Mod。'),
 ('S11','特殊动作伸缩','检查站立祈祷、闭眼祈祷、划十字、跪拜和体型变体动作，观察颈部、头部及躯干是否被拉长或压缩；查看 motion_guard.json。')]
def emit_checklist(directory,identity,automated=None):
 out=Path(directory);out.mkdir(parents=True,exist_ok=True)
 rows=[{'id':i,'group':g,'check':t,'status':'未测','evidence':''} for i,g,t in CASES]
 for sex in ('男','女'):
  for age in (5,12,17,18,40,70):
   rows.append({'id':f'C-{sex}-{age}','group':'性别／年龄镜头','check':f'{sex}，{age} 岁：分别检查人物头像、半身面板、理发器和宫廷；记录面部中心、裁切、朝向和缩放。与同年龄原版角色对照。','status':'未测','evidence':''})
 report={'schema_version':1,'identity':identity,'game_visual_verified':False,'automatic_report':automated,'checks':rows}
 (out/'人工验收检查表.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 text='人物模型人工验收检查表\n\n结构检查通过不代表以下项目通过。每项填写：未测／通过／失败／不适用，并附截图、日志或说明。\n\n'+'\n\n'.join(f"[未测] {r['id']} {r['group']}\n{r['check']}\n证据／备注：" for r in rows)
 (out/'人工验收检查表.txt').write_text(text,encoding='utf-8')
 body=''.join('<tr><td>'+html.escape(r['id'])+'</td><td>'+html.escape(r['group'])+'</td><td>'+html.escape(r['check'])+'</td><td><select><option>未测</option><option>通过</option><option>失败</option><option>不适用</option></select></td><td><textarea aria-label="证据备注"></textarea></td></tr>' for r in rows)
 page='''<!doctype html><meta charset="utf-8"><title>人物模型验收检查表</title><style>body{font:15px/1.6 system-ui;margin:30px;color:#233041}table{border-collapse:collapse;width:100%}td,th{padding:12px;border:1px solid #bbb;vertical-align:top}th{background:#e5edf5}select,textarea,button{font:inherit}textarea{width:230px;min-height:75px}button{padding:8px 16px}p{max-width:1000px}</style><h1>人物模型验收检查表</h1><p>结构检查与游戏验收分开记录。不要自动将“文件存在”勾为“通过”。填写后点击导出保存；页面不上传数据。</p><button id="export">导出验收记录 JSON</button><table><thead><tr><th>编号</th><th>类别</th><th>检查内容</th><th>结果</th><th>证据／备注</th></tr></thead><tbody>'''+body+'''</tbody></table><script>document.getElementById('export').onclick=()=>{let rows=[...document.querySelectorAll('tbody tr')].map(r=>({id:r.cells[0].textContent,group:r.cells[1].textContent,check:r.cells[2].textContent,status:r.querySelector('select').value,evidence:r.querySelector('textarea').value}));let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({checks:rows},null,2)],{type:'application/json'}));a.download='人物模型验收记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};</script>'''
 (out/'人工验收检查表.html').write_text(page,encoding='utf-8')
 return report

def emit_paths(directory,bundle_id,mod_root,records=None,state='inspected_or_planned'):
 out=Path(directory);out.mkdir(parents=True,exist_ok=True);mod_root=Path(mod_root).resolve()
 if records is None:records=[{'kind':kind,'target':str(mod_root/key),'descriptor':str(mod_root/(key+'.mod'))} for kind,key in [('runtime','ck3char_runtime'),('models','ck3char_'+bundle_id)]]
 rows=[]
 for r in records:
  target=Path(r['target']);descriptor=Path(r['descriptor']);declared=None
  if descriptor.is_file():
   found=re.search(r'(?m)^\s*path\s*=\s*"([^"]+)"',descriptor.read_text(encoding='utf-8-sig',errors='replace'));declared=found[1] if found else None
  rows.append({'role':r['kind'],'launcher_descriptor':str(descriptor),'declared_path':declared,'planned_relative_path':'mod/'+target.name,'registered_directory':str(target),'physical_directory':str(target.resolve()),'directory_exists':target.is_dir(),'descriptor_exists':descriptor.is_file()})
 report={'bundle_directory':str(out.resolve()),'installation_state':state,'entries':rows,'error_log':str(mod_root.parent/'logs/error.log'),'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'note':'路径说明只记录磁盘与注册位置，不能证明游戏已加载。'}
 (out/'测试模组位置.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 text='测试模组位置说明\n\n状态：'+{'installed':'已安装','rolled_back':'已回退','inspected_or_planned':'当前检查或构建计划'}.get(state,state)+'\n生成位置：'+report['bundle_directory']+'\n\n'
 for r in rows:text+=f"{r['role']}\n启动器描述文件：{r['launcher_descriptor']}\n实际 path=：{r['declared_path'] or '尚未写入；计划 '+r['planned_relative_path']}\n注册／兼容路径：{r['registered_directory']}\n最终物理目录：{r['physical_directory']}\n目录存在：{r['directory_exists']}；描述文件存在：{r['descriptor_exists']}\n\n"
 text+='游戏错误日志：'+report['error_log']+'\n\n只退出到主菜单不会重新加载模型。完整重启后核对播放集和日志时间。\n如出现 Folder not found for DLC/Mod，先检查描述文件 path= 与上方注册路径，不要反复重做模型。\n本文件不修改播放集，也不自动启动游戏。\n'
 (out/'测试模组位置.txt').write_text(text,encoding='utf-8');return report
