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
local letterSymbols = import '../Constants/LetterSymbols.json';
local Routes = import 'InputRoutes.libsonnet';

local returnForeground = [
  Style.when('$returnKeyType', [0], 'phoneReturnIcon'),
  Style.when('$returnKeyType', std.range(1, 11), 'phoneReturnText'),
];
local languageForeground = [
  Style.when('rime$ascii_mode', false, 'phoneChineseModeIcon'),
  Style.when('rime$ascii_mode', true, 'phoneEnglishModeIcon'),
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
    [std.stringChars(letterSymbols.letters)[i]]:
      std.stringChars(letterSymbols.chinese)[i]
    for i in std.range(0, 25)
  },
  englishLetterHints: {
    [std.stringChars(letterSymbols.letters)[i]]:
      std.stringChars(letterSymbols.english)[i]
    for i in std.range(0, 25)
  },

  base(isPortrait, mainControls=false, english=null)::
    local iconInsets = if isPortrait then { top: 15.4, bottom: 15.4, left: 6, right: 6 }
      else { top: 9.8, bottom: 9.8, left: 6, right: 6 };
    local languageIcon(state) = Style.fileImage({
      contentMode: 'scaleAspectFit', insets: iconInsets,
      normalImage: { file: 'language', image: state },
      highlightImage: { file: 'language', image: state },
    });
    // 水平按笔画居中，垂直对齐 22.5pt 英文标点的字面位置。
    local punctuationIcon(name) =
      local drop = if name == 'comma' then 28 / 3 else 8.5;
      local padding = if isPortrait then 17 else 10;
      Style.fileImage({
      contentMode: 'scaleAspectFit',
      insets: { top: padding + drop, bottom: padding - drop, left: 3, right: 3 },
      normalImage: { file: 'punctuation', image: name },
      highlightImage: { file: 'punctuation', image: name },
    });
    Style.merge([
    Preedit.new(fontSize=fonts.iPhonePreedit), Toolbar.new(phoneControls=true, mainControls=mainControls,
      schemeAction=if english == null then { shortcut: '#方案切换' } else { keyboardType: 'skinSchemes' }),
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
      // 已确认的整体图标保持相同比例，键帽背景独立适配。
      phoneChineseModeIcon: languageIcon('chinese'),
      phoneEnglishModeIcon: languageIcon('english'),
      phoneAsciiNotification: optionNotification(Theme.systemBackgroundName, languageForeground, Keys.asciiModeButton.action),
      phoneChineseCommaLabel: punctuationIcon('comma'),
      phoneEnglishCommaLabel: text(',', { fontSize: fonts.keyLabel }),
      phoneChinesePeriodLabel: punctuationIcon('period'),
      phoneEnglishPeriodLabel: text('.', { fontSize: fonts.keyLabel }),
      phoneCommaNotification: optionNotification(Theme.alphabeticBackgroundName, commaForeground, { symbol: ',' }),
      phonePeriodNotification: optionNotification(Theme.alphabeticBackgroundName, periodForeground, { symbol: '.' }),
    },
  ]),

  enter(width={}):: Button.system('enterButton', Keys.enterButton + width + {
    backgroundStyle: Theme.blueBackgroundName, foregroundStyle: returnForeground,
    notification: ['phoneReturnTypeNotification', 'phoneReturnPreeditNotification'],
  }),
  language(width, english=null):: Button.system('asciiModeButton', Keys.asciiModeButton + width + (
    if english == null then { foregroundStyle: languageForeground, notification: ['phoneAsciiNotification'] }
    else {
      foregroundStyle: if english then 'phoneEnglishModeIcon' else 'phoneChineseModeIcon',
      notification: [],
      action: Routes.to(if english then Routes.config.defaultChinese else Routes.config.english),
    }
  )),
  punctuation(insets, english=null):: Style.merge([
    Button.alphabetic('chineseCommaButton', Keys.chineseCommaButton + { size: { width: '1/10' },
      foregroundStyle: if english == null then commaForeground else if english then 'phoneEnglishCommaLabel' else 'phoneChineseCommaLabel',
      action: { symbol: if english == true then ',' else '，' },
      notification: if english == null then ['phoneCommaNotification'] else [] }, insets, hint=null),
    Button.alphabetic('chinesePeriodButton', Keys.chinesePeriodButton + { size: { width: '1/10' },
      foregroundStyle: if english == null then periodForeground else if english then 'phoneEnglishPeriodLabel' else 'phoneChinesePeriodLabel',
      action: { symbol: if english == true then '.' else '。' },
      notification: if english == null then ['phonePeriodNotification'] else [] }, insets, hint=null),
  ]),
}
