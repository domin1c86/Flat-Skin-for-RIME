# 元书输入法 · 扁平灰白

`default/` 包含可导入皮肤的源码与生成配置；`preview/index.html` 是可离线打开的设计与操作演示。当前选择方案 2：扁平灰白。

## 独立中英文主键盘

iPhone 中文 `pinyin`、英文 `alphabetic` 使用同一份布局构造器，分别生成完整的横竖屏、浅色深色配置。每份文件的上标、上滑显示与动作、长按网格与旧版回退、逗号句号都固定为该键盘的语言，不再等待 `ascii_mode` 通知更新。A/L 的可视区域、气泡锚点及所有按键尺寸共用同一份定义。

中文字母键面和普通气泡均为大写，点按仍向 RIME 发送拼音字母；英文普通气泡跟随键面，普通状态小写，Shift／大写锁定大写。上滑气泡显示符号，Shift 不改变符号。英文自动句首大写由元书决定，皮肤不强制启用。

符号采用独立的 Unicode 基准逐键校验：中文为 `1234567890～！＠＃％“”＊？（）－＿：；｀`，英文为对应半角字符，H/J 两键均为直双引号。数字保留半角。上滑和长按符号项均使用 `symbol` 直接输入，普通字母用 `character` 交给当前方案。

## 中英切换与方案选择

主界面的中英按钮现在同步切换键盘类型与 RIME 方案：

| 操作 | 键盘类型 | 输入方案 |
| --- | --- | --- |
| 中文 → 英文 | alphabetic | melt_eng / Easy English Nano |
| 英文 → 中文 | pinyin | double_pinyin_flypy / 小鹤双拼－薄荷定制 |

返回中文固定使用目前约定的小鹤双拼，不自动记忆其他中文方案。方案 ID 集中在 `default/jsonnet/Constants/InputRoutes.json`。

工具栏顺序仍为菜单、留白、符号、Emoji、剪贴板、方案选择；方案选择图标保持不变，打开皮肤自己的面板。面板列出小鹤双拼－薄荷定制、薄荷全拼、薄荷小鹤混输和 Easy English Nano，每项同步选择键盘类型与方案。它不扫描手机已安装方案，所选方案必须在元书中安装并启用。`skinSchemes` 是这个面板的键盘类型。

英文 `melt_eng` 需要关闭 ASCII 直通才能生成词库候选。皮肤采用官方的 `keyboardType + switchRimeSchema` 组合动作，不使用不明确的 ASCII 设置接口，也不修改你的薄荷配置。请核实手机上的英文方案 `ascii_mode` 默认状态及候选。

数字页返回使用 `returnPrimaryKeyboard`；符号页返回使用 `returnLastKeyboard`，应回到进入前的中／英文主键盘，需实机验证。数字、符号页原有工具栏与分类保持原样。

**支持边界：** 从元书应用或原生菜单独立切换方案／ASCII 状态，未必同步改变自定义键盘类型。请使用本皮肤的中英按钮或方案面板重新同步。冷启动时元书是否恢复匹配的键盘类型与方案也需实机确认。

## 已确认的气泡与外观

长按三选气泡默认选择上标：通常为「大写／符号／小写」，靠左为「符号／大写／小写」，靠右镜像。原生竖屏 Q/W/A 左开，P/O/L 右开，横屏 Q/P 使用边缘排序。40×44pt 单元格、4pt 留白、22.5pt 字号、8.5pt 圆角、无描边，柔和阴影；边缘宽度适配沿用已确认设置。长按字母选项直接输入固定大小写，不进入拼音候选。

网页长按为 300ms，水平 24pt 换格、提前移动超过 10pt 取消长按计时。进入气泡后不触发普通上滑，远移取消，返回可恢复高亮，松手只输入一次。原生长按时间由元书控制；网格以商店版 ≥1.6.27 为目标，保留单行列表回退。原生上滑互斥、边缘锚点和取消仍须实机确认。

中英图标沿用已确认的中／英对角布局，激活色一致，灰色圆弧转角与未激活文字同色。中文逗号与句号使用水平笔画居中的图形，垂直高度与英文标点对齐。符号分类高亮保持 8.5pt 圆角及左右 3pt、上下 2pt 内缩。

iPhone 拼音预编辑字号为 12pt，候选为 16pt，预编辑区高度 25pt。音节分隔仍由输入方案提供。Emoji 使用原生 `emojis` 页，皮肤不保证默认打开笑脸分类。

iPad 普通布局与动作继续保留，浮动键盘复用 iPhone 配置。新增 alphabetic 的 iPad 普通映射仍使用原有 iPad 布局；本轮独立英文符号功能以 iPhone 和浮动键盘为目标。

## 构建、预览和审计

需要 Python 3.10+ 与 Jsonnet CLI；可使用 PATH 或 `.tools/jsonnet.exe`。Pillow 仅用于示意图，图标资源已随皮肤保存。

```shell
python scripts/sync_preview_symbols.py
python scripts/build_skin.py --compile-only
python -m unittest discover -s tests -v
python scripts/render_skin_preview.py
python scripts/render_callout_preview.py
python scripts/render_hold_preview.py --language-states
python scripts/build_skin.py
python scripts/audit_letter_symbols.py
```

目前生成 28 份配置，检查所有映射、引用、动作、布局与 iPad 分体，然后生成 `dist/扁平灰白.cskin`。配置以 JSON 语法保存为 YAML；压缩包包含一层 UTF-8「扁平灰白」目录及 Jsonnet 源码。

运行 `python scripts/render_skin_preview.py --language-states --output dist/中英文主键盘配置示意.png` 比较中英文及 Shift，使用 `--category 中文` 查看分类选中背景。示意图读取真实配置，SF Symbols 为近似绘制，不是 iOS 实机截图。

原生符号映射位于 `LetterSymbols.json`，方案映射位于 `InputRoutes.json`；修改后运行同步脚本，将两份数据嵌入离线 HTML，无需联网。预览的方案面板和中英按钮同步变化，数字／符号返回保留语言与方案；英文词库候选由真实元书提供，网页不模拟。

重新生成中英图标或标点图形时，需要 Node.js 与 sharp，分别运行 `scripts/build_language_assets.cjs` 或 `scripts/build_punctuation_assets.cjs`。

逐键结果见 [中英文符号核对报告](docs/中英文符号核对报告.md)，[修复前记录](docs/中英文符号核对报告-修复前.md)保留之前的缺口。审计退出码 0 仅表示配置一致，不是实机验收通过。

## 交付与实机验收

本轮是完整配置验证包，尚未完成计划中的最小实机验证。此环境无法运行元书 iOS，请先按 [实机验收清单](docs/中英文键盘实机验收.md) 测试 Q/F/H/J、A/L、逗号句号，再扩展到全部 26 键。冷启动恢复、组合动作顺序、英文候选、预编辑期间直接符号输入、数字与符号返回是验收重点。

将 `.cskin` 分享给元书，重新导入并启用。实机通过后才标记为最终验收完成。

依据：[官方动作与组合切换](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)、[皮肤结构](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/structure/)、[配置索引](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/keys-reference/)。
