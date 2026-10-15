"""Pré-visualização de imagens/ícones sobre fundo xadrez (mostra a transparência)."""
import io
from typing import List, Tuple

from .icon_tools import _lanczos

CHECK_A, CHECK_B = (62, 38, 61), (42, 24, 41)


def checkerboard(size: Tuple[int, int], cell: int = 8):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", size, CHECK_A)
    draw = ImageDraw.Draw(img)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle([x, y, x + cell - 1, y + cell - 1], fill=CHECK_B)
    return img


def fit_on_checker(image, box: Tuple[int, int] = (300, 300)):
    from PIL import Image
    img = image.convert("RGBA").copy()
    img.thumbnail(box, _lanczos())
    canvas = checkerboard(box)
    canvas.paste(img, ((box[0] - img.width) // 2, (box[1] - img.height) // 2), img)
    return canvas


def ico_frames(source) -> List[tuple]:
    """Retorna [(tamanho, imagem RGBA)] de cada resolução contida no .ico (bytes ou caminho)."""
    from PIL import Image
    handle = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    frames = []
    with Image.open(handle) as ico:
        for size in sorted(ico.info.get("sizes", {ico.size})):
            ico.size = size
            ico.load()
            frames.append((size[0], ico.convert("RGBA").copy()))
    return frames


def ico_strip(source, height: int = 280, pad: int = 12):
    """Todas as resoluções do .ico lado a lado, em tamanho real (pixels), sobre xadrez."""
    frames = ico_frames(source)
    width = sum(f[0] for f in frames) + pad * (len(frames) + 1)
    canvas = checkerboard((max(width, 120), height))
    x = pad
    for size, frame in frames:
        canvas.paste(frame, (x, height - size - pad), frame)
        x += size + pad
    return canvas
