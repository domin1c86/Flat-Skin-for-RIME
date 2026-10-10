# 元书输入法 · 扁平灰白

`default/` 是可导入皮肤的源码与生成配置，`preview/index.html` 保留之前的三种风格对照预览。当前选定的是方案 2：扁平灰白。

## 长按气泡与拼音字号

离线打开 `preview/index.html`，点击「体验扁平灰白」，按住任意字母 300ms，左右滑动选择，松手输入。常规排序为「大写／对应上标／小写」；气泡以按键中轴居中会越界时，左缘改为「上标／大写／小写」，右缘镜像为「小写／大写／上标」，最外侧选项的中心对齐按键中心。极端边缘只收窄该选项以避免裁切，其余选项与文字大小保持一致。气泡外框沿用键帽的圆角、无描边和主题底边效果，并增加两层柔和阴影区分主键盘背景；深色模式使用稍深的阴影。示意气泡与实际交互气泡使用同一套样式。

长按默认选中对应上标的符号或数字，不受中英文、Shift 或大写锁定影响。常规布局选中中间项，左缘选中最左项，右缘选中最右项；不滑动直接松手即输入上标。长按选中的字母在本地演示中直接输入，不经过拼音候选。左右滑动以初始选项为原点，不受气泡移位影响。

气泡打开后，本次触摸不再触发普通上划输入。上下移动不会改选符号；垂直移动超过 44pt，或水平移出三项范围后清除高亮，松手取消，移回可重新选择。未长按时的点击与上划保持原有行为。页面同时展示 F 键的三种选中状态；放大预览可切换深浅色、横竖屏、中英文与 Shift。

实际皮肤已为 iPhone 主界面 26 个字母配置 `hintSymbolsGridStyle`，以元书商店版 ≥1.6.27 为目标；同时保留单行 `hintSymbolsStyle` 作为旧版回退。候选项使用 `symbol` 动作直接输入固定大小写字母、符号或数字；普通点按继续发送拼音字母，上划的符号或数字也使用 `symbol` 直接输入。原生阴影使用一个柔和的 geometry 阴影，HTML 使用两层阴影近似展示。

中文普通气泡保持大写，英文普通气泡与键面一致：普通状态小写，Shift／大写锁定大写。上滑气泡优先显示当前语言的符号，不受大小写影响。中文上标与长按符号项为 `1234567890～！＠＃％“”＊？（）－＿：；｀`，英文为对应半角字符，H/J 均使用英文直双引号。数字保留半角，两侧长按大小写字母选项保留；符号直接输入，不交给薄荷/RIME 转换。

符号定义集中在 `default/jsonnet/Constants/LetterSymbols.json`；修改后运行 `python scripts/sync_preview_symbols.py` 将同一份映射嵌入离线 HTML，再构建。首次状态采用完整条件前景，语言通知同时更新上滑动作、短按与长按引用，保留完整键面几何。原生首次恢复英文状态时的动作、拼音尚未上屏时的直接符号输入仍需实机检查。

原生气泡按键位与方向选择边缘排序：竖屏 Q/W/A 左开、P/O/L 右开，横屏只处理 Q/P。以符号格为锚点并上移到按键上方，元书继续处理越界修正。竖屏 Q/P、横屏 A/L 使用相对按键宽度适配小屏，其他单元格为 40×44pt；原生统一单元格宽度与网页仅收窄最外侧单元格的方式略有差别，需要在目标 iPhone 上确认边缘效果。

网页长按延迟为 300ms。当前公开皮肤配置未提供原生长按触发时间字段，`.cskin` 不能强制将元书设为 300ms；原生触发时间由元书控制。皮肤已配置横向移动 24pt 换格、10pt 起始阈值。长按与普通上划的互斥、远移取消及直接输入仍需实机验收。浏览器地址加 `?longpress=1` 可直接打开扁平灰白放大预览。

iPhone 的拼音预编辑字号为 12pt，候选字号仍为 16pt，预编辑区高度仍为 25pt；iPad 保持原有字号。皮肤不添加音节分隔符，不修改薄荷/RIME 方案。

iPhone 字母键首次加载使用完整的条件前景，中文显示大写、英文跟随 Shift；条件数组不混入独立样式名。中英文通知从同一份完整按键定义派生，保留 A/L 的可视区域、尺寸、动作与气泡，避免切换后字母向外偏移。上标与字母明确在可视区域内水平居中。

## 构建

需要 Python 3.10+ 与 Google Jsonnet CLI。Windows、macOS、Linux 均可使用同一套 Python 脚本，不依赖 make、zip 或 rsync。

```shell
python scripts/build_skin.py
```

脚本会从 `default/jsonnet/main.jsonnet` 编译全部配置，检查深浅文件配对、设备映射、样式引用、动作、颜色、布局尺寸和 iPad 分体布局，再生成 `dist/扁平灰白.cskin`。压缩包包含一层 UTF-8 的「扁平灰白」目录及 Jsonnet 源文件，便于在手机继续修改。

