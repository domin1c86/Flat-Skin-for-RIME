// iPhone 主键盘：26 键 + 数字/符号上划；横竖屏共用键位。
local Keys = import '../Constants/Keys.libsonnet';
local colors = import '../Constants/Colors.libsonnet';
local fonts = import '../Constants/Fonts.libsonnet';
local metrics = import '../Constants/Metrics.libsonnet';
local Button = import '../Components/Button.libsonnet';
local Layout = import '../Components/Layout.libsonnet';
local Phone = import '../Components/iPhone.libsonnet';
local Hold = import '../Components/iPhoneHold.libsonnet';
local Style = import '../Components/Style.libsonnet';
local Theme = import '../Components/Theme.libsonnet';
local Widths = import '../Components/Widths.libsonnet';
local name(c) = c + 'Button';
local names(row) = [name(c) for c in std.stringChars(row)];

{
  new(isPortrait=true)::
    local insets = metrics.keyInsets.iPhone[if isPortrait then 'portrait' else 'landscape'];
    local key(c, width=Widths.iPhone.unit) =
      local n = name(c);
      local topName = n + 'SwipeLabel';
      local bottomName = n + 'LetterLabel';
      local upperName = n + 'UppercaseForegroundStyle';
      local chineseForeground = [topName + 'ForegroundStyle', upperName];
      local normalForeground = [
        topName + 'ForegroundStyle',
        Style.when('rime$ascii_mode', false, upperName),
        Style.when('rime$ascii_mode', true, bottomName + 'ForegroundStyle'),
      ];
      Button.alphabetic(n, Keys[n] + width + {
        swipeUpAction: if std.count(std.stringChars('qwertyuiop'), c) > 0
          then { character: Phone.letterHints[c] } else { symbol: Phone.letterHints[c] },
        layers: [
          { name: topName, params: { text: Phone.letterHints[c], fontSize: 9, center: { y: 0.18 },
              foregroundNormalColor: colors.swipeHintColor, foregroundHighlightColor: colors.swipeHintColor } },
          { name: bottomName, params: { text: c, fontSize: fonts.keyLabel, center: { y: 0.59 } } },
        ],
      }, insets, { size: metrics.hint.iPhoneSize }) + Hold.new(c, Phone.letterHints[c], isPortrait) + {
        [n]+: {
          foregroundStyle: normalForeground,
          uppercasedStateForegroundStyle: chineseForeground,
          notification: [n + 'ChineseLabelNotification'],
          hintSymbolsGridStyle: n + 'HoldGridStyle', hintSymbolsStyle: n + 'HoldListStyle',
        },
        [n + 'ChineseLabelNotification']: {
          notificationType: 'rime', rimeNotificationType: 'optionChanged',
          rimeOptionName: 'ascii_mode', rimeOptionValue: false,
          backgroundStyle: Theme.alphabeticBackgroundName, foregroundStyle: chineseForeground,
          hintSymbolsGridStyle: n + 'HoldGridStyle', hintSymbolsStyle: n + 'HoldListStyle',
        },
        [upperName]+: { center: { y: 0.59 } },
        // 上划气泡需要独立前景，否则会继续显示普通按键的字母。
        [n + 'HintStyle']+: { swipeUpForegroundStyle: n + 'SwipeHintForegroundStyle' },
        [n + 'SwipeHintForegroundStyle']: Style.text({
          text: Phone.letterHints[c], fontSize: fonts.hintLabel,
          normalColor: colors.standardCalloutForegroundColor,
        }),
      };
    Style.merge([
      Phone.base(isPortrait, mainControls=true),
      Hold.shared,
      { keyboardLayout: [
        Layout.row(names('qwertyuiop')),
        Layout.row(names('asdfghjkl')),
        Layout.row(['shiftButton'] + names('zxcvbnm') + ['backspaceButton']),
        Layout.row(['symbolicButton', 'numericButton', 'chineseCommaButton', 'spaceButton',
                    'chinesePeriodButton', 'asciiModeButton', 'enterButton']),
      ] },
      Style.merge([key(c) for c in std.stringChars('qwertyuiopsdfghjkzxcvbnm')]),
      key('a', Widths.iPhone.homeRowLeft), key('l', Widths.iPhone.homeRowRight),
      Button.system('shiftButton', Keys.shiftButton + Widths.iPhone.sideLeft + {
        uppercasedStateForegroundStyle: Theme.shiftUppercasedForegroundName,
        capsLockedStateForegroundStyle: Theme.shiftCapsLockedForegroundName,
      }),
      Button.system('backspaceButton', Keys.backspaceButton + Widths.iPhone.sideRight),
      Button.system('symbolicButton', Keys.symbolicButton + { text: '符号', size: { width: '1.5/10' } }),
      Button.system('numericButton', Keys.numericButton + Widths.iPhone.unit),
      Phone.punctuation(insets),
      Button.alphabetic('spaceButton', Keys.spaceButton + { size: { width: '3/10' } }, insets, hint=null),
      Phone.language(Widths.iPhone.unit),
      Phone.enter({ size: { width: '1.5/10' } }),
    ]),
}
