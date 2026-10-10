// 已确认的三选气泡。选择项直接上屏，普通点按与上划仍走原有动作。
local Style = import 'Style.libsonnet';
local colors = import '../Constants/Colors.libsonnet';
local metrics = import '../Constants/Metrics.libsonnet';

{
  new(c, symbol, isPortrait, state='Chinese')::
    local n = c + 'Button' + state;
    // 竖屏第二颗键也靠近边缘；横屏只需处理最外侧 Q/P。
    local left = std.count(std.stringChars(if isPortrait then 'qwa' else 'q'), c) > 0;
    local right = std.count(std.stringChars(if isPortrait then 'pol' else 'p'), c) > 0;
    local ids = if left then ['Symbol', 'Upper', 'Lower']
      else if right then ['Lower', 'Upper', 'Symbol'] else ['Upper', 'Symbol', 'Lower'];
    local selected = if left then 0 else if right then 2 else 1;
    local optionName(id) = n + 'Hold' + id;
    local values = { Upper: std.asciiUpper(c), Lower: c, Symbol: symbol };
    // Q/P 的触摸区域从屏幕边缘开始。按键相对宽度 + 外侧零留白可保持
    // 最外侧单元格中心与按键中心对齐，避免固定 40pt 单元格在小屏上越界。
    local outer = isPortrait && (c == 'q' || c == 'p');
    // 横屏 A/L 的可视中心靠近侧边：按键比例宽度使小屏仍可居中，
    // 同时维持字号不变；其他非外侧键使用预览的 40pt。
    local homeEdge = !isPortrait && (c == 'a' || c == 'l');
    local size = { width: if outer then { percentage: 1 }
      else if homeEdge then { percentage: 0.6 } else 40, height: 44 };
    local padding = { top: 4, bottom: 4, left: if outer && c == 'q' then 0 else 4,
      right: if outer && c == 'p' then 0 else 4 };
    {
      [n + 'HoldGridStyle']: {
        symbolRows: [[optionName(id) for id in ids]],
        size: size, spacing: { horizontal: 0, vertical: 0 }, insets: padding,
        anchor: { row: 0, col: selected }, selected: { row: 0, col: selected },
        // 锚点对齐后上移到按键上方。父区域越界修正交由元书处理。
        offset: { x: 0, y: if isPortrait then -55 else -49 },
        moveStep: { horizontal: 24, vertical: 44 }, moveThreshold: 10,
        checkIfOverflowsParentHeight: true,
        backgroundStyle: 'phoneHoldBackground', selectedBackgroundStyle: 'phoneHoldSelectedBackground',
      },
      // 旧版本忽略网格参数时，仍能使用单行长按列表。
      [n + 'HoldListStyle']: {
        symbolStyles: [optionName(id) for id in ids], size: size, insets: padding,
        selectedIndex: selected, checkIfOverflowsParentHeight: true,
        backgroundStyle: 'phoneHoldBackground', selectedBackgroundStyle: 'phoneHoldSelectedBackground',
      },
    } + {
      [optionName(id)]: {
        type: 'button', foregroundStyle: optionName(id) + 'Foreground',
        action: { symbol: values[id] }, uppercasedStateAction: { symbol: values[id] },
      }
      for id in std.objectFields(values)
    } + {
      [optionName(id) + 'Foreground']: Style.text({
        text: values[id], fontSize: 22.5,
        normalColor: colors.standardCalloutForegroundColor,
        highlightColor: '#FFFFFF',
      })
      for id in std.objectFields(values)
    },

  shared:: {
    phoneHoldBackground: Style.geometry({
      normalColor: colors.standardCalloutBackgroundColor,
      highlightColor: colors.standardCalloutBackgroundColor,
      cornerRadius: metrics.key.cornerRadius,
      normalShadowColor: '#000000', highlightShadowColor: '#000000',
      shadowOpacity: { light: 0.18, dark: 0.36 }, shadowRadius: 8,
      shadowOffset: { x: 0, y: 3 },
    }),
    phoneHoldSelectedBackground: Style.geometry({
      normalColor: colors.blueButtonBackgroundColor,
      highlightColor: colors.blueButtonBackgroundColor,
      cornerRadius: metrics.key.cornerRadius,
    }),
  },
}
