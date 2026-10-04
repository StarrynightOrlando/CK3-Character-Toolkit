# 第三方来源与分发边界

## CK3 / Clausewitz

本项目不是 Paradox 官方工具。生成器读取使用者本机 CK3 的 `game/gfx/FX/court_scene.shader` 和必要的原版参考结构。本仓库没有原版 shader/include、模型、动画、纹理、游戏程序或反汇编材料。

完整 Runtime shader 是在本机对 CK3 文件改写后的生成物；它不随公开源码包提供。发布组合人物包或本机 Runtime 前，作者须独立核对游戏、模型、纹理及动作的分享条件。仓库中的生成算法不能给第三方资源重新授权。这里不作“原版派生文件可任意再分发”的断言。

## io_pdx_mesh

作者：ross-g 及其贡献者。上游 [io_pdx_mesh](https://github.com/ross-g/io_pdx_mesh)，[许可文件](https://github.com/ross-g/io_pdx_mesh/blob/master/license.txt)，[安装说明](https://github.com/ross-g/io_pdx_mesh/blob/master/readme.md)。上游标示 GNU GPL v3。本地参考依赖 revision 为 `2249e35f80a1cc04ba4c2b8e4c650f36b18085db`（0.91）；本项目不捆绑它、不更改其作者与许可。

作者另行下载与安装；settings.pdx_tools 指向包含 io_pdx_mesh 目录的父目录。worker 使用其 pdx_data 与 Blender exporter API，实际可用性需 doctor 和实际导出验证。更换依赖版本不能仅靠目录存在判断兼容。未捆绑依赖不意味着集成后的分发义务被豁免；任何整体分发需复核对应许可，本项目尚未指定自身开源许可证。

## Python / Blender / Unity / VRChat 与材质插件

分别由使用者自行安装，不随仓库提供。当前本机验证使用 Python 3.12；Windows 安装核验需要 3.12+ 的 Junction 检查 API。Blender 版本与 io_pdx_mesh API 需一起确认，不能把上游最低版本说明当成本工具全部版本的保证。

Unity / VRChat 只是部分人物的来源环境。UnityPackage 仅做清单检查；SDK、插件、lilToon、Poiyomi、PhysBone、Avatar 资产与商业贴图不捆绑、不自动转换。相关品牌名称用于描述输入边界，不表示隶属或认可。

## 本项目内容

源码从本地 CK3 Character Toolkit 0.5.0 候选白名单整理；作者指南汇总该人物工具的既有实现与经验，包含 AI 协作整理。没有声明用这些经验训练了模型。历史 `csc_*` 输入名称仅用于兼容迁移，不包含历史角色资产。许可状态见 LICENSE.md。
