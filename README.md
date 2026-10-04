# CK3 Character Toolkit — 3D 人物前置与 VRC 导入经验

面向 CK3 模组作者与 AI 助手的 **3D 人物制作基础库、公共材质前置生成器和作者指南**。源码来自 0.5.0 收尾候选；本公开整理版称为 `0.5.0-public.1`，工具内部版本与 Runtime API 保持 0.5.0 / 1。

核心经验包括：还原 Unity/VRC 的最终穿搭；准备几何、骨架和贴图；建立 CK3 头身与相机挂点；逐段核对动作；选择适合二次元人物的哑光/脸部材质；组合、安装与核验模组。这里的“前置”是 CK3 Character Runtime，工具代码和作者说明则在本仓库。

**当前可做：多格式源文件导入检查 + 已准备人物工程的 CK3 导出与组合。完整的原始 VRC Avatar 一键转换尚未实现。** 本仓库没有私人角色或可直接使用的准备参考包，首次作者必须按 [准备契约](docs/PREPARED_REFERENCE.md) 自行建立合法来源的参考输入。

## 阅读入口

- [支持类型与能力矩阵](docs/SUPPORTED_TYPES.md)：明确扩展名、完成阶段和不支持的内容。
- [作者指南：3D 前置与 VRC 迁移](docs/AUTHOR_GUIDE.md)：从最终 Avatar 装配到 CK3 的具体步骤。
- [材质与着色器经验](docs/SHADER_GUIDE.md)：四种 Effect、透明、双面、选择与阴影分支。
- [准备参考契约](docs/PREPARED_REFERENCE.md)：完整导出的实际输入要求。
- [人工验收检查表](docs/ACCEPTANCE_CHECKLIST.md)：几何、材质、男女/年龄、动作、安装证据。
- [AI 协作与交接](docs/AI_HANDOFF.md)：可直接交给 AI 的说明；这是文档，不是训练出的模型能力，不要求安装任何 skill。
- [发布、来源与检查记录](docs/PUBLIC_RELEASE.md)、[第三方说明](THIRD_PARTY_NOTICES.md)、[许可状态](LICENSE.md)。

## 支持类型速览

| 输入 | 已实现阶段 | CK3 输出边界 |
| --- | --- | --- |
| `.blend` | 读取 Blender 网格、骨架、材质槽、Shape Keys | 完整导出须为经过准备的工程，搭配参考 Mod |
| `.fbx` | 通过 Blender 导入检查 | 衣装、骨架、贴图与参考契约仍需准备 |
| `.glb` / `.gltf` | glTF 几何、骨架导入检查 | glTF 材质/动画不直接变成 CK3 材质/动作 |
| `.vrm` | 二进制 glTF 容器的几何、骨架导入检查 | 不转换 VRM 表情、MToon、春骨；真实模型仍需逐个验证 |
| `.obj` | 静态几何导入检查 | 没有可用人物骨架，不能直接套身体动作 |
| `.unitypackage` | 读取资源路径清单 | 不实例化 Avatar，不执行 Unity 脚本，不自动转换 |
| Unity 场景/Prefab/VRC 工程 | 作者在 Unity 确认最终装配后提供上述输入 | 不是本工具的直接导入类型 |
| `.pmx` / `.pmd`、`.vrca`、AssetBundle | 未实现 | 需另行提供格式适配或合法转换输入 |

这里的“支持”描述代码实现的阶段，不代表每个商业 Avatar、每个 Blender 版本或所有 CK3 动作均已游戏验收。详细条件与验证范围见 [支持矩阵](docs/SUPPORTED_TYPES.md)。

## 快速使用

作者端：Windows、Python 3.12+、Blender、作者另行安装的 io_pdx_mesh，以及本机 CK3。Python 控制层使用标准库；Blender worker 需要 `bpy` / `mathutils`，完整导出另需 io_pdx_mesh。依赖版本说明见第三方文档。

```powershell
Copy-Item examples/settings.example.json settings.local.json
New-Item -ItemType Directory profiles.local -Force
Copy-Item examples/profile.example.json profiles.local/my_avatar.json
# 编辑这两份本地文件，填写自己的路径与准备输入，再执行：
python bridge_cli.py doctor
python bridge_cli.py inspect 'C:/MyAssets/source.fbx'
python bridge_cli.py audit my_avatar
python bridge_cli.py build my_avatar
python bridge_cli.py compile my_collection 'builds/<本次成功构建>/package'
```

也可双击 `启动工具.cmd` 使用本地工作台。`inspect` 输出 `intake.json` 和候选 `imported.blend`；它总是明确保留 `ck3_ready=false`。`audit` / `build` 使用配置中的 **prepared_blend + reference_mod**，不会自动使用上一次导入结果。

编译生成 `runtime/` 与 `models/`。新候选安装会创建归属受控的兼容入口与 `.mod`，并保留旧物理版本用于回退：

```powershell
python bridge_cli.py check 'builds/<本次组合目录>'
python bridge_cli.py install 'builds/<本次组合目录>' --mod-root 'C:/MyCK3User/mod' --storage-root 'E:/CK3CharacterData'
python bridge_cli.py verify-install 'state/installs/<本次事务>'
python bridge_cli.py trace-state 'E:/CK3CharacterData/<模型目录>' arms_crossed
# 如需回退该工具事务：
python bridge_cli.py rollback 'state/installs/<本次事务>'
```

安装需要作者有意执行。工具不选择播放集、不启动游戏。完整退出并重启后，游戏内测试由用户完成。构建成功、安装读回、游戏加载、用户视觉验收必须分别记录。

## 公开库与本机生成

仓库和公开源码 ZIP **不含完整 CK3 原版或派生 Runtime 着色器**。`bridge/runtime.py` 保存本项目的改写算法与材质逻辑，从作者自己的 `game/gfx/FX/court_scene.shader` 本机生成；`compile` 与 `runtime-zip` 均会触发此生成。生成物依赖 CK3 文件，分享前另行核对许可。源码包使用 `python tools/prepare_public_release.py` 验证并生成，不能把本机 `runtime-zip` 直接当成本仓库公开附件。

不收录角色模型/贴图、Unity/Blender 工程、游戏原始资源、存档、本机配置、密钥、机甲实验或 EXE 反汇编材料。没有指定本项目开源许可证；不要把可公开查看等同于任意再许可授权。

## 开发验证

```powershell
python -m unittest discover -s tests -p 'test_*.py' -v
python tools/prepare_public_release.py
# Blender 内另测站姿数值约束：
& 'C:/Path/To/blender.exe' --background --disable-autoexec --python-exit-code 7 --python tests/test_stance_blender.py
```

普通 Python 会跳过需要 Blender mathutils 的站姿测试。导入格式夹具在 `tests/make_format_fixtures.py` / `tests/run_intake_checks.py`，仅验证合成内容与容器路径。宽站姿、衣物碰撞、表情、动作过渡及多 Mod 共存仍须真实游戏验证。
