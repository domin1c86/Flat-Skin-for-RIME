// One layout generator, two complete language-specific primary keyboards.
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
  new(isPortrait=true, english=false)::
    local insets = metrics.keyInsets.iPhone[if isPortrait then 'portrait' else 'landscape'];
    local state = if english then 'English' else 'Chinese';
    local hints = if english then Phone.englishLetterHints else Phone.letterHints;
    local key(c, width=Widths.iPhone.unit) =
      local n = name(c);
      local top = n + 'SwipeLabelForegroundStyle';
      local upper = n + 'UppercaseForegroundStyle';
      local lower = n + 'LetterLabelForegroundStyle';
      local painted = Button.alphabetic(n, Keys[n] + width + {
        swipeUpAction: { symbol: hints[c] },
        layers: [
          { name: n + 'SwipeLabel', params: { text: hints[c], fontSize: 9,
              center: { x: 0.5, y: 0.18 }, foregroundNormalColor: colors.swipeHintColor,
              foregroundHighlightColor: colors.swipeHintColor } },
          { name: n + 'LetterLabel', params: { text: c, fontSize: fonts.keyLabel,
              center: { x: 0.5, y: 0.59 } } },
        ],
      }, insets, { size: metrics.hint.iPhoneSize });
      painted + Hold.new(c, hints[c], isPortrait, state) + {
        [n]+: {
          foregroundStyle: [top, if english then lower else upper],
          uppercasedStateForegroundStyle: [top, upper], capsLockedStateForegroundStyle: [top, upper],
          notification: [],
          hintSymbolsGridStyle: n + state + 'HoldGridStyle', hintSymbolsStyle: n + state + 'HoldListStyle',
        },
        [upper]+: { center: { x: 0.5, y: 0.59 } },
        [n + 'HintStyle']+: {
          foregroundStyle: n + (if english then 'LowerHintForegroundStyle' else 'HintForegroundStyle'),
          uppercasedStateForegroundStyle: n + 'HintForegroundStyle',
          capsLockedStateForegroundStyle: n + 'HintForegroundStyle',
          swipeUpForegroundStyle: n + 'SwipeHintForegroundStyle',
        },
        [n + 'LowerHintForegroundStyle']: Style.text({ text: c, fontSize: fonts.hintLabel,
          normalColor: colors.standardCalloutForegroundColor }),
        [n + 'SwipeHintForegroundStyle']: Style.text({ text: hints[c], fontSize: fonts.hintLabel,
          normalColor: colors.standardCalloutForegroundColor }),
      };
    Style.merge([
      Phone.base(isPortrait, mainControls=true, english=english), Hold.shared,
      { keyboardLayout: [
        Layout.row(names('qwertyuiop')), Layout.row(names('asdfghjkl')),
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
      Phone.punctuation(insets, english),
      Button.alphabetic('spaceButton', Keys.spaceButton + { size: { width: '3/10' } }, insets, hint=null),
      Phone.language(Widths.iPhone.unit, english), Phone.enter({ size: { width: '1.5/10' } }),
    ]),
}
