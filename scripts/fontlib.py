"""Shared local font discovery; no downloads or bundled font licenses."""
import os
from pathlib import Path

try:
    from PIL import ImageFont
except ImportError:
    ImageFont = None


def _candidates(mono=False):
    override = os.environ.get("DRAW_FONT")
    if override:
        yield Path(override).expanduser()
        yield Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / override
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = ["consola.ttf", "cour.ttf"] if mono else [
        "msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf",
    ]
    for name in names:
        yield windows / name
    if not mono:
        for path in (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
        ):
            yield Path(path)
    family = "DejaVuSansMono.ttf" if mono else "DejaVuSans.ttf"
    yield Path("/usr/share/fonts/truetype/dejavu") / family
    yield Path("/Library/Fonts/Arial.ttf")
    yield Path(family)  # Pillow/FreeType's own search path


def find_font(size, mono=False):
    if ImageFont is None:
        return None
    for path in _candidates(mono):
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def find_cjk_font():
    """Return a likely CJK font path; DRAW_FONT is the user's explicit choice."""
    override = os.environ.get("DRAW_FONT")
    for path in _candidates():
        explicit = override and (path == Path(override).expanduser() or path == Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / override)
        if path.is_file() and (explicit or any(
            part in path.name.lower() for part in ("msyh", "simhei", "simsun", "cjk", "pingfang", "stheiti")
        )):
            return str(path)
    return None
