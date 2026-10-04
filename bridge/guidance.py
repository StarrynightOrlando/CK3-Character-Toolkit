GUIDES={
 'stance': '原版动作重定向不会自动满足动漫人物的站姿审美。通过 profile.stance 显式启用站姿收窄；只按动作 ID 白名单处理，并检查整段足部位移和可达性。默认保留所有平移；如显式允许 max_pelvis_drop_ratio，只额外调整 body_root 高度，保留 ground_joint、腿长、脚部高度/朝向和非腿部旋转；头、躯干、道具与相机锚点会继承骨盆下降，须复查构图。未知、坐姿、跪拜、骑乘、跨步及不可达目标必须跳过并记录，不能靠缩短腿骨、横向缩放整个人或删身体解决。查看 docs/站姿适配.txt 与 stance_report.json；离线通过不代表动作切换及衣物碰撞已通过。',
 'character': '通用人物：先识别 Blender、FBX、GLB/glTF、OBJ、VRM 等来源；Unity/VRC 只是其中一种装配来源。确认穿搭、隐藏身体、Shape Keys、合并骨架和左右方向。不要只按物体名称选网格；不要自动丢弃非标准骨骼。Unity 的最终 Avatar 与单独 FBX 不一定相同。当前版本接受经过准备的 Blender 工程，原始 Avatar 的服装装配、骨骼映射和表情转换仍需人工准备。',
 'shader': 'CK3 着色器经验：必须检查实际运行的 PS_attachment；不要只修改同文件中另一个 MainCode。检查 .asset 的 shader_file/effect 与 .mesh 内嵌 shader 名一致。不要把 Unity lilToon/Poiyomi 参数直接当作 CK3 PBR 参数。角色皮肤与发丝可分材质。阴影、透明与选择描边也要检查。',
 'animation': '动画检查必须包括每一段 .anim 与目标 .mesh 的骨骼数量、名称、顺序、父子关系、根节点比例和采样长度。原版 134 骨动画不能因名称大致相同就认定可用于 199 骨模型。空采样数组应省略属性，不要序列化为空数组。未命中动画时可能停在绑定姿势；人物面板空白也要查日志中的缺失动画。',
 'camera': '使用原版头部节点布局与完整原版身体骨架前缀。头部相机/灯光节点只在头部公开，身体中的对应内部锚点使用模型私有名。不得猜测相机脚本支持按人物类型扩展。逐项检查男女、5/12/17/18/40/70 岁及原版→自定义→原版的打开顺序；结构匹配不证明游戏镜头已通过。',
 'checklist': '每次构建生成可阅读的 TXT、可填写导出的 HTML 与 JSON 检查表。身体裁切应有明确遮罩依据；外套、制服的整体骨骼比例不等于裙摆局部质量。道具既检查名字与挂点，也检查游戏中是否出现及握持。检查表默认全部未测，不能由结构校验自动勾选。',
 'paths': '构建、安装与 check 命令生成“测试模组位置.txt/json”，区分构建目录、启动器 .mod、注册/兼容路径与最终物理目录。完整重启后确认日志时间和播放集；Folder not found 应先排查路径，不能当成模型导出失败。',
 'motion_guard': '固定体型角色默认检查颈骨局部长度，超过目标绑定长度 ±15% 时仅修正平移长度，保留方向、旋转、缩放和根位移。motion_guard.json 列出每段改动。不要把弯曲导致的位移方向变化当作拉伸，也不要为了消除警告由 AI 自行关闭保护。',
 'acceptance': '解析成功、哈希一致、Blender 预览、CK3 日志、用户游戏截图是不同证据。构建成功只表示导出与静态检查通过，不能标记游戏验收完成。不要由 AI 擅自启动游戏、覆盖源工程、安装未知前置、发布到创意工坊，或把私人 Avatar 和本机路径纳入公开工具包。',
 'packages': '公共前置仅包含运行时着色器及契约。模型、贴图和动画属于模型包。每包使用独立 char_<id> 前缀；骨骼和局部动画 ID 不必改名。多个包的原版动作选择器必须统一编译，禁止各自覆盖同一个 animations.txt。当前使用组合模组编译器，尚不宣称任意独立配套 Mod 可以直接混装。'
}
def handoff(profile,status,output,issues=()):
 sections=['CK3 Character Toolkit / AI 交接报告',f'适配器：{profile["adapter"]}',f'模型包：{profile["id"]}',f'准备后的输入：{profile.get("prepared_blend", "未设置")}',f'输出：{output}',f'状态：{status}','游戏内验收：尚未验证','问题：'+('; '.join(issues) or '参见 audit.json / validation.json / worker.log')]
 return '\n\n'.join(sections+[GUIDES[profile['adapter']],GUIDES['shader'],GUIDES['animation'],GUIDES['stance'],GUIDES['camera'],GUIDES['packages'],GUIDES['acceptance']])
