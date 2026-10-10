// Wrap frontend boundaries once, after labels and bubbles have been generated.
local routes = import '../Constants/InputRoutes.json';
local boundary(a) =
  if std.isString(a) then std.member([
    'enter', 'dismissKeyboard', 'nextKeyboard', 'returnPrimaryKeyboard',
    'returnLastKeyboard', 'moveCursorBackward', 'moveCursorForward',
  ], a)
  else if !std.isObject(a) then false
  else if std.objectHas(a, 'combine') then std.length(std.filter(boundary, a.combine)) > 0
  else std.objectHas(a, 'symbol') || std.objectHas(a, 'keyboardType') ||
       std.objectHas(a, 'switchRimeSchema') ||
       (std.objectHas(a, 'shortcut') && std.member([
         '#showPasteboardView', '#toggleScriptView', '#keyboardMenu', '#方案切换',
         '#行首', '#行尾', '#换行', '#Enter', '#重输',
       ], a.shortcut));
local protect(a) = if boundary(a) then {
  combine: [{ sendKeys: routes.contextCancelKeys }, a, { sendKeys: routes.contextResetKeys }],
} else a;
local walk(v) =
  if std.isArray(v) then [walk(x) for x in v]
  else if std.isObject(v) then {
    [k]: if k != 'notificationKeyboardAction' && (k == 'action' || std.endsWith(k, 'Action'))
         then protect(v[k]) else walk(v[k])
    for k in std.objectFields(v)
  } else v;
{
  apply(doc)::
    local guarded = walk(doc);
    guarded + if std.objectHas(doc, 'spaceButton') then {
      spaceButton+: { notification+: ['skinPredictionSpaceNotification'] },
      skinPredictionSpaceNotification: {
        notificationType: 'rime', rimeNotificationType: 'optionChanged',
        rimeOptionName: 'skin_context_prediction', rimeOptionValue: true,
        backgroundStyle: doc.spaceButton.backgroundStyle,
        foregroundStyle: doc.spaceButton.foregroundStyle,
        action: 'space',
      },
    } else {},
}
