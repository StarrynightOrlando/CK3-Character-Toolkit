# 公开整理、来源与验证记录

## 版本与白名单

公开整理版 `0.5.0-public.1` 来自 CK3 Character Toolkit 0.5.0 收尾候选。检查时本地源码与原工具 ZIP 的 49 份文件字节一致。原包校验值：

| 原候选 | SHA-256 |
| --- | --- |
| Toolkit 0.5.0 ZIP | `b902519e0563131a0638da6448f27ece0025d383c3cfcfcd9d00cb2a8134b662` |
| Runtime 0.5.0 ZIP（仅本机保留，不公开打包） | `0384755723b7ffb19afa433337ac96fdff068dc23fb87cd810d0f0f1a93df953` |

公开内容限于根目录入口/文档、bridge、tests、examples、tools、.github。没有复制私人角色、贴图、参考工程、已安装模组、历史机甲工具或反汇编目录。本次仅清理人物工具中不再使用的其他产品分支与标签；材质公式与 Runtime API 保持原状。

## 验证结果（2026-10-04）

使用 Python 3.12.13、Blender 5.2.2 LTS 和本机检测到的 CK3 1.20.0.3。该版本号只记录生成环境，不表示本次已做游戏视觉验收。

- 普通 Python 单元套件：41 项中 35 项通过，6 项需要 Blender mathutils 而跳过。
- Blender 单独站姿约束套件：上述 6 项全部通过；这是数值约束证据，不是站姿视觉验收。
- Blender 合成格式夹具：blend、fbx、glb、gltf、obj、vrm 共 6 条导入路径通过，并保持 ck3_ready=false；unitypackage 清单检查通过且 imported=false。
- VRM 夹具仅由 GLB 容器构成，没有验证真实 VRM 扩展语义、表情或春骨，也没有验证全部商业 VRC Avatar。
- 用本机游戏重新生成的 Runtime shader 与原 0.5.0 Runtime ZIP 中 shader **逐字节一致**，SHA-256 为 `98ce864dfce30caea09d319398f3bca07eb76763525ca5f8076179111971e6b1`；12 个 Effect 均为唯一 ck3char_* 命名。完整 shader 留在忽略的本机构建目录，不加入源码包。
- 公开源码打包器校验白名单、文本类型、已知凭据模式、个人 Windows 路径、Markdown 本地链接、Git 跟踪范围，以及 ZIP 与审核源文件的逐文件一致性。

没有执行私人角色完整 build、安装更新或游戏启动；现有模组和原始发布包保留。人物完整输出仍需作者自己的 prepared-reference-v1 输入。新增加的 CI 工作流尚未在远端执行，本地等价命令的结果如上。

## 生成公开附件

```powershell
python tools/prepare_public_release.py
```

生成 `releases/0.5.0-public.1/CK3-Character-Toolkit-0.5.0-public.1-source.zip`、`public-source-audit.json` 和 `SHA256SUMS.txt`，均在 Git 忽略目录。ZIP 使用排序成员与固定时间戳；同一源码文件字节可重复生成相同包。Git 文本换行设置不同的 checkout 可能产生不同字节，应以各次 SHA256SUMS 为准。

`public-zip` 是源码打包；`runtime-zip` 则从 CK3 生成游戏派生文件，二者分发边界不同。禁止把整个 releases/builds 目录递归作为公开附件。发布前复核第三方/模型许可，以及 LICENSE.md 中尚未指定本项目开源许可的状态。

## Git 与远端

仓库目标应来自用户提供的 URL 或可核实的现有 remote。原源目录没有 Git remote，不能根据项目名自行假定远端。整理完的本地提交与远端上传分别确认；远端上传后还需核对实际提交 SHA/分支/内容。未获得目标仓库时仅保留本地候选与源码包。
