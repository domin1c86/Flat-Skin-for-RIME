local routes = import '../Constants/InputRoutes.json';
{
  config: routes,
  to(id):: { combine: [
    { keyboardType: if id == routes.english then 'alphabetic' else 'pinyin' },
    { switchRimeSchema: id },
  ] },
}
