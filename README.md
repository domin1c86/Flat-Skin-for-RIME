# 元书输入法 · 扁平灰白

`default/` 是可导入皮肤的源码与生成配置，`preview/index.html` 保留之前的三种风格对照预览。当前选定的是方案 2：扁平灰白。

## 长按气泡预览

离线打开 `preview/index.html`，点击「体验扁平灰白」，按住任意字母 300ms，左右滑动选择，松手输入。常规排序为「大写／对应上标／小写」；气泡以按键中轴居中会越界时，左缘改为「上标／大写／小写」，右缘镜像为「小写／大写／上标」，最外侧选项的中心对齐按键中心。极端边缘只收窄该选项以避免裁切，其余选项与文字大小保持一致。气泡外框沿用键帽的圆角、无描边和主题底边效果。

默认仍选中当前字母：中文按大写，英文跟随 Shift；长按选中的字母在本地演示中直接输入，不经过拼音候选。左右滑动以初始选项为原点，不受气泡移位影响。

气泡打开后，本次触摸不再触发普通上划输入。上下移动不会改选符号；垂直移动超过 44pt，或水平移出三项范围后清除高亮，松手取消，移回可重新选择。未长按时的点击与上划保持原有行为。页面同时展示 F 键的三种选中状态；放大预览可切换深浅色、横竖屏、中英文与 Shift。

这是交互设计预览，尚未加入实际皮肤；300ms 和滑选阈值是网页演示值。后续原生版本拟使用 `hintSymbolsGridStyle`，以元书商店版 ≥1.6.27 为目标，手势互斥及字母直接输入仍需实机验收。浏览器地址加 `?longpress=1` 可直接打开扁平灰白放大预览。

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

`render_skin_preview.py` 从已生成配置读取键位、尺寸、配色、双层键面和分类数据，生成 `default/demo.png`。图中的 SF Symbols 是近似绘制，图片明确标记为配置示意；不能替代元书实机验证。

## 实机验收

将 `.cskin` 通过文件或分享菜单用元书打开并启用，确认以下行为：

- iPhone 横竖屏、浅色深色下，主键盘、数字页、符号页均完整显示，切页高度一致。
- Q–P 上划输入 1–0，其余字母上划输入上标；上划气泡同步显示对应字符，普通按下仍显示字母。中英文、Shift 和大写锁定状态下均检查 F → #、Q → 1。
- 中英切换后键面状态与 RIME ascii_mode 一致，逗号、句号输入正确的全角/半角字符。
- 空格选定候选、删除长按连删、普通回车和搜索/发送标签正常。
- 符号分类可切换；锁定可以连续输入；返回键可以回到进入符号页之前的键盘。
- 中英按钮使用已确认的整体图标，横竖屏均等比居中；「中」和「英」激活时分别使用同一黑色／白色。未激活文字和转角线为灰色。
- 主界面工具栏顺序是菜单、留白、符号、Emoji、剪贴板、方案切换，不显示脚本按钮；符号按钮打开符号页，方案切换打开原生方案列表。数字页、符号页和 iPad 的工具栏保持原状。
- 常用、中文、英文分类的高亮均有圆角和内缩，首尾分类选中时不覆盖外层圆角。
- iPad 五行布局和分体正常，浮动键盘也有完整映射。

皮肤不更改 RIME 输入方案。原有 iPad 布局与动作保留，配色统一使用扁平灰白。

Emoji 保留 `{ keyboardType: 'emojis' }` 原生入口。公开动作接口未提供已核实可用的笑脸分类选择参数；本项目不保证强制打开该分类，使用说明中保留手动选择笑脸图标的方法。HTML 中的 Emoji 是本地交互演示，不能证明元书原生默认分类已改变。

配置能力依据元书官方文档的[布局](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/layout/)、[集合视图](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/collection/)、[按键动作](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)和[条件样式](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/parameters/)。
