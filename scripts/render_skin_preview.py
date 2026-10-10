"""Render a configuration diagram from compiled skin data (not an iOS screenshot).

Requires Pillow. SF Symbols are approximated with simple vector strokes; all key
geometry, text, layers, colors and collection data come from the generated files.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from build_skin import ROOT, SKIN, layout_rectangles, length, validate_style_reference

SCALE = 3
CONDITIONS = {'$returnKeyType': 0, 'rime$ascii_mode': False, '$symbolicKeyboardLockState': False}


def font(size, text='', weight='regular'):
    cjk = any(ord(char) > 0x2ff for char in text)
    candidates = ([Path('C:/Windows/Fonts/msyhbd.ttc' if weight != 'regular' else 'C:/Windows/Fonts/msyh.ttc')] if cjk else []) + ([Path('C:/Windows/Fonts/segoeuib.ttf')] if weight != 'regular' else []) + [
        Path('C:/Windows/Fonts/segoeui.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), max(1, round(size * SCALE)))
    return ImageFont.load_default()


def selected(value, ascii_mode=False):
    if value is None:
        return []
    validate_style_reference(value, 'preview style reference')
    if isinstance(value, str):
        return [value]
    refs = []
    for item in value or []:
        if isinstance(item, str):
            refs.append(item)
        else:
            match = ascii_mode if item['conditionKey'] == 'rime$ascii_mode' else CONDITIONS.get(item['conditionKey'])
            expected = item['conditionValue']
            if match == expected or isinstance(expected, list) and match in expected:
                refs += [item['styleName']] if isinstance(item['styleName'], str) else item['styleName']
    return refs


def effective_button(doc, node, ascii_mode=False, after_language_change=False):
    """Model initial styles separately from an ascii_mode notification replacement."""
    if not after_language_change:
        return node
    notifications = node.get('notification', [])
    if isinstance(notifications, str):
        notifications = [notifications]
    for ref in notifications:
        replacement = doc[ref]
        if (replacement.get('notificationType') == 'rime'
                and replacement.get('rimeNotificationType') == 'optionChanged'
                and replacement.get('rimeOptionName') == 'ascii_mode'
                and replacement.get('rimeOptionValue') is ascii_mode):
            # Only actions have the documented fallback to the original node.
            actions = {key: value for key, value in node.items() if key == 'action' or key.endswith('Action')}
            return actions | replacement
    return node


def button_foreground(node, shift=False, caps_locked=False):
    if caps_locked and 'capsLockedStateForegroundStyle' in node:
        return node['capsLockedStateForegroundStyle']
    if (shift or caps_locked) and 'uppercasedStateForegroundStyle' in node:
        return node['uppercasedStateForegroundStyle']
    return node.get('foregroundStyle')


def inset(rect, values):
    x, y, w, h = rect
    left, top = values.get('left', 0), values.get('top', 0)
    return (x + left, y + top, max(0, w - left - values.get('right', 0)), max(0, h - top - values.get('bottom', 0)))


def icon(draw, name, center, size, color):
    x, y = center
    unit = size / 24

    def points(coords):
        return [((x + (px - 12) * unit) * SCALE, (y + (py - 12) * unit) * SCALE) for px, py in coords]

    def line(coords):
        draw.line(points(coords), fill=color, width=max(1, round(1.8 * unit * SCALE)), joint='curve')

    def rectangle(coords, radius=2):
        draw.rounded_rectangle(points(coords), radius=radius * unit * SCALE, outline=color, width=max(1, round(1.7 * unit * SCALE)))

    if name.startswith('square.grid'):
        for px, py in ((3, 3), (15, 3), (3, 15), (15, 15)):
            rectangle([(px, py), (px + 6, py + 6)], 1.5)
    elif name == 'face.smiling':
        draw.ellipse(points([(3, 3), (21, 21)]), outline=color, width=max(1, round(1.7 * unit * SCALE)))
        line([(8, 8), (8, 10)]); line([(16, 8), (16, 10)])
        draw.arc(points([(7, 9), (17, 18)]), 10, 170, fill=color, width=max(1, round(1.7 * unit * SCALE)))
    elif name == 'doc.on.doc':
        rectangle([(3, 3), (17, 17)]); rectangle([(7, 7), (21, 21)])
        line([(11, 12), (17, 12)]); line([(11, 16), (17, 16)])
    elif name == 'chevron.left.forwardslash.chevron.right':
        line([(8, 7), (3, 12), (8, 17)]); line([(16, 7), (21, 12), (16, 17)]); line([(14, 4), (10, 20)])
    elif name == 'chevron.down':
        line([(5, 9), (12, 16), (19, 9)])
    elif name == 'number':
        line([(9, 3), (7, 21)]); line([(17, 3), (15, 21)])
        line([(4, 9), (21, 9)]); line([(3, 15), (20, 15)])
    elif name == 'arrow.triangle.2.circlepath':
        draw.arc(points([(3, 3), (21, 21)]), 185, 350, fill=color, width=max(1, round(1.8 * unit * SCALE)))
        draw.arc(points([(3, 3), (21, 21)]), 5, 170, fill=color, width=max(1, round(1.8 * unit * SCALE)))
        line([(17, 7), (21, 12), (23, 7)]); line([(1, 17), (3, 12), (7, 17)])
    elif name.startswith('delete.left'):
        line([(9, 5), (20, 5), (21, 7), (21, 17), (19, 19), (9, 19), (2, 12), (9, 5)])
        line([(11, 9), (17, 15)]); line([(17, 9), (11, 15)])
    elif name.startswith('shift') or name.startswith('capslock'):
        line([(12, 3), (21, 12), (15, 12), (15, 21), (9, 21), (9, 12), (3, 12), (12, 3)])
    elif name == 'arrow.turn.down.left':
        line([(20, 5), (20, 12), (18, 16), (4, 16)]); line([(9, 11), (4, 16), (9, 21)])
    elif name == 'space':
        line([(4, 10), (4, 15), (20, 15), (20, 10)])
    elif name.startswith('lock'):
        rectangle([(5, 10), (19, 21)], 2.5)
        if name == 'lock.open':
            line([(8, 10), (8, 6), (10, 3), (14, 3), (16, 6)])
        else:
            line([(8, 10), (8, 6), (10, 3), (14, 3), (16, 6), (16, 10)])


def render_keyboard(name, scheme, width=390, category='常用', ascii_mode=False, preedit='',
                    shift=False, caps_locked=False, after_language_change=False):
    doc = json.loads((SKIN / scheme / (name + '.yaml')).read_text(encoding='utf-8'))
    if 'symbolCategoryData' in doc and category not in doc['symbolCategoryData']:
        raise ValueError(f'Unknown symbol category: {category}')
    total = doc['preeditHeight'] + doc['toolbarHeight'] + doc['keyboardHeight']
    board = doc['keyboardBackgroundStyle']['normalColor']
    image = Image.new('RGB', (round(width * SCALE), round(total * SCALE)), board)
    draw = ImageDraw.Draw(image)

    def paint(reference, rect, highlighted=False):
        for ref in selected(reference, ascii_mode):
            node = doc[ref]
            x, y, w, h = inset(rect, node.get('insets', {}))
            if node.get('buttonStyleType') == 'fileImage':
                resource = node.get('highlightImage', node['normalImage']) if highlighted else node['normalImage']
                folder = SKIN / scheme / 'resources'
                descriptor = json.loads((folder / (resource['file'] + '.yaml')).read_text(encoding='utf-8'))
                bounds = descriptor[resource['image']]['rect']
                atlas = Image.open(folder / (resource['file'] + '.png')).convert('RGBA')
                tile = atlas.crop((bounds['x'], bounds['y'], bounds['x'] + bounds['width'], bounds['y'] + bounds['height']))
                factor = min(w / tile.width, h / tile.height)
                iw, ih = max(1, round(tile.width * factor * SCALE)), max(1, round(tile.height * factor * SCALE))
                tile = tile.resize((iw, ih), Image.Resampling.LANCZOS)
                image.paste(tile, (round((x + w / 2) * SCALE - iw / 2), round((y + h / 2) * SCALE - ih / 2)), tile)
                continue
            color = node.get('highlightColor', node.get('normalColor')) if highlighted else node.get('normalColor')
            if not color:
                continue
            if node.get('buttonStyleType') == 'geometry':
                draw.rounded_rectangle((x * SCALE, y * SCALE, (x + w) * SCALE, (y + h) * SCALE),
                                       radius=node.get('cornerRadius', 0) * SCALE, fill=color)
            else:
                center = node.get('center', {})
                point = (x + w * center.get('x', .5), y + h * center.get('y', .5))
                size = node.get('fontSize', 16)
                if node.get('buttonStyleType') == 'text':
                    label = node.get('text', '')
                    draw.text((point[0] * SCALE, point[1] * SCALE), label, font=font(size, label, node.get('fontWeight', 'regular')), fill=color, anchor='mm')
                elif node.get('buttonStyleType') == 'systemImage':
                    icon(draw, node['systemImageName'], point, size, color)

    def paint_cell(node, rect):
        node = effective_button(doc, node, ascii_mode, after_language_change)
        bounds = node.get('bounds', {})
        x, y, w, h = rect
        visible_w = length(bounds.get('width'), w)
        visible_h = length(bounds.get('height'), h)
        visible_w = w if visible_w is None else visible_w
        visible_h = h if visible_h is None else visible_h
        alignment = bounds.get('alignment', 'center')
        x += 0 if alignment.startswith('left') else w - visible_w if alignment.startswith('right') else (w - visible_w) / 2
        y += 0 if alignment.endswith('Top') else h - visible_h if alignment.endswith('Bottom') else (h - visible_h) / 2
        rect = (x, y, visible_w, visible_h)
        paint(node.get('backgroundStyle'), rect)
        if node.get('type', 'button') == 'button':
            paint(button_foreground(node, shift, caps_locked), rect)
            return
        if node['type'] == 'subClassifiedSymbols':
            values = doc[category]
            rows, cols = node['maximumRow'], node['maximumColumn']
        elif node['type'] in ('symbols', 'classifiedSymbols'):
            values = doc[node['dataSource']]
            rows, cols = node['maximumRow'], 1
        else:
            return
        x, y, w, h = inset(rect, node.get('insets', {}))
        cell_style = doc[node['cellStyle']]
        foreground = dict(doc[cell_style['foregroundStyle']])
        for i, label in enumerate(values):
            cx, cy = x + (i % cols) * w / cols, y + (i // cols) * h / rows
            label = label if isinstance(label, str) else label['label']
            is_selected = node['type'] == 'classifiedSymbols' and label == category
            paint(cell_style.get('backgroundStyle'), (cx, cy, w / cols, h / rows), highlighted=is_selected)
            if node.get('displaySeparatorLine'):
                separator = node['separatorLineColor']
                if i % cols:
                    draw.line((cx * SCALE, cy * SCALE, cx * SCALE, (cy + h / rows) * SCALE), fill=separator, width=1)
                if i >= cols:
                    draw.line((cx * SCALE, cy * SCALE, (cx + w / cols) * SCALE, cy * SCALE), fill=separator, width=1)
            size = foreground['fontSize']
            draw.text(((cx + w / cols / 2) * SCALE, (cy + h / rows / 2) * SCALE), label,
                      font=font(size, label), fill=foreground.get('highlightColor', foreground['normalColor']) if is_selected else foreground['normalColor'], anchor='mm')

    for field, offset, height, region_style in (
        ('toolbarLayout', doc['preeditHeight'], doc['toolbarHeight'], 'toolbarStyle'),
        ('keyboardLayout', doc['preeditHeight'] + doc['toolbarHeight'], doc['keyboardHeight'], 'keyboardStyle'),
    ):
        left, top, w, h = inset((0, offset, width, height), doc[region_style].get('insets', {}))
        for cell, (x, y, rw, rh) in layout_rectangles(doc, field, w, h):
            paint_cell(doc[cell], (left + x, top + y, rw, rh))
    if preedit:
        node = doc[selected(doc['preeditStyle']['foregroundStyle'], ascii_mode)[-1]]
        x = doc['preeditStyle'].get('insets', {}).get('left', 0)
        draw.text((x * SCALE, doc['preeditHeight'] / 2 * SCALE), preedit,
                  font=font(node['fontSize'], preedit), fill=node.get('normalColor', '#000000'), anchor='lm')
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=SKIN / 'demo.png')
    parser.add_argument('--category', choices=('常用', '中文', '英文'), default='常用', help='selected category shown in the symbol diagram')
    parser.add_argument('--language-states', action='store_true', help='compare Chinese, English and English Shift after language notifications')
    args = parser.parse_args()
    gap, margin, title_height = 18, 24, 52
    board_width, board_height = 390, 281
    image = Image.new('RGB', ((3 * board_width + 2 * gap + 2 * margin) * SCALE,
                              (2 * (board_height + 36) + title_height + 2 * margin) * SCALE), '#f7f7f5')
    draw = ImageDraw.Draw(image)
    title = '字母显示修复 · iPhone' if args.language_states else '扁平灰白 · iPhone'
    draw.text((margin * SCALE, margin * SCALE), title, font=font(23, title), fill='#242725')
    draw.text(((margin + 850) * SCALE, (margin + 9) * SCALE), '配置示意 · 非实机截图', font=font(12, '配置示意'), fill='#747974')
    for row, scheme in enumerate(('light', 'dark')):
        scenes = (('pinyinPortrait', '中文 / 切回后'), ('pinyinPortrait', '英文 / 切换后'),
                  ('pinyinPortrait', '英文 Shift')) if args.language_states else (
                      ('pinyinPortrait', '主界面'), ('numericPortrait', '数字'), ('symbolicPortrait', '符号'))
        for column, (name, label) in enumerate(scenes):
            x, y = margin + column * (board_width + gap), margin + title_height + row * (board_height + 36)
            draw.text((x * SCALE, y * SCALE), label + (' / 浅色' if row == 0 else ' / 深色'), font=font(13, label), fill='#747974')
            image.paste(render_keyboard(name, scheme, category=args.category,
                                        preedit='jian dan de' if name == 'pinyinPortrait' and (not args.language_states or column == 0) else '',
                                        ascii_mode=args.language_states and column > 0,
                                        shift=args.language_states and column == 2,
                                        after_language_change=args.language_states), (x * SCALE, (y + 26) * SCALE))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, optimize=True)
    print(f'Rendered configuration diagram: {args.output}')


if __name__ == '__main__':
    main()
