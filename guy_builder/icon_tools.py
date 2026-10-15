"""Conversão PNG -> ICO (multi-resolução, preservando transparência). Pillow é importado sob demanda."""
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

from .config import ICO_SIZES


@dataclass
class ImageInfo:
    path: Path
    width: int
    height: int
    format: str
    mode: str
    file_size: int
    has_alpha: bool


@dataclass
class IcoResult:
    data: bytes
    sizes: List[int]
    warnings: List[str] = field(default_factory=list)


def is_valid_ico(path) -> bool:
    """Checagem leve do cabeçalho (sem Pillow): reservado=0, tipo=1 (ícone), ao menos 1 imagem."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(6)
    except OSError:
        return False
    return len(head) == 6 and head[:4] == b"\x00\x00\x01\x00" and int.from_bytes(head[4:6], "little") > 0


def _lanczos():
    from PIL import Image
    return getattr(Image, "Resampling", Image).LANCZOS


def read_image_info(path) -> ImageInfo:
    from PIL import Image
    path = Path(path)
    with Image.open(path) as im:
        has_alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
        return ImageInfo(path, im.width, im.height, im.format or path.suffix.lstrip(".").upper(),
                         im.mode, path.stat().st_size, has_alpha)


def load_rgba(path):
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        return im.convert("RGBA")


def build_ico_bytes(source, sizes: Sequence[int] = ICO_SIZES) -> IcoResult:
    """Gera o .ico em memória (permite pré-visualizar antes de salvar)."""
    from PIL import Image
    sizes = sorted({int(s) for s in sizes})
    if not sizes or sizes[0] < 1 or sizes[-1] > 256:
        raise ValueError("Tamanhos de ícone devem estar entre 1 e 256.")
    img = source.convert("RGBA") if hasattr(source, "convert") else load_rgba(source)
    warnings: List[str] = []

    w, h = img.size
    if w != h:
        side = max(w, h)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(img, ((side - w) // 2, (side - h) // 2))
        img = canvas
        warnings.append(f"A imagem não é quadrada ({w}×{h}); foi centralizada em um quadro transparente "
                        f"{side}×{side} para não distorcer.")
    largest = sizes[-1]
    if img.width < largest:
        warnings.append(f"A imagem tem {img.width}px, menos que {largest}px; foi ampliada e os tamanhos "
                        f"grandes terão menos nitidez. Use um PNG de pelo menos {largest}×{largest}.")
        img = img.resize((largest, largest), _lanczos())

    buf = io.BytesIO()
    img.save(buf, format="ICO", sizes=[(s, s) for s in sizes])
    data = buf.getvalue()
    stored = read_ico_sizes(data)
    missing = [s for s in sizes if s not in stored]
    if missing:
        warnings.append("Tamanhos não gravados pela biblioteca: " + ", ".join(map(str, missing)))
    return IcoResult(data=data, sizes=stored, warnings=warnings)


def read_ico_sizes(source) -> List[int]:
    from PIL import Image
    handle = io.BytesIO(source) if isinstance(source, (bytes, bytearray)) else source
    with Image.open(handle) as ico:
        return sorted({s[0] for s in ico.info.get("sizes", {ico.size})})
