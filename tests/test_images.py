from PIL import Image

from ytdl.images import CHECK_SIZE, GAP, checkbox_image, row_image


def test_checked_box_is_filled_and_unchecked_is_hollow():
    on, off = checkbox_image("on"), checkbox_image("off")
    assert on.size == off.size == (CHECK_SIZE, CHECK_SIZE)
    corner = (3, CHECK_SIZE // 2)  # perto da borda esquerda, fora do "✓"
    assert on.getpixel(corner)[3] >= 250   # preenchida (borda suavizada)
    assert off.getpixel(corner)[3] == 0    # vazada por dentro
    assert off.getpixel((1, CHECK_SIZE // 2))[3] > 0  # mas tem contorno


def test_row_image_layout():
    thumb = Image.new("RGB", (64, 36), "red")
    img = row_image(thumb, "on", (64, 36))
    assert img.size == (CHECK_SIZE + GAP + 64, 36)
    assert img.getpixel((CHECK_SIZE + GAP + 10, 10))[:3] == (255, 0, 0)


def test_row_image_without_checkbox_keeps_alignment():
    img = row_image(None, None, (64, 36))
    assert img.size == (CHECK_SIZE + GAP + 64, 36)
    assert img.getpixel((5, 18))[3] == 0  # espaço da caixinha vazio
