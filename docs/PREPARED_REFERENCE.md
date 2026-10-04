# prepared-reference-v1：完整导出的实际输入契约

本库没有公开角色样例或已验证参考模型。`examples/profile.example.json` 是字段模板，不是一份能直接构建的模型。若没有自己准备的参考 Mod，先用 inspect 检查源文件，并完成本契约，再执行 audit/build。

## 配置字段

schema_version=1；id 为 3–48 字符的小写字母/数字/下划线，以字母开头，并与 profiles.local 文件名一致；adapter 只能是 character。prepared_blend 指向经过准备的工程，reference_mod 指向作者有权使用的参考包，reference_slot 决定历史输入前缀 `csc_<slot>`。它只是迁移输入契约；输出使用 `char_<id>`。

`exclude_shapes` 列出经作者审阅的额外网格，`add_reference_helpers` 是允许补齐的参考辅助节点，`part_roles` 可标识裙摆等部件，`attachment_nodes` 指定必要挂点，`author_notes` 记录约束。`unity_inventory` 可引用作者自行准备的 Unity 装配清单，仅辅助审阅。motion_guard 和 stance 见作者指南；stance 默认关闭。

## 参考文件结构

```text
reference_mod/
  common/portrait_types/csc_personal_types.txt
  common/genes/csc_<slot>_native*                 # 如采用
  gfx/models/portraits/csc_<slot>/
    csc_<slot>.asset
    csc_<slot>.mesh
    csc_<slot>_camera.asset
    <camera.asset 引用的代理网格>
    <asset 引用的本地纹理、身体/附加动画>
  gfx/portraits/portrait_animations/animations.txt
  gfx/portraits/accessories/csc_<slot>_native*    # 如采用
  gfx/portraits/portrait_modifiers/csc_<slot>_native* # 如采用
```

portrait_types 中必须有 `csc_<slot>_3d`。身体/代理 .asset 的 pdxmesh 记录本地 file、meshsettings 与已转换 animation/additive_animation；引用必须位于该人物资源目录之内。其他私有控制与附件必须闭合，不能仅有名称没有实际资源。

准备后的 Blender 场景须有一个最终骨架；对象 data.name 与参考 meshsettings 的 name 对应，不重复。漏部件报 MISSING_PARTS，未审阅额外部件报 UNREVIEWED_PARTS；参考骨骼缺失或新增骨骼需要明确准备，不能自动删掉继续导出。

当前材质迁移识别 `gfx/FX/csc_<slot>_v013.shader` 及历史人物 Effect 前缀 `csc_orlando_v013_`，后者只保留为已有参考输入的兼容别名，不携带对应角色资产。作者的新参考若直接使用 ck3char_avatar_*，应按 check 核对实际 shader/effect。不要因为名字相近就声称任意旧前置均可迁移。

参考动作骨骼顺序须与参考网格一致。使用未经烘焙的 animation-set import 会触发 UNBAKED_IMPORT。build 按绑定姿态差异重定向现有参考动作，并检查输出；它不会凭空建立原始 VRC 骨架到 CK3 原版骨架的通用映射。

## 输出与边界

`package/manifest.json` 记录文件与选择器哈希、char_<id> 命名空间、Runtime API=1 和 requires_runtime。compile 校验每份输入、合并同一批人物选择器、生成 Runtime 和自动/人工报告。不要让独立人物包各自覆盖 animations.txt 后直接一起启用。

工程序列是：源导入 → 人工准备 → audit → build → compile → check → 有意安装 → verify-install → 用户游戏验收。解析通过不能省略中间准备步骤。
