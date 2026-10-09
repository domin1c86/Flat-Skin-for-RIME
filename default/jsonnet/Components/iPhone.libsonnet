// iPhone 三个页面共用的状态与样式，不改变 iPad 的按键动作。
local Button = import 'Button.libsonnet';
local Style = import 'Style.libsonnet';
local Theme = import 'Theme.libsonnet';
local Preedit = import 'Preedit.libsonnet';
local Toolbar = import 'Toolbar.libsonnet';
local colors = import '../Constants/Colors.libsonnet';
local metrics = import '../Constants/Metrics.libsonnet';
local fonts = import '../Constants/Fonts.libsonnet';
local Keys = import '../Constants/Keys.libsonnet';

local returnForeground = [
  Style.when('$returnKeyType', [0], 'phoneReturnIcon'),
  Style.when('$returnKeyType', std.range(1, 11), 'phoneReturnText'),
];
local languageForeground = [
  Style.when('rime$ascii_mode', false, ['phoneChineseLabel', 'phoneInactiveEnglishLabel', 'phoneLanguageDivider']),
  Style.when('rime$ascii_mode', true, ['phoneInactiveChineseLabel', 'phoneEnglishLabel', 'phoneLanguageDivider']),
];
local commaForeground = [
  Style.when('rime$ascii_mode', false, 'phoneChineseCommaLabel'),
  Style.when('rime$ascii_mode', true, 'phoneEnglishCommaLabel'),
];
local periodForeground = [
  Style.when('rime$ascii_mode', false, 'phoneChinesePeriodLabel'),
  Style.when('rime$ascii_mode', true, 'phoneEnglishPeriodLabel'),
];

local optionNotification(background, foreground, action) = {
  notificationType: 'rime', rimeNotificationType: 'optionChanged',
  rimeOptionName: 'ascii_mode', rimeOptionValue: true,
  backgroundStyle: background, foregroundStyle: foreground, action: action,
};
local text(label, extra={}) = Style.text({
  text: label, fontSize: fonts.systemKeyText,
  normalColor: colors.standardButtonForegroundColor,
  highlightColor: colors.standardButtonHighlightedForegroundColor,
} + extra);

{
  // 上标顺序与三张参考图、HTML 预览一致。
  letterHints: {
    [std.stringChars('qwertyuiopasdfghjklzxcvbnm')[i]]:
      std.stringChars('1234567890~!@#%“”*?()-_:;`')[i]
    for i in std.range(0, 25)
  },

  base(isPortrait, mainControls=false):: Style.merge([
    Preedit.new(), Toolbar.new(phoneControls=true, mainControls=mainControls),
    Theme.shared(metrics.keyInsets.iPhone[if isPortrait then 'portrait' else 'landscape']),
    {
      keyboardHeight: metrics.keyboardHeight.iPhone[if isPortrait then 'portrait' else 'landscape'],
      keyboardStyle: { backgroundStyle: Theme.keyboardBackgroundName },
      phoneReturnIcon: Style.systemImage({
        systemImageName: 'arrow.turn.down.left', fontSize: fonts.systemKeyImage,
        normalColor: colors.blueButtonForegroundColor, highlightColor: colors.blueButtonForegroundColor,
      }),
      phoneReturnText: text('$returnKeyType', {
        normalColor: colors.blueButtonForegroundColor, highlightColor: colors.blueButtonForegroundColor,
      }),
      phoneReturnTypeNotification: {
        notificationType: 'returnKeyType', returnKeyType: std.range(0, 11),
        backgroundStyle: Theme.blueBackgroundName, foregroundStyle: returnForeground,
        action: 'enter',
      },
      phoneReturnPreeditNotification: {
        notificationType: 'preeditChanged',
        backgroundStyle: Theme.blueBackgroundName, foregroundStyle: returnForeground,
        action: 'enter',
      },
      phoneChineseLabel: text('中', { fontSize: 12, center: { x: 0.28, y: 0.32 } }),
      phoneInactiveChineseLabel: text('中', { fontSize: 12, center: { x: 0.28, y: 0.32 },
        normalColor: colors.swipeHintColor, highlightColor: colors.swipeHintColor }),
      phoneEnglishLabel: text('A', { fontSize: 14, center: { x: 0.74, y: 0.70 },
        normalColor: colors.blueButtonBackgroundColor, highlightColor: colors.blueButtonBackgroundColor }),
      phoneInactiveEnglishLabel: text('A', { fontSize: 14, center: { x: 0.74, y: 0.70 },
        normalColor: colors.swipeHintColor, highlightColor: colors.swipeHintColor }),
      // 独立斜线前景层，居中且短于键帽高度，两端留白。
      phoneLanguageDivider: text('/', { fontSize: 36, fontWeight: 'semibold', center: { x: 0.51, y: 0.5 },
        normalColor: colors.swipeHintColor, highlightColor: colors.swipeHintColor }),
      phoneAsciiNotification: optionNotification(Theme.systemBackgroundName, languageForeground, Keys.asciiModeButton.action),
      phoneChineseCommaLabel: text('，', { fontSize: fonts.keyLabel }),
      phoneEnglishCommaLabel: text(',', { fontSize: fonts.keyLabel }),
      phoneChinesePeriodLabel: text('。', { fontSize: fonts.keyLabel }),
      phoneEnglishPeriodLabel: text('.', { fontSize: fonts.keyLabel }),
      phoneCommaNotification: optionNotification(Theme.alphabeticBackgroundName, commaForeground, { symbol: ',' }),
      phonePeriodNotification: optionNotification(Theme.alphabeticBackgroundName, periodForeground, { symbol: '.' }),
    },
  ]),

  enter(width={}):: Button.system('enterButton', Keys.enterButton + width + {
    backgroundStyle: Theme.blueBackgroundName, foregroundStyle: returnForeground,
    notification: ['phoneReturnTypeNotification', 'phoneReturnPreeditNotification'],
  }),
  language(width):: Button.system('asciiModeButton', Keys.asciiModeButton + width + {
    foregroundStyle: languageForeground, notification: ['phoneAsciiNotification'],
  }),
  punctuation(insets):: Style.merge([
    Button.alphabetic('chineseCommaButton', Keys.chineseCommaButton + { size: { width: '1/10' },
      foregroundStyle: commaForeground, notification: ['phoneCommaNotification'] }, insets, hint=null),
    Button.alphabetic('chinesePeriodButton', Keys.chinesePeriodButton + { size: { width: '1/10' },
      foregroundStyle: periodForeground, notification: ['phonePeriodNotification'] }, insets, hint=null),
  ]),
}
