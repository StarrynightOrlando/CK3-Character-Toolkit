# 人物材质与着色器经验

实现来源：`bridge/runtime.py`。完整 shader 从本机 `gfx/FX/court_scene.shader` 生成；本仓库只保存改写算法与原创着色逻辑，不保存 CK3 原始/完整派生 shader。

## 绑定关系与效果

逐一核对 `.asset` 的 shader_file/effect、meshsettings.shader 和 `.mesh` 内嵌 material.shader。只改其中一个或修改同文件另一段 MainCode，不能证明模型实际使用了新效果。本库改写的是 **PS_attachment**，该分支 hover 使用 **AppliedHover**。

| Effect | 适用方向 | 本库实际行为 |
| --- | --- | --- |
| `ck3char_avatar_matte` | 不透明人物服装、身体等 | 基础贴图颜色乘轻度平滑明暗，减少写实反射带来的外观偏差 |
| `ck3char_avatar_cutout` | 需要 alpha 的发丝、睫毛/衣片等 | matte 的着色逻辑 + alpha_to_coverage BlendState；需实测边缘和排序 |
| `ck3char_avatar_face` | 希望稳定基础颜色的脸部 | 颜色分支不乘 MbShade，避免脸部明显受该法线明暗项影响 |
| `ck3char_avatar_face_cutout` | 需要 alpha 的脸部相关部件 | face 分支 + alpha_to_coverage BlendState；不是通用眼球材质修复 |

每个效果另有 `<effect>_selection` 和 `<effect>Shadow`，共 12 个私有 Effect。保留选择与阴影入口，移除复制来的原版 Effect 定义，避免私有像素逻辑劫持原版皮肤、眼睛或附件。颜色效果定义包含 USE_CHARACTER_DATA、PDX_MESH_BLENDSHAPES、DOUBLE_SIDED_ENABLED；脸部分支另含 MB_AVATAR_FACE。

## 实际颜色逻辑

`MbNormal` 由输入切线空间法线变换到世界空间。`MbLight` 从太阳光属性获取方向；`MbShade = smoothstep(0.10, 0.55, saturate(dot(MbNormal, MbLight._ToLightDir)))`。普通人物颜色为 `Diffuse.rgb * (0.80 + 0.20 * MbShade) * (1.1 / PI)`，脸部为 `Diffuse.rgb * (1.1 / PI)`，两者再乘 `1 + saturate(AppliedHover) * 0.08`。

它是轻度二次元人物明暗方案，不是完整 Unity toon 渲染器，没有自动迁移 lilToon/Poiyomi 的描边、MatCap、ramp 或插件逻辑。代码里的 MB_AVATAR_FACE 是历史宏命名，不表示本库包含其他产品适配器。脸部颜色稳定也不保证眼睛高光、光照、阴影与后处理在所有场景完全相同。

## 贴图与透明准备

作者先核对源材质实际基础贴图、颜色乘数、alpha、UV 和材质槽。opaque 材质不能误带透明 alpha；发丝与睫毛的边缘要在正/侧/背面和远近镜头看。参考绑定使用 texture_diffuse、texture_normal、texture_specular 三个入口；这些纹理需作者提前准备，build 不自动烘焙 Unity 材质。

法线采样继承 CK3 的 UnpackRRxGNormal 路径，不能直接把 Unity 常规 RGB normal 的通道当成完全相同。转换或使用中性法线时应核对 CK3 的实际解码；无效法线会影响身体明暗。properties/specular 保留文件契约，但不要把本库的自定义 Diffuse 颜色分支描述成完整金属 PBR；具体通道意义以作者本机 CK3 代码与采用的像素分支为准。

当前 cutout Effect 选择 alpha_to_coverage 的 BlendState，**没有额外定义 ALPHA_TO_COVERAGE 宏**。不要宣称该宏控制的 mip alpha 重标定/SharpenAlpha 已启用。当前 selection/Shadow 变体也没有独立复制一套透明边缘裁切逻辑；发丝选择轮廓和投影须游戏实测，不能只凭变体名称宣布正确。为了保留 0.5.0 材质经验，这次公开整理不未经视觉回归改动其公式。

## 版本与回归

生成器要求 PS_attachment 和 PS_portrait_hair_backface 段及 VARIATIONS_ENABLED 区块符合预期文本结构。CK3 更新后若结构变化，应报错并人工更新适配，不能随意扩大替换范围。supported_version 来自 launcher 的 rawVersion，不是未来版本验收结果。

每次修改以原版人物作对照，分别看皮肤/脸部、头发透明、双面、选择与阴影。检查人物头像、半身面板、理发器、宫廷及打开顺序。通过私有命名空间静态检查不能替代当前版本游戏回归。
