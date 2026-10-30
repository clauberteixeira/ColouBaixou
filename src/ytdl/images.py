"""Caixinhas de seleção desenhadas (os símbolos ☐/☑ dependem da fonte e saíam errados)."""

from typing import Literal

from PIL import Image, ImageDraw

CHECK_SIZE = 18
GAP = 8
SCALE = 4  # desenha maior e reduz: bordas suaves
BLUE = (31, 106, 165, 255)
GRAY = (138, 138, 138, 255)
FAINT = (138, 138, 138, 90)
WHITE = (255, 255, 255, 255)
Check = Literal["on", "off", "disabled"]


def checkbox_image(state: Check) -> Image.Image:
    big = CHECK_SIZE * SCALE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = (SCALE, SCALE, big - SCALE - 1, big - SCALE - 1)
    radius = 4 * SCALE
    if state == "on":
        d.rounded_rectangle(box, radius=radius, fill=BLUE)
        d.line([(big * 0.27, big * 0.52), (big * 0.44, big * 0.69), (big * 0.75, big * 0.33)],
               fill=WHITE, width=int(2.4 * SCALE), joint="curve")
    else:
        d.rounded_rectangle(box, radius=radius, outline=GRAY if state == "off" else FAINT,
                            width=int(1.6 * SCALE))
    return img.resize((CHECK_SIZE, CHECK_SIZE), Image.LANCZOS)


def row_image(thumb: Image.Image | None, check: Check | None, thumb_size: tuple[int, int]) -> Image.Image:
    """Caixinha + miniatura numa imagem só (o Treeview aceita uma imagem por linha)."""
    width, height = CHECK_SIZE + GAP + thumb_size[0], thumb_size[1]
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if check:
        box = checkbox_image(check)
        img.alpha_composite(box, (0, (height - CHECK_SIZE) // 2))
    if thumb is not None:
        img.paste(thumb.convert("RGBA").resize(thumb_size), (CHECK_SIZE + GAP, 0))
    return img
