// 原生分类符号列表：左侧滚动分类、锁定、返回，右侧四列五行。
local metrics = import '../Constants/Metrics.libsonnet';
local colors = import '../Constants/Colors.libsonnet';
local fonts = import '../Constants/Fonts.libsonnet';
local Button = import '../Components/Button.libsonnet';
local Layout = import '../Components/Layout.libsonnet';
local Phone = import '../Components/iPhone.libsonnet';
local Style = import '../Components/Style.libsonnet';
local Theme = import '../Components/Theme.libsonnet';
local catalog = import '../Constants/SymbolCatalog.json';
local lockForeground = [
  Style.when('$symbolicKeyboardLockState', false, 'symbolUnlockedIcon'),
  Style.when('$symbolicKeyboardLockState', true, 'symbolLockedIcon'),
];

{
  new(isPortrait=true)::
    local insets = metrics.keyInsets.iPhone[if isPortrait then 'portrait' else 'landscape'];
    Style.merge([
      Phone.base(isPortrait),
      {
        keyboardLayout: [Layout.stack('HStack', [
          Layout.stack('VStack', [
            Layout.row(['symbolCategories'], 'symbolCategoryRows'),
            Layout.row(['symbolLockButton']), Layout.row(['symbolReturnButton']),
          ], 'symbolSidebar'),
          Layout.stack('VStack', [Layout.row(['symbolCollection'])], 'symbolContent'),
        ])],
        symbolSidebar: { size: { width: '1.6/10' } },
        symbolContent: { size: { width: '8.4/10' } },
        symbolCategoryRows: { size: { height: '3/5' } },
        symbolCategories: {
          type: 'classifiedSymbols', maximumRow: 3, dataSource: 'symbolCategoryData',
          backgroundStyle: Theme.systemBackgroundName, cellStyle: 'symbolCategoryCell',
          insets: insets, displaySeparatorLine: false,
        },
        symbolCategoryData: [category.label for category in catalog.categories],
        symbolCollection: {
          type: 'subClassifiedSymbols', maximumRow: 5, maximumColumn: 4,
          insets: insets, backgroundStyle: Theme.alphabeticBackgroundName,
          cellStyle: 'symbolCell', displaySeparatorLine: true, separatorLineColor: colors.separatorColor,
        },
        symbolCategoryCell: { backgroundStyle: 'symbolCategoryHighlight', foregroundStyle: 'symbolCategoryLabel' },
        symbolCategoryHighlight: Style.geometry({
          highlightColor: colors.systemButtonHighlightedBackgroundColor,
          cornerRadius: metrics.key.cornerRadius,
          insets: { top: 2, bottom: 2, left: 3, right: 3 },
        }),
        symbolCategoryLabel: Style.text({ fontSize: fonts.systemKeyText,
          normalColor: colors.systemButtonForegroundColor, highlightColor: colors.systemButtonForegroundColor }),
        symbolCell: { backgroundStyle: 'symbolCellHighlight', foregroundStyle: 'symbolLabel' },
        symbolCellHighlight: Style.geometry({ highlightColor: colors.standardButtonHighlightedBackgroundColor }),
        symbolLabel: Style.text({ fontSize: 20,
          normalColor: colors.standardButtonForegroundColor, highlightColor: colors.standardButtonForegroundColor }),
        symbolShortTextCell: { backgroundStyle: 'symbolCellHighlight', foregroundStyle: 'symbolShortLabel' },
        symbolShortLabel: Style.text({ fontSize: 12,
          normalColor: colors.standardButtonForegroundColor, highlightColor: colors.standardButtonForegroundColor }),
        symbolUnlockedIcon: Style.systemImage({ systemImageName: 'lock.open', fontSize: fonts.systemKeyImage,
          normalColor: colors.systemButtonForegroundColor, highlightColor: colors.systemButtonForegroundColor }),
        symbolLockedIcon: Style.systemImage({ systemImageName: 'lock', fontSize: fonts.systemKeyImage,
          normalColor: colors.blueButtonBackgroundColor, highlightColor: colors.blueButtonBackgroundColor }),
        symbolLockNotification: {
          notificationType: 'keyboardAction', notificationKeyboardAction: 'symbolicKeyboardLockStateToggle',
          backgroundStyle: Theme.systemBackgroundName, foregroundStyle: lockForeground,
          action: 'symbolicKeyboardLockStateToggle',
        },
      } + { [category.label]: [
        if std.length(symbol) > 3 then { label: symbol, value: symbol, styleName: 'symbolShortTextCell' }
        else symbol
        for symbol in category.symbols
      ] for category in catalog.categories },
      Button.system('symbolLockButton', { action: 'symbolicKeyboardLockStateToggle',
        foregroundStyle: lockForeground, notification: ['symbolLockNotification'] }),
      Button.system('symbolReturnButton', { action: 'returnLastKeyboard', text: '返回' }),
    ]),
}
