local routes = import '../Constants/InputRoutes.json';
{
  config: routes,
  toggle(english):: { combine: [
    { keyboardType: if english then 'pinyin' else 'alphabetic' },
    { sendKeys: routes.toggleKeys },
  ] },
  to(id):: { combine: [
    { keyboardType: if id == routes.english then 'alphabetic' else 'pinyin' },
    { switchRimeSchema: id },
  ] },
}
