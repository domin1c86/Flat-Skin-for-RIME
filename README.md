# 元书输入法 · 扁平灰白

`default/` 是可导入皮肤的源码与生成配置，`preview/index.html` 保留之前的三种风格对照预览。当前选定的是方案 2：扁平灰白。

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

## 更新预览图

可选，需要 Pillow：

```shell
python scripts/build_skin.py --compile-only
python scripts/render_skin_preview.py
python scripts/build_skin.py
```

`render_skin_preview.py` 从已生成配置读取键位、尺寸、配色、双层键面和分类数据，生成 `default/demo.png`。图中的 SF Symbols 是近似绘制，图片明确标记为配置示意；不能替代元书实机验证。

## 实机验收

将 `.cskin` 通过文件或分享菜单用元书打开并启用，确认以下行为：

- iPhone 横竖屏、浅色深色下，主键盘、数字页、符号页均完整显示，切页高度一致。
- Q–P 上划输入 1–0，其余字母上划输入上标；Shift、大写锁定后上标仍显示。
- 中英切换后键面状态与 RIME ascii_mode 一致，逗号、句号输入正确的全角/半角字符。
- 空格选定候选、删除长按连删、普通回车和搜索/发送标签正常。
- 符号分类可切换；锁定可以连续输入；返回键可以回到进入符号页之前的键盘。
- iPad 五行布局和分体正常，浮动键盘也有完整映射。

皮肤不更改 RIME 输入方案。原有 iPad 布局与动作保留，配色统一使用扁平灰白。

配置能力依据元书官方文档的[布局](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/layout/)、[集合视图](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/collection/)、[按键动作](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)和[条件样式](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/parameters/)。
