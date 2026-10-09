// 数字九宫格：左侧一体运算符，中间 1–9，右侧删除 / . / @。
local Keys = import '../Constants/Keys.libsonnet';
local metrics = import '../Constants/Metrics.libsonnet';
local colors = import '../Constants/Colors.libsonnet';
local fonts = import '../Constants/Fonts.libsonnet';
local Button = import '../Components/Button.libsonnet';
local Layout = import '../Components/Layout.libsonnet';
local Phone = import '../Components/iPhone.libsonnet';
local Style = import '../Components/Style.libsonnet';
local Theme = import '../Components/Theme.libsonnet';
local column(rows, style=null) = Layout.stack('VStack', rows, style);
local middleWidth = { size: { width: '2.1/9.7' } };
local sideWidth = { size: { width: '1.7/9.7' } };
local digits = ['oneButton', 'twoButton', 'threeButton', 'fourButton', 'fiveButton',
                'sixButton', 'sevenButton', 'eightButton', 'nineButton', 'zeroButton'];

{
  new(isPortrait=true)::
    local insets = metrics.keyInsets.iPhone[if isPortrait then 'portrait' else 'landscape'];
    Style.merge([
      Phone.base(isPortrait),
      {
        keyboardLayout: [
          Layout.stack('HStack', [
            column([Layout.row(['numericOperators'])], 'numericSideColumn'),
            column([Layout.row(digits[0:3]), Layout.row(digits[3:6]), Layout.row(digits[6:9])], 'numericCenterColumn'),
            column([Layout.row(['backspaceButton']), Layout.row(['periodButton']), Layout.row(['atButton'])], 'numericSideColumn'),
          ], 'numericTopRow'),
          Layout.row(['symbolicButton', 'pinyinButton', 'zeroButton', 'spaceButton', 'enterButton']),
        ],
        numericTopRow: { size: { height: '3/4' } },
        numericSideColumn: sideWidth,
        numericCenterColumn: { size: { width: '6.3/9.7' } },
        numericOperators: {
          type: 'symbols', maximumRow: 4, dataSource: 'numericOperatorData',
          backgroundStyle: Theme.systemBackgroundName, cellStyle: 'numericOperatorCell',
          insets: insets, displaySeparatorLine: false,
        },
        numericOperatorData: ['+', '-', '*', '/'],
        numericOperatorCell: {
          backgroundStyle: 'numericOperatorHighlight', foregroundStyle: 'numericOperatorLabel',
        },
        numericOperatorHighlight: Style.geometry({ highlightColor: colors.systemButtonHighlightedBackgroundColor }),
        numericOperatorLabel: Style.text({ fontSize: fonts.keyLabel,
          normalColor: colors.standardButtonForegroundColor, highlightColor: colors.standardButtonForegroundColor }),
      },
      Style.merge([
        Button.alphabetic(n, Keys[n] + (if n == 'zeroButton' then middleWidth else {}),
          insets, { size: metrics.hint.iPhoneSize })
        for n in digits
      ]),
      Button.system('backspaceButton', Keys.backspaceButton),
      Button.system('periodButton', { action: { symbol: '.' }, text: '.', fontSize: fonts.keyLabel }),
      Button.system('atButton', Keys.atButton + { fontSize: fonts.keyLabel }),
      Button.system('symbolicButton', Keys.symbolicButton + sideWidth + { text: '符号' }),
      Button.system('pinyinButton', { action: 'returnPrimaryKeyboard', text: '返回' } + middleWidth),
      Button.system('spaceButton', Keys.spaceButton + middleWidth + { text: '空格', foregroundStyle: 'numericSpaceLabel' }),
      { numericSpaceLabel: Style.text({ text: '空格', fontSize: fonts.systemKeyText,
          normalColor: colors.systemButtonForegroundColor, highlightColor: colors.systemButtonForegroundColor }) },
      Phone.enter(sideWidth),
    ]),
}
