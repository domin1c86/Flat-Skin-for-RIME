"""Render native hold-grid configuration diagrams, not iOS gesture screenshots."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from build_skin import SKIN, ROOT, layout_rectangles, length
from render_skin_preview import SCALE, font, inset, render_keyboard, effective_button


def hold_geometry(doc, letter, width, ascii_mode=False):
    key = effective_button(doc, doc[letter + 'Button'], ascii_mode, True)
    rect = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))[letter + 'Button']
    x, y, w, h = rect
    bounds = key.get('bounds', {})
    visible = length(bounds.get('width'), w)
    if visible is not None:
        x += w - visible if bounds.get('alignment') == 'right' else 0
        w = visible
    grid = doc[key['hintSymbolsGridStyle']]
    cell_w = length(grid['size']['width'], w)
    cell_h = length(grid['size']['height'], h)
    padding = grid['insets']
    panel_w = 3 * cell_w + padding['left'] + padding['right']
    panel_h = cell_h + padding['top'] + padding['bottom']
    panel_x = x + w / 2 - padding['left'] - (grid['anchor']['col'] + .5) * cell_w
    panel_y = y + doc['preeditHeight'] + doc['toolbarHeight'] + h / 2 + grid['offset']['y'] - cell_h / 2 - padding['top']
    # Mirror documented parent-bound overflow protection.
    panel_x = min(max(0, panel_x), width - panel_w)
    panel_y = max(0, panel_y)
    return grid, (panel_x, panel_y, panel_w, panel_h), (cell_w, cell_h)


def render_hold(letter, scheme, orientation='Portrait', width=390, ascii_mode=False):
    name = ('alphabetic' if ascii_mode else 'pinyin') + orientation
    doc = json.loads((SKIN / scheme / (name + '.yaml')).read_text(encoding='utf-8'))
    image = render_keyboard(name, scheme, width, preedit='' if ascii_mode else '12pt 拼音预编辑示意',
                            ascii_mode=ascii_mode, after_language_change=True).convert('RGBA')
    grid, rect, cell_size = hold_geometry(doc, letter, width, ascii_mode)
    x, y, w, h = rect
    background = doc[grid['backgroundStyle']]
    shadow = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(shadow)
    offset = background['shadowOffset']
    draw.rounded_rectangle(((x+offset['x'])*SCALE,(y+offset['y'])*SCALE,(x+w+offset['x'])*SCALE,(y+h+offset['y'])*SCALE),
                           radius=background['cornerRadius']*SCALE,fill=(0,0,0,round(255*background['shadowOpacity'])))
    image = Image.alpha_composite(image, shadow.filter(ImageFilter.GaussianBlur(background['shadowRadius']*SCALE)))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((x*SCALE,y*SCALE,(x+w)*SCALE,(y+h)*SCALE), radius=background['cornerRadius']*SCALE,fill=background['normalColor'])
    cell_w, cell_h = cell_size
    for column, ref in enumerate(grid['symbolRows'][0]):
        cx = x + grid['insets']['left'] + column*cell_w
        cy = y + grid['insets']['top']
        selected = column == grid['selected']['col']
        foreground = doc[doc[ref]['foregroundStyle']]
        if selected:
            highlight = doc[grid['selectedBackgroundStyle']]
            draw.rounded_rectangle((cx*SCALE,cy*SCALE,(cx+cell_w)*SCALE,(cy+cell_h)*SCALE),radius=highlight['cornerRadius']*SCALE,fill=highlight['normalColor'])
        draw.text(((cx+cell_w/2)*SCALE,(cy+cell_h/2)*SCALE),foreground['text'],font=font(foreground['fontSize'],foreground['text']),
                  fill=foreground['highlightColor'] if selected else foreground['normalColor'],anchor='mm')
    return image.convert('RGB')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/长按气泡配置示意.png')
    parser.add_argument('--language-states', action='store_true', help='compare Chinese and English symbol options')
    args = parser.parse_args()
    margin, gap, width, height = 20, 16, 390, 281
    scenes = [(scheme, english) for scheme in ('light', 'dark') for english in ((False, True) if args.language_states else (False,))]
    result=Image.new('RGB',((margin*2+width*3+gap*2)*SCALE,(margin*2+50+len(scenes)*(height+32))*SCALE),'#F7F7F5')
    draw=ImageDraw.Draw(result)
    draw.text((margin*SCALE,margin*SCALE),'原生配置示意 · 默认选择上标 · 非实机截图',font=font(18,'原生配置示意'),fill='#242725')
    for row, (scheme, english) in enumerate(scenes):
        for col, (letter,label) in enumerate((('q','左缘 Q'),('f','常规 F'),('p','右缘 P'))):
            x=margin+col*(width+gap); y=margin+50+row*(height+32)
            draw.text((x*SCALE,y*SCALE),label+(' / 英文' if english else ' / 中文')+(' / 浅色' if scheme=='light' else ' / 深色'),font=font(12,label),fill='#747974')
            result.paste(render_hold(letter,scheme,ascii_mode=english),(x*SCALE,(y+24)*SCALE))
    args.output.parent.mkdir(parents=True,exist_ok=True);result.save(args.output)
    print('Rendered:',args.output)


if __name__ == '__main__':
    main()