Jsonnet 位于 PATH 时会自动使用；也可传 `--jsonnet PATH`，或放在 `.tools/jsonnet.exe`（Windows）/ `.tools/jsonnet`（其他平台）。项目使用 Jsonnet 0.21.0 验证过。

```shell
python scripts/build_skin.py --compile-only
python scripts/build_skin.py --check
python -m unittest discover -s tests -v
```

配置使用 JSON 语法保存为 `.yaml`；JSON 是 YAML 的子集，因此不需要额外的 YAML 解析库。

中英图标已作为透明图片资源保存在深浅色的 `resources/` 目录中，普通构建无需额外依赖。仅重新生成图标时，需要 Node.js 与 `sharp`，运行 `node scripts/build_language_assets.cjs`；该脚本也会同步离线 HTML 中的图标。

中文逗号和句号使用水平按笔画边界居中的透明图形，垂直位置与英文逗号、句点对齐。重新生成这两个资源时运行 `node scripts/build_punctuation_assets.cjs`，同时更新 HTML 预览中的相同轮廓；输入动作仍为原来的中文标点。

## 更新预览图

可选，需要 Pillow：

```shell
python scripts/build_skin.py --compile-only
python scripts/render_skin_preview.py
python scripts/build_skin.py
```

可使用 `python scripts/render_skin_preview.py --category 中文 --output dist/中文分类示意.png` 查看其他分类的选中状态；分类选项为常用、中文、英文。

运行 `python scripts/render_skin_preview.py --language-states --output dist/字母显示修复示意.png` 可比较切换后的中文、英文和英文 Shift 状态。渲染器分别模拟初始条件、语言通知及大小写前景，拒绝原生不支持的混合样式数组。

运行 `python scripts/render_callout_preview.py` 查看短按大小写与上滑符号；运行 `python scripts/render_hold_preview.py --language-states` 比较中英文 Q/F/P 的长按选项。均读取当前生成配置，不能替代原生状态恢复与手势验收。

`render_skin_preview.py` 从已生成配置读取键位、尺寸、配色、双层键面和分类数据，生成 `default/demo.png`。图中的 SF Symbols 是近似绘制，图片明确标记为配置示意；不能替代元书实机验证。

## 实机验收

将 `.cskin` 通过文件或分享菜单用元书打开并启用，确认以下行为：

- iPhone 横竖屏、浅色深色下，主键盘、数字页、符号页均完整显示，切页高度一致。
- Q–P 上划直接输入半角 1–0，其余字母上划输入当前语言的上标；中文 F → ＃、H/J → “/”，英文 F → #、H/J → 直双引号。键面上标、气泡、实际输入应一致，Shift 与大写锁定不改变符号。普通气泡中文为大写，英文跟随键面大小写。
- 长按 F 默认选中中文 ＃ 或英文 #、Q 默认选中 1、P 默认选中 0，左右滑选大小写字母。检查 Q/W/A 与 P/O/L 的竖屏边缘位置，以及横屏 Q/P。气泡有柔和阴影、无描边、8.5pt 圆角；上移和远移取消不应另行触发普通上划输入。
- 拼音预编辑为 12pt，候选字为 16pt；候选字号若在元书中手动设定，以应用设置为准。音节分隔仍由原有输入方案提供。
- 中英切换后键面状态与 RIME ascii_mode 一致，逗号、句号输入正确的全角/半角字符。
- 首次打开中文或英文键盘，26 个字母与上标均完整显示，无需先切换语言；连续执行中文→英文→中文及反向切换，并组合 Shift／大写锁定，确认 A/L 始终在各自键帽内居中。配置与示意图检查不能替代实机验收。
- 空格选定候选、删除长按连删、普通回车和搜索/发送标签正常。
- 符号分类可切换；锁定可以连续输入；返回键可以回到进入符号页之前的键盘。
- 中英按钮使用已确认的整体图标，横竖屏均等比居中；「中」和「英」激活时分别使用同一黑色／白色。未激活文字和转角线为灰色。
- 主界面工具栏顺序是菜单、留白、符号、Emoji、剪贴板、方案切换，不显示脚本按钮；符号按钮打开符号页，方案切换打开原生方案列表。数字页、符号页和 iPad 的工具栏保持原状。
- 常用、中文、英文分类的高亮均有圆角和内缩，首尾分类选中时不覆盖外层圆角。
- iPad 五行布局和分体正常，浮动键盘也有完整映射。

皮肤不更改 RIME 输入方案。原有 iPad 布局与动作保留，配色统一使用扁平灰白。

Emoji 保留 `{ keyboardType: 'emojis' }` 原生入口。公开动作接口未提供已核实可用的笑脸分类选择参数；本项目不保证强制打开该分类，使用说明中保留手动选择笑脸图标的方法。HTML 中的 Emoji 是本地交互演示，不能证明元书原生默认分类已改变。

配置能力依据元书官方文档的[布局](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/layout/)、[集合视图](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/collection/)、[按键动作](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)和[条件样式](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/parameters/)。

可运行 `python scripts/render_hold_preview.py` 生成 `dist/长按气泡配置示意.png`，从已编译配置检查 Q/F/P 的浅色深色气泡；它是配置示意，不能替代 iOS 实机测试。
