local standard = import 'main.standard.jsonnet';
local Style = import 'Components/Style.libsonnet';
local ContextActions = import 'Components/ContextActions.libsonnet';
local colors = import 'Constants/Colors.libsonnet';
local targets = [
  theme + '/' + layout + orientation + '.yaml'
  for theme in ['light', 'dark']
  for layout in ['pinyin', 'alphabetic']
  for orientation in ['Portrait', 'Landscape']
];
local patch = ContextActions.apply({
  deleteAllProbeGrid: {
    symbolRows: [['deleteAllProbeOption'], ['deleteAllProbeCancel']],
    size: { width: 96, height: 40 },
    spacing: { horizontal: 0, vertical: 0 },
    insets: { top: 4, bottom: 4, left: 4, right: 4 },
    anchor: { row: 1, col: 0 },
    selected: { row: 1, col: 0 },
    offset: { x: 0, y: -48 },
    moveStep: { horizontal: 96, vertical: 40 },
    moveThreshold: 16,
    checkIfOverflowsParentHeight: true,
    backgroundStyle: 'phoneHoldBackground',
    selectedBackgroundStyle: 'phoneHoldSelectedBackground',
  },
  deleteAllProbeOption: {
    type: 'button',
    foregroundStyle: 'deleteAllProbeLabel',
    action: { combine: [{ shortcut: '#重输' }, { shortcut: '#deleteText' }] },
  },
  deleteAllProbeCancel: {
    type: 'button', foregroundStyle: 'deleteAllProbeCancelLabel', action: 'none',
  },
  deleteAllProbeLabel: Style.text({
    text: '删除全部', fontSize: 16,
    normalColor: { light: '#C42B2B', dark: '#FF8585' },
    highlightColor: '#FFFFFF',
  }),
  deleteAllProbeCancelLabel: Style.text({
    text: '取消', fontSize: 16,
    normalColor: colors.standardCalloutForegroundColor,
    highlightColor: '#FFFFFF',
  }),
});
{
  [path]:
    local document = std.parseJson(standard[path]);
    if path == 'config.yaml' then
      std.toString(document + { name: document.name + '·删除全部验证' })
    else if std.member(targets, path) then
      std.toString(document + Style.resolve(patch, std.startsWith(path, 'dark/')) + {
        backspaceButton: {
          [field]: document.backspaceButton[field]
          for field in std.objectFields(document.backspaceButton)
          if field != 'repeatAction'
        } + { hintSymbolsGridStyle: 'deleteAllProbeGrid' },
      })
    else standard[path]
  for path in std.objectFields(standard)
}
