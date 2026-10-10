// Select keyboard type and RIME schema together, without option-state guessing.
local Phone = import '../Components/iPhone.libsonnet';
local Routes = import '../Components/InputRoutes.libsonnet';
local Button = import '../Components/Button.libsonnet';
local Layout = import '../Components/Layout.libsonnet';
local Style = import '../Components/Style.libsonnet';
{
  new(isPortrait=true):: Style.merge([
    Phone.base(isPortrait),
    { keyboardLayout: [Layout.row(['scheme' + item.id]) for item in Routes.config.schemes]
        + [Layout.row(['schemeBack'])] },
    Style.merge([Button.system('scheme' + item.id, {
      text: item.label, action: Routes.to(item.id), fontSize: if isPortrait then 17 else 15,
    }) for item in Routes.config.schemes]),
    Button.system('schemeBack', { text: '返回', action: 'returnLastKeyboard' }),
  ]),
}
