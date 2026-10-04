# 支持类型、阶段与限制

以 `bridge/intake.py`、`bridge/intake_worker.py`、`bridge/blender_worker.py` 的实际实现为准。后缀会转为小写。inspect 只接受存在的单个源文件；依赖的外部纹理、glTF `.bin` 和贴图须可访问。

## 文件格式矩阵

| 类型 | 导入方式 | 会报告什么 | 不会自动完成什么 |
| --- | --- | --- | --- |
| `.blend` | Blender 打开工程，禁止自动执行脚本 | 网格/骨架、材质名称、UV、Shape Keys、负变换 | 服装选择、骨架统一、CK3 材质与动作适配 |
| `.fbx` | Blender FBX importer，尝试导入源动画 | 同上 | Unity Prefab 覆盖、组件、材质插件、FX 控制器还原；源动画到 CK3 的自动转换 |
| `.gltf` / `.glb` | Blender glTF importer | 同上；外部资源仍须完整 | PBR 材质和动画自动转换为 CK3 契约 |
| `.vrm` | 要求文件头为 `glTF`，按 glTF 几何导入 | 网格/骨架及几何检查警告 | VRM 专有表情、春骨、物理、MToon、完整元数据语义与使用限制自动处理 |
| `.obj` | Blender OBJ importer | 静态网格、材质名称、UV | 人体骨架与蒙皮；OBJ 报告可能无骨架，不能直接做有动作的人物 |
| `.unitypackage` | 读取压缩包中受大小限制的 `pathname` 记录 | 资源路径/后缀清单，`imported=false` | 解包资产、运行 Unity、执行 Editor 脚本、实例化 Avatar、解析最终穿搭 |

inspect 成功时保存独立的 `imported.blend`，不覆盖源文件，核对源哈希，并保留 `ck3_ready=false`。对 UnityPackage 不生成导入后的 Avatar 工程。

## VRC 支持到底意味着什么

可以处理作者有权使用的 VRC 模型导出的 FBX、Blender 或 glTF 几何，读取 UnityPackage 资源清单，并在准备后导出 CK3 人物。VRC 不是单一文件格式。本工具没有直接读取 `.unity`、`.prefab`、`.asset`、`.mat` 的 Avatar 装配转换器；Unity 清单 JSON 是作者自行提供的辅助审计输入，不是完整场景解析器。

不转换 VRChat SDK、PhysBone、Contact、Constraint、Expression Menu/Parameters、Animator/FX、着装开关、lilToon/Poiyomi、自动眨眼/口型或 VRM 表情。Shape Keys 被列出不等于已变成 CK3 表情。物理链与骨骼须先保留审阅；删掉它们可能影响蒙皮与头发/裙摆。

若 Avatar 依赖 Unity 装配，作者先在 Unity 中确认最终启用的部件、实际形态与材质，再准备可检查的几何和贴图。单独的 FBX 可能缺少装配结果、衣服开关和身体裁切信息。

## 完整输出支持

完整 `audit/build` 只支持 `adapter="character"`，输入是 `prepared-reference-v1`：一个最终骨架的 `.blend` + 与其部件、骨骼、纹理和已转换动作一致的参考 Mod。不提供参考私人模型；不是导入任意 FBX 后立刻一键 build。详见 [准备契约](PREPARED_REFERENCE.md)。

输出是 CK3 portrait 人物模型包、公共 Runtime 和统一动作选择器组合。公共 Runtime 暴露 matte/cutout/face/face_cutout 四类人物效果及 selection/Shadow 变体。当前没有机甲、通用静态地图资产或其他游戏的输出适配器。

## 明确未支持

PMX/PMD、VRC 下载缓存 `.vrca`、Unity AssetBundle、压缩的完整 Unity 工程、自动表情映射、任意骨架自动重定向、物理布料、所有服装碰撞、任意独立人物包直接混装、全部游戏动作适配均未实现。源模型包含这些功能不会使本工具自动支持它们。

Blender 版本/API、缺失外部贴图、复杂 FBX 和真实 VRM 扩展可能影响导入。合成夹具的 `.vrm` 实际是 GLB 容器样本，只证明几何容器路径可读，不能宣布全部 VRM 0.x/1.0 特性已验证。CK3 更新后需重新生成并验收；自动写 supported_version 只是版本检测，不是兼容认证。
