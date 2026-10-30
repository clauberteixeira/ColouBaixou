"""Gera assets/icon.ico (quadrado vermelho arredondado com seta de download)."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "assets" / "icon.ico"
SIZE = 256


def draw() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=56, fill=(217, 48, 37, 255))
    white = (255, 255, 255, 255)
    d.rectangle((108, 52, 148, 138), fill=white)                    # haste da seta
    d.polygon([(64, 128), (192, 128), (128, 192)], fill=white)      # ponta da seta
    d.rounded_rectangle((60, 204, 196, 222), radius=9, fill=white)  # base ("bandeja")
    return img


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    draw().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(OUT)
