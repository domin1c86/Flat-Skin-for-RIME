"""Render short/swipe callouts from native configuration; not an iOS screenshot."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
from build_skin import ROOT, SKIN, layout_rectangles, length
from render_skin_preview import SCALE, font, selected, effective_button, button_foreground, render_keyboard


def callout_foreground(doc, letter, english=False, shift=False, caps=False, swipe=False, notified=False):
    key = effective_button(doc, doc[letter + 'Button'], english, notified)
    hint = doc[key['hintStyle']]
    reference = hint['swipeUpForegroundStyle'] if swipe else button_foreground(hint, shift, caps)
    return hint, doc[selected(reference, english)[0]]


def render_callout(letter, scheme, english=False, shift=False, caps=False, swipe=False,
                   orientation='Portrait', width=390):
    name = 'pinyin' + orientation
    doc = json.loads((SKIN / scheme / (name + '.yaml')).read_text(encoding='utf-8'))
    image = render_keyboard(name, scheme, width, ascii_mode=english, shift=shift, caps_locked=caps,
                            after_language_change=True)
    hint, foreground = callout_foreground(doc, letter, english, shift, caps, swipe, True)
    key = effective_button(doc, doc[letter + 'Button'], english, True)
    x, y, w, h = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))[letter + 'Button']
    bounds = key.get('bounds', {})
    visible = length(bounds.get('width'), w)
    if visible is not None:
        x += w - visible if bounds.get('alignment') == 'right' else (0 if bounds.get('alignment') == 'left' else (w-visible)/2)
        w = visible
    pw, ph = hint['size']['width'], hint['size']['height']
    px = min(max(0, x + w / 2 - pw / 2), width - pw)
    py = max(0, y + doc['preeditHeight'] + doc['toolbarHeight'] - ph - 2)
    background = doc[hint['backgroundStyle']]
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((px*SCALE, py*SCALE, (px+pw)*SCALE, (py+ph)*SCALE),
                           radius=background['cornerRadius']*SCALE, fill=background['normalColor'],
                           outline=background['normalBorderColor'], width=max(1, round(background['borderSize']*SCALE)))
    draw.text(((px+pw/2)*SCALE, (py+ph/2)*SCALE), foreground['text'],
              font=font(foreground['fontSize'], foreground['text']), fill=foreground['normalColor'], anchor='mm')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'dist/气泡大小写与符号示意.png')
    args = parser.parse_args()
    width, height, margin, gap = 390, 281, 24, 18
    scenes = [('中文短按 F', False, False, False), ('英文短按 f', True, False, False),
              ('英文 Shift F', True, True, False), ('中文上滑 ＃', False, False, True),
              ('英文上滑 #', True, False, True), ('英文 Shift 上滑 #', True, True, True)]
    image = Image.new('RGB', ((2*margin+3*width+2*gap)*SCALE, (2*margin+46+4*(height+32))*SCALE), '#f7f7f5')
    draw = ImageDraw.Draw(image)
    title = '普通气泡与上滑 · 配置示意，非实机截图'
    draw.text((margin*SCALE, margin*SCALE), title, font=font(18, title), fill='#242725')
    for scheme_index, scheme in enumerate(('light', 'dark')):
        for i, (label, english, shift, swipe) in enumerate(scenes):
            row, col = scheme_index*2+i//3, i%3
            x, y = margin+col*(width+gap), margin+46+row*(height+32)
            draw.text((x*SCALE, y*SCALE), label+(' / 浅色' if scheme=='light' else ' / 深色'), font=font(12, label), fill='#747974')
            image.paste(render_callout('f', scheme, english, shift, swipe=swipe), (x*SCALE, (y+24)*SCALE))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, optimize=True)
    print('Rendered:', args.output)


if __name__ == '__main__':
    main()
