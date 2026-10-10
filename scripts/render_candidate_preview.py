"""Render English candidate-switch configuration diagrams, not iOS screenshots."""
from PIL import Image, ImageDraw
from build_skin import ROOT
from render_skin_preview import SCALE, font, render_keyboard
from render_hold_preview import render_hold


def main():
    margin, gap, column_width = 24, 18, 680
    scenes = []
    for theme in ('light', 'dark'):
        for orientation, width in (('Portrait', 390), ('Landscape', 680)):
            images = [render_keyboard('alphabetic' + orientation, theme, width,
                        english_candidates_enabled=enabled, after_language_change=True)
                      for enabled in (True, False)]
            images.append(render_hold('comma', theme, orientation, width, ascii_mode=True,
                button_name='chineseCommaButton'))
            scenes.append((theme, orientation, images))
    height = 2 * margin + 45 + sum(images[0].height / SCALE + 34 for _, _, images in scenes)
    result = Image.new('RGB', (round((2*margin + 3*column_width + 2*gap)*SCALE), round(height*SCALE)), '#F7F7F5')
    draw = ImageDraw.Draw(result)
    draw.text((margin*SCALE, margin*SCALE), '英文词库候选开关 · 配置示意，非实机截图', font=font(18, '英文词库'), fill='#242725')
    y = margin + 45
    for theme, orientation, images in scenes:
        for index, (label, image) in enumerate(zip(('候选开启 · 蓝色「词」', '候选关闭 · 灰色「词」', '长按 · 松手切换一次'), images)):
            x = margin + index * (column_width + gap)
            title = label + (' / 浅色' if theme == 'light' else ' / 深色') + (' / 竖屏' if orientation == 'Portrait' else ' / 横屏')
            draw.text((x*SCALE, y*SCALE), title, font=font(12, title), fill='#747974')
            result.paste(image, (round((x+(column_width-image.width/SCALE)/2)*SCALE), round((y+24)*SCALE)))
        y += images[0].height/SCALE + 34
    output = ROOT / 'dist/英文词库候选开关配置示意.png'
    output.parent.mkdir(exist_ok=True)
    result.save(output, optimize=True)
    print('Rendered:', output)


if __name__ == '__main__':
    main()
