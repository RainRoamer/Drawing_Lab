#!/usr/bin/env python
# Drawing Lab toolkit: SVG, ASCII art, procedural raster scenes, charts and the
# photo lab. Python 3.10+; see requirements.txt and bootstrap.ps1.
import argparse
import json
import math
import os
import random
import re
import sys
import tempfile
from fontlib import find_font, find_cjk_font

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
except ImportError:
    Image = None

try:
    import matplotlib
except ImportError:
    matplotlib = None

PALETTES = {
    "sunset": ["#2d1b4e", "#7b3fa0", "#e07a5f", "#f4a261", "#f9dc9c"],
    "ocean": ["#023047", "#219ebc", "#8ecae6", "#ffb703", "#fb8500"],
    "forest": ["#081c15", "#1b4332", "#2d6a4f", "#40916c", "#d8f3dc"],
    "neon": ["#0d0221", "#31081f", "#6418ff", "#01efc8", "#f72585"],
    "paper": ["#fdf6e3", "#eee8d5", "#93a1a1", "#268bd2", "#b58900"],
    "mono": ["#111111", "#333333", "#555555", "#888888", "#dddddd"],
}

DEFAULT_RAMP = " .:-=+*#%@"
ASCII_CELL_RATIO = 0.5

SVG_SCENES = ["grid", "concentric", "mountains", "waves", "skyline", "spiral"]
RASTER_SCENES = [
    "gradient", "stripes", "checker", "dots", "rings",
    "waves", "blobs", "stars", "sunburst", "city", "spiral",
]

CHART_KINDS = ["bar", "hbar", "line", "pie", "scatter"]


def die(msg):
    print(f"[drawkit] {msg}", file=sys.stderr)
    sys.exit(1)


def require_pil():
    if Image is None:
        die("缺少 Pillow：请用当前解释器运行 python -m pip install -r requirements.txt 安装依赖")


def require_np():
    if np is None:
        die("缺少 numpy：请用当前解释器运行 python -m pip install -r requirements.txt 安装依赖")


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb[:3])


def ensure_out(path, default_name):
    if path:
        return path
    return default_name


def parse_color(s, default="#000000"):
    return s if s else default


def doctor_cmd(args):
    import importlib
    out = []
    out.append(f"python: {sys.version.split()[0]}  {sys.executable}")
    libs = {"PIL": "Pillow", "numpy": "numpy", "matplotlib": "matplotlib",
            "svglib": "svglib", "reportlab.graphics": "reportlab",
            "rlPyCairo": "rlPyCairo"}
    missing_core = False
    for module, label in libs.items():
        ok = False
        try:
            importlib.import_module(module)
            ok = True
        except Exception:
            ok = False
        required = module in ("PIL", "numpy")
        missing_core |= required and not ok
        out.append(f"  {label}: {'ok' if ok else '缺失'} ({'core' if required else 'optional'})")
    cjk = find_cjk_font()
    out.append(f"  CJK font: {cjk if cjk else '未找到（中文图表/文字会缺字）'}")
    print("\n".join(out))
    return 1 if missing_core else 0


def _svg_scene(name, w, h, bg, seed):
    rnd = random.Random(seed)
    w, h = int(w), int(h)
    esc = lambda s: re.sub(r"&(?!amp;)", "&amp;", s).replace("<", "&lt;").replace(">", "&gt;")
    header = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    if bg:
        header += f'<rect width="{w}" height="{h}" fill="{esc(bg)}"/>'
    body = []
    if name == "grid":
        n = 8
        cw, ch = w / n, h / n
        colors = ["#268bd2", "#b58900", "#dc322f"]
        for r in range(n):
            for c in range(n):
                x, y = c * cw, r * ch
                fill = colors[(r + c) % len(colors)]
                body.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cw:.2f}" height="{ch:.2f}" fill="{fill}"/>')
    elif name == "concentric":
        cx, cy = w / 2, h / 2
        rings = 9
        colors = ["#268bd2", "#2aa198", "#859900", "#b58900", "#cb4b16", "#d33682", "#6c71c4"]
        r = max(w, h) * 0.5
        for i in range(rings, 0, -1):
            radius = r * i / rings
            fill = colors[i % len(colors)]
            body.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" fill="{fill}"/>')
        body.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r*0.04:.2f}" fill="#fdf6e3"/>')
    elif name == "mountains":
        sunx, suny = w * 0.78, h * 0.26
        body.append(f'<circle cx="{sunx:.2f}" cy="{suny:.2f}" r="{h*0.16:.2f}" fill="#f9dc9c"/>')
        layers = [("#2d1b4e", h * 0.72, 3), ("#7b3fa0", h * 0.6, 2), ("#e07a5f", h * 0.48, 1)]
        for col, base, amp in layers:
            pts = [(0, h)]
            step = w / 24
            x = 0
            while x <= w + step:
                y = base - amp * (rnd.random() * 0.18 + 0.02) * h * 0.18 * (math.sin(x / w * math.pi * (layers.index((col, base, amp)) + 2)) + 1.2)
                pts.append((x, max(y, 0)))
                x += step
            pts.append((w, h))
            path = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            body.append(f'<polygon points="{path}" fill="{col}"/>')
    elif name == "waves":
        body.append(f'<rect width="{w}" height="{h}" fill="#023047"/>')
        n = 5
        cols = ["#219ebc", "#8ecae6", "#ffb703", "#fb8500"]
        for k in range(n):
            yb = h * (0.35 + 0.62 * k / n)
            pts = []
            for x in range(0, w + 1, 4):
                y = yb + math.sin(x / w * math.pi * (3 + k)) * h * 0.05
                pts.append((x, y))
            path = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
            body.append(f'<polyline points="{path}" fill="none" stroke="{cols[k%4]}" stroke-width="{h*0.045:.2f}" stroke-linecap="round"/>')
    elif name == "skyline":
        y_ground = h * 0.8
        body.append(f'<rect width="{w}" height="{h}" fill="#0d0221"/>')
        body.append(f'<rect y="{y_ground:.2f}" width="{w}" height="{h-y_ground:.2f}" fill="#31081f"/>')
        for i in range(rnd.randint(14, 22)):
            bw = w / 22 * (0.7 + rnd.random() * 0.6)
            bh = (h * 0.25) * (0.4 + rnd.random())
            bx = i * (w / 22)
            by = y_ground - bh
            body.append(f'<rect x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}" fill="#6418ff"/>')
            for wy in range(3):
                body.append(f'<rect x="{bx + bw*0.18:.2f}" y="{by + bh*(0.2+0.28*wy):.2f}" width="{bw*0.26:.2f}" height="{bh*0.06:.2f}" fill="#01efc8"/>')
        body.append(f'<rect x="{w*0.3:.2f}" y="{h*0.15:.2f}" width="{w*0.4:.2f}" height="{h*0.05:.2f}" rx="{h*0.025:.2f}" fill="#f72585"/>')
    elif name == "spiral":
        cx, cy = w / 2, h / 2
        pts = []
        turns = 5
        for i in range(600):
            t = i / 600.0 * turns * 2 * math.pi
            rad = max(w, h) * 0.01 * (1 + t / (turns * 2 * math.pi)) * 2.4
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
        for i in range(1, len(pts)):
            p0, p1 = pts[i - 1], pts[i]
            col = ["#268bd2", "#2aa198", "#859900", "#b58900", "#d33682"][i % 5]
            body.append(f'<line x1="{p0[0]:.2f}" y1="{p0[1]:.2f}" x2="{p1[0]:.2f}" y2="{p1[1]:.2f}" stroke="{col}" stroke-width="3"/>')
    else:
        die(f"未知 SVG 场景：{name}（可选：{', '.join(SVG_SCENES)}）")
    body.append("</svg>")
    return header + "".join(body)


def svg_new_cmd(args):
    scene = args.scene
    if scene not in SVG_SCENES:
        die(f"未知 SVG 场景：{scene}（可选：{', '.join(SVG_SCENES)}）")
    out = ensure_out(args.out, f"{scene}.svg")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    svg = _svg_scene(scene, args.width, args.height, args.background, args.seed)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"SVG 已生成：{out}（场景 {scene}，{args.width}x{args.height}，seed={args.seed}）")
    return 0


def svg_scenes_cmd(args):
    print("内置 SVG 场景：" + ", ".join(SVG_SCENES))
    return 0


def svg_check_cmd(args):
    import xml.etree.ElementTree as ET
    if not os.path.isfile(args.path):
        die(f"找不到文件：{args.path}")
    try:
        tree = ET.parse(args.path)
    except ET.ParseError as exc:
        print(f"SVG XML 解析失败：{exc}")
        return 1
    root = tree.getroot()
    attrs = {}
    for k in ("width", "height", "viewBox"):
        if k in root.attrib:
            attrs[k] = root.attrib[k]
    count = {}
    for el in root.iter():
        tag = re.sub(r"^\{.*\}", "", el.tag)
        count[tag] = count.get(tag, 0) + 1
    print(f"SVG 有效：{args.path}")
    print(f"  根标签: {re.sub(r'^\{.*\}', '', root.tag)}  属性: {attrs}")
    print("  元素计数: " + ", ".join(f"{k}={v}" for k, v in sorted(count.items())))
    if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        print("  注意：根元素不是 <svg>，可能不是合法 SVG")
        return 1
    return 0


def svg_render_cmd(args):
    if not os.path.isfile(args.path):
        die(f"找不到文件：{args.path}")
    out = ensure_out(args.out, os.path.splitext(os.path.basename(args.path))[0] + ".png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    scale = args.scale
    if not math.isfinite(scale) or scale <= 0:
        die("--scale 必须为正的有限数")
    try:
        from cairosvg import svg2png
        svg2png(url=args.path, write_to=out, scale=scale)
        print(f"SVG 已渲染（cairosvg）：{out}")
        return 0
    except (ImportError, OSError):
        pass
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        drawing = svg2rlg(args.path)
        if drawing is None:
            die("svglib 无法解析该 SVG（复杂特性可能不支持）")
        renderPM.drawToFile(drawing, out, fmt="PNG", dpi=int(96 * scale))
        print(f"SVG 已渲染（svglib + reportlab）：{out}")
        return 0
    except ModuleNotFoundError as exc:
        die(f"缺少 SVG 渲染依赖（{exc.name}）：用当前解释器运行 python -m pip install -r requirements.txt，或用浏览器预览")


def ascii_render_cmd(args):
    require_pil()
    if not os.path.isfile(args.image):
        die(f"找不到文件：{args.image}")
    out = ensure_out(args.out, os.path.splitext(os.path.basename(args.image))[0] + ".txt")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    img = Image.open(args.image)
    cols = args.cols or 80
    cell = ASCII_CELL_RATIO if args.ratio is None else args.ratio
    w, h = img.size
    rows = max(1, int(cols * h / w * cell))
    if args.color:
        img = img.resize((cols, rows), Image.LANCZOS)
        px = img.load()
        lines = []
        for y in range(rows):
            line = []
            for x in range(cols):
                r, g, b = px[x, y][:3]
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                idx = int(lum / 255 * (len(DEFAULT_RAMP) - 1)) if not args.invert else int((255 - lum) / 255 * (len(DEFAULT_RAMP) - 1))
                line.append(f"\033[38;2;{r};{g};{b}m{DEFAULT_RAMP[idx]}")
            lines.append("".join(line) + "\033[0m")
        text = "\n".join(lines)
    else:
        img = ImageOps.grayscale(img).resize((cols, rows), Image.LANCZOS)
        vals = list(img.tobytes())
        if args.invert:
            vals = [255 - v for v in vals]
        ramp = args.chars or DEFAULT_RAMP
        if args.threshold is not None:
            chs = [ramp[-1] if v < args.threshold else ramp[0] for v in vals]
        else:
            chs = [ramp[int(v / 255 * (len(ramp) - 1))] for v in vals]
        text = "\n".join("".join(chs[i:i + cols]) for i in range(0, len(chs), cols))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"字符画已生成：{out}（{cols}x{rows}）")
    return 0


def ascii_toimage_cmd(args):
    require_pil()
    if not os.path.isfile(args.text):
        die(f"找不到文件：{args.text}")
    out = ensure_out(args.out, os.path.splitext(os.path.basename(args.text))[0] + ".png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    with open(args.text, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    cols = args.cols or max((len(l) for l in lines), default=0)
    font = find_font(args.size, mono=True)
    if font is None:
        font = ImageFont.load_default()
        cell_w, cell_h = font.getbbox("M")[2] or 8, args.size
    else:
        bbox = font.getbbox("M")
        cell_w = max((bbox[2] - bbox[0]) or 8, 8)
        cell_h = args.size
    bg = hex2rgb(args.background) if args.background else (255, 255, 255)
    fg = hex2rgb(args.foreground) if args.foreground else (0, 0, 0)
    W = max(1, cols * cell_w)
    H = max(1, len(lines) * cell_h)
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)
    for i, ln in enumerate(lines):
        d.text((0, i * cell_h), ln, font=font, fill=fg)
    canvas.save(out)
    print(f"字符画已转图片：{out}（{W}x{H}）")
    return 0


def _raster_scene(name, w, h, palette, seed):
    require_pil()
    require_np()
    rnd = random.Random(seed)
    cols = [hex2rgb(c) for c in palette]
    w, h = int(w), int(h)
    if name == "gradient":
        x = np.linspace(0, 1, w).reshape(1, -1)
        y = np.linspace(0, 1, h).reshape(-1, 1)
        t = (x + y) / 2
        arr = np.zeros((h, w, 3))
        seg = t * (len(cols) - 1)
        for i in range(len(cols) - 1):
            mask = ((seg >= i) & (seg < i + 1))[..., None]
            f = (seg - i)[..., None]
            arr += mask * (np.array(cols[i]) * (1 - f) + np.array(cols[i + 1]) * f)
        arr += (seg >= len(cols) - 1)[..., None] * np.array(cols[-1])
        return Image.fromarray(arr.astype("uint8"))
    if name == "stripes":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        bands = rnd.randint(8, 20)
        bw = w / bands
        for i in range(bands):
            d.rectangle([i * bw, 0, (i + 1) * bw, h], fill=cols[i % len(cols)])
        return img
    if name == "checker":
        n = rnd.choice([4, 6, 8, 10, 12])
        cw, ch = w / n, h / n
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        for r in range(n):
            for c in range(n):
                if (r + c) % 2 == 0:
                    d.rectangle([c * cw, r * ch, (c + 1) * cw, (r + 1) * ch], fill=cols[1 % len(cols)])
                else:
                    d.rectangle([c * cw, r * ch, (c + 1) * cw, (r + 1) * ch], fill=cols[2 % len(cols)])
        return img
    if name == "dots":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        n = rnd.choice([10, 12, 16])
        dx, dy = w / n, h / n
        rad = min(dx, dy) * 0.30
        for r in range(n + 1):
            for c in range(n + 1):
                col = cols[(r + c) % (len(cols) - 1) + 1]
                d.ellipse([c * dx - rad, r * dy - rad, c * dx + rad, r * dy + rad], fill=col)
        return img
    if name == "rings":
        cx, cy = w / 2, h / 2
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        rings = rnd.randint(8, 14)
        maxr = math.hypot(cx, cy)
        for i in range(rings, 0, -1):
            r = maxr * i / rings
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cols[i % (len(cols) - 1) + 1], width=max(2, int(r * 0.05)))
        return img
    if name == "waves":
        require_np()
        x = np.linspace(0, 2 * math.pi * (rnd.randint(2, 5)), w)
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        n = rnd.randint(4, 8)
        for k in range(n):
            yb = h * (0.2 + 0.75 * k / n)
            amp = h * (0.02 + rnd.random() * 0.04)
            pts = [(xx, yb + amp * math.sin(xx / w * 2 * math.pi * rnd.randint(2, 5) + k)) for xx in range(0, w, 4)]
            pts += [(w, yb + amp)]
            d.line(pts, fill=cols[k % len(cols)], width=max(3, int(h * 0.03)))
        return img
    if name == "blobs":
        img = Image.new("RGB", (w, h), cols[0])
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for _ in range(rnd.randint(24, 48)):
            r = rnd.randint(10, max(20, int(min(w, h) * 0.18)))
            cx, cy = rnd.randint(0, w), rnd.randint(0, h)
            col = cols[rnd.randint(1, len(cols) - 1)]
            alpha = rnd.randint(60, 160)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (alpha,))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        return img
    if name == "stars":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        for _ in range(rnd.randint(60, 160)):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            r = rnd.choice([1, 1, 1, 2, 2, 3])
            col = cols[rnd.randint(1, len(cols) - 1)]
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        return img
    if name == "sunburst":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        rays = rnd.randint(16, 40)
        maxr = math.hypot(cx, cy)
        for i in range(rays):
            a0 = 2 * math.pi * i / rays
            a1 = 2 * math.pi * (i + 1) / rays
            col = cols[i % len(cols)]
            d.polygon([(cx, cy),
                       (cx + maxr * math.cos(a0), cy + maxr * math.sin(a0)),
                       (cx + maxr * math.cos(a1), cy + maxr * math.sin(a1))], fill=col)
        d.ellipse([cx - w * 0.12, cy - w * 0.12, cx + w * 0.12, cy + w * 0.12], fill=cols[-1])
        return img
    if name == "city":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        yg = h * 0.82
        d.rectangle([0, yg, w, h], fill=cols[1])
        bw = w / rnd.randint(14, 22)
        for i in range(int(w / bw)):
            bh = (h * 0.4) * (0.4 + rnd.random())
            d.rectangle([i * bw + 2, yg - bh, (i + 1) * bw - 2, yg], fill=cols[2 % len(cols)])
            for wy in range(3):
                d.rectangle([i * bw + bw * 0.2, yg - bh + bh * (0.22 + 0.28 * wy), i * bw + bw * 0.5, yg - bh + bh * (0.3 + 0.28 * wy)], fill=cols[-1])
        return img
    if name == "spiral":
        img = Image.new("RGB", (w, h), cols[0])
        d = ImageDraw.Draw(img)
        cx, cy = w / 2, h / 2
        pts = []
        for i in range(800):
            t = i / 800.0 * 5 * 2 * math.pi
            rad = min(w, h) * 0.02 + t / (5 * 2 * math.pi) * min(w, h) * 0.46
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
        for i in range(1, len(pts)):
            d.line([pts[i - 1], pts[i]], fill=cols[(i // 20) % len(cols)], width=3)
        return img
    die(f"未知 raster 场景：{name}")


def raster_cmd(args):
    if args.scene not in RASTER_SCENES:
        die(f"未知场景：{args.scene}（可选：{', '.join(RASTER_SCENES)}）")
    palette = PALETTES.get(args.palette)
    if not palette:
        die(f"未知配色：{args.palette}（可选：{', '.join(PALETTES)}）")
    out = ensure_out(args.out, f"{args.scene}.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    img = _raster_scene(args.scene, args.width, args.height, palette, args.seed)
    img.save(out)
    print(f"画面已生成：{out}（{args.scene}，{args.width}x{args.height}，配色 {args.palette}）")
    return 0


def raster_scenes_cmd(args):
    print("内置场景：" + ", ".join(RASTER_SCENES))
    print("内置配色：" + ", ".join(f"{k}={','.join(v)}" for k, v in PALETTES.items()))
    return 0


def _load_data(args):
    if args.data_file:
        if not os.path.isfile(args.data_file):
            die(f"找不到数据文件：{args.data_file}")
        with open(args.data_file, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
        labels = obj.get("labels", args.labels or [])
        values = obj.get("values", args.values or [])
        pairs = obj.get("pairs", None)
        series = obj.get("series", None)
    else:
        labels = args.labels or []
        values = args.values or []
        pairs = args.pairs or None
        series = None
    if pairs:
        if isinstance(pairs, str):
            pairs = [x for x in pairs.split(",") if x.strip()]
        parsed = []
        for tok in pairs:
            if isinstance(tok, (list, tuple)) and len(tok) == 2:
                x, y = tok
            elif isinstance(tok, str) and ":" in tok:
                x, y = tok.split(":", 1)
            elif isinstance(tok, str) and "," in tok:
                x, y = tok.split(",", 1)
            else:
                die(f"成对数据需 x:y 格式：{tok}")
            parsed.append((float(x), float(y)))
        return labels, None, parsed, None
    if isinstance(values, str):
        values = [float(x) for x in values.split(",") if x.strip()]
    elif not values:
        values = []
    if isinstance(labels, str):
        labels = [x for x in labels.split(",") if x.strip()]
    elif not labels:
        labels = []
    return labels, values, None, series


def _pil_chart(kind, out, labels, values, pairs, title, w, h, theme):
    bg = hex2rgb("#111111") if theme == "dark" else hex2rgb("#ffffff")
    ink = hex2rgb("#dddddd") if theme == "dark" else hex2rgb("#222222")
    accent = hex2rgb("#268bd2")
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    pad = 60
    if kind in ("bar", "hbar", "line"):
        low, high = min([0] + values), max([0] + values)
        if low == high:
            high = low + 1
        def tx(v):
            return pad + (w - 2 * pad) * (v - low) / (high - low)
        def ty(v):
            return h - pad - (h - 2 * pad) * (v - low) / (high - low)
    if kind == "bar":
        n = len(values)
        bw = (w - 2 * pad) / max(n, 1)
        for i, v in enumerate(values):
            x0 = pad + i * bw + bw * 0.15
            top, bottom = sorted((ty(v), ty(0)))
            d.rectangle([x0, top, x0 + bw * 0.7, bottom], fill=accent)
            if labels and i < len(labels):
                d.text((x0, h - pad + 6), str(labels[i]), font=find_font(14), fill=ink)
            d.text((x0, max(20, top - 20)), f"{v:g}", font=find_font(14), fill=ink)
        d.line([(pad, ty(0)), (w - pad, ty(0))], fill=ink)
    elif kind == "hbar":
        step = (h - 2 * pad) / len(values)
        for i, v in enumerate(values):
            top = pad + i * step + step * 0.15
            left, right = sorted((tx(0), tx(v)))
            d.rectangle([left, top, right, top + step * 0.7], fill=accent)
            label = str(labels[i]) if labels else str(i + 1)
            d.text((8, top), label, font=find_font(14), fill=ink)
        d.line([(tx(0), pad), (tx(0), h - pad)], fill=ink)
    elif kind == "line":
        n = len(values)
        pts = []
        for i, v in enumerate(values):
            x = pad + (w - 2 * pad) * i / max(n - 1, 1)
            y = ty(v)
            pts.append((x, y))
        if len(pts) > 1:
            d.line(pts, fill=accent, width=3)
        for p in pts:
            d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=accent)
        if labels:
            for i, l in enumerate(labels):
                d.text((pts[i][0] - 10, h - pad + 6), str(l), font=find_font(14), fill=ink)
    elif kind == "pie":
        total = sum(values) or 1
        start = 0
        cx, cy = w * 0.32, h / 2
        r = min(w * 0.25, h * 0.4)
        cols = [hex2rgb(c) for c in ["#268bd2", "#2aa198", "#859900", "#b58900", "#cb4b16", "#d33682", "#6c71c4"]]
        for i, v in enumerate(values):
            end = start + 360 * v / total
            d.pieslice([cx - r, cy - r, cx + r, cy + r], start, end, fill=cols[i % len(cols)])
            start = end
        if labels:
            for i, l in enumerate(labels):
                d.text((w * 0.64, pad + i * 20), f"{l}: {values[i]:g}", font=find_font(14), fill=ink)
    elif kind == "scatter":
        if not pairs:
            die("scatter 需要成对数据 --pairs 或 --data-file pairs 字段")
        xmin, xmax = min(p[0] for p in pairs), max(p[0] for p in pairs)
        ymin, ymax = min(p[1] for p in pairs), max(p[1] for p in pairs)
        pts = []
        for x, y in pairs:
            px = pad + (w - 2 * pad) * (x - xmin) / (xmax - xmin) if xmax != xmin else w / 2
            py = h - pad - (h - 2 * pad) * (y - ymin) / (ymax - ymin) if ymax != ymin else h / 2
            pts.append((px, py))
            d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=accent)
    if title:
        d.text((w // 2, 12), title, font=find_font(20), fill=ink, anchor="ma")
    img.save(out)


def chart_cmd(args):
    if args.kind not in CHART_KINDS:
        die(f"未知图表类型：{args.kind}（可选：{', '.join(CHART_KINDS)}）")
    labels, values, pairs, series = _load_data(args)
    if values is not None:
        values = [float(v) for v in values]
        if not all(math.isfinite(v) for v in values):
            die("图表数值必须为有限数")
        if labels and len(labels) != len(values):
            die("标签数量必须与数值数量相同")
    if pairs and not all(math.isfinite(v) for pair in pairs for v in pair):
        die("散点坐标必须为有限数")
    if args.kind == "pie" and values and (min(values) < 0 or sum(values) <= 0):
        die("饼图数值不能为负且总和必须大于零")
    if args.kind == "scatter" and not pairs:
        die("scatter 需要成对数据 --pairs x:y,x2:y2 或 --data-file 的 pairs 字段")
    if not values and args.kind != "scatter":
        die("该图表类型需要 --values 或 --data-file 的 values 字段")
    out = ensure_out(args.out, f"{args.kind}.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    w, h = args.width, args.height
    theme = args.theme
    if matplotlib is not None:
        import matplotlib.pyplot as plt
        if theme == "dark":
            plt.style.use("dark_background")
        cjk = find_cjk_font()
        if cjk:
            try:
                import matplotlib.font_manager as fm
                fm.fontManager.addfont(cjk)
                fam = fm.FontProperties(fname=cjk).get_name()
                plt.rcParams["font.sans-serif"] = [fam, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
            except Exception:
                pass
        fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
        if args.kind in ("bar", "hbar"):
            ax.bar(labels if labels else range(len(values)), values, color="#268bd2") if args.kind == "bar" else ax.barh(labels if labels else range(len(values)), values, color="#268bd2")
        elif args.kind == "line":
            ax.plot(list(range(len(values))), values, marker="o", color="#268bd2")
            if labels:
                ax.set_xticks(range(len(labels)), labels)
        elif args.kind == "pie":
            ax.pie(values, labels=labels if labels else None, autopct="%1.1f%%")
        elif args.kind == "scatter":
            xs = [p[0] for p in pairs]
            ys = [p[1] for p in pairs]
            ax.scatter(xs, ys, color="#268bd2", alpha=0.8)
        if args.title:
            ax.set_title(args.title)
        if args.kind in ("bar", "line"):
            ax.set_ylabel("value")
        fig.tight_layout()
        fig.savefig(out)
        plt.close(fig)
        print(f"图表已生成（matplotlib）：{out}")
        return 0
    if args.kind == "scatter" and not pairs:
        die("scatter 需要成对数据 --pairs x:y,x2:y2 或 --data-file 的 pairs 字段")
    _pil_chart(args.kind, out, labels, values, pairs or [], args.title, w, h, theme)
    print(f"图表已生成（Pillow 回退）：{out}")
    return 0


def _exif_summary(img):
    exif = img.getexif()
    if not exif:
        return None
    out = {}
    names = {271: "make", 272: "model", 306: "datetime", 36867: "created",
             274: "orientation", 33434: "exposure", 37386: "focal", 34853: "gps"}
    for tag, key in names.items():
        if tag in exif:
            out[key] = str(exif[tag])
    return out


def photo_info_cmd(args):
    require_pil()
    if not os.path.isfile(args.path):
        die(f"找不到文件：{args.path}")
    img = Image.open(args.path)
    print(f"文件：{args.path}")
    print(f"  尺寸: {img.size}  模式: {img.mode}  格式: {img.format}")
    print(f"  DPI: {img.info.get('dpi', 'N/A')}")
    ex = _exif_summary(img)
    if ex:
        for k, v in ex.items():
            print(f"  EXIF {k}: {v}")
    else:
        print("  EXIF: 无")
    return 0


def photo_inspect_cmd(args):
    require_pil()
    require_np()
    if not os.path.isfile(args.path):
        die(f"找不到文件：{args.path}")
    img = Image.open(args.path)
    print(f"文件：{args.path}")
    print(f"  尺寸: {img.size}  模式: {img.mode}  格式: {img.format}")
    ex = _exif_summary(img)
    if ex:
        print("  EXIF: " + ", ".join(f"{k}={v}" for k, v in ex.items()))
    arr = np.asarray(img.convert("RGB")).astype(float)
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    print(f"  亮度: 均值 {lum.mean():.1f}  标准差 {lum.std():.1f}  最暗 {lum.min():.0f}  最亮 {lum.max():.0f}")
    hist = np.histogram(lum, bins=10, range=(0, 255))[0]
    hist = (hist / hist.sum() * 100).round(1)
    print("  亮度分布(10档%): " + " ".join(f"{v:.0f}" for v in hist))
    small = img.convert("RGB").resize((64, 64), Image.LANCZOS)
    q = small.quantize(colors=6, method=Image.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    doms = []
    for c, idx in counts:
        doms.append(f"{rgb2hex(tuple(pal[idx * 3:idx * 3 + 3]))}({c * 100 // total}%)")
    print("  主色: " + " ".join(doms))
    return 0


def _apply_ops(img, ops):
    for op in ops:
        key, _, val = op.partition("=")
        key = key.strip().lower()
        if key == "resize":
            if not val:
                die("resize 需要值，如 resize=800x 或 resize=800x600")
            m = re.match(r"^(\d*)[xX](\d*)$", val.strip())
            if not m:
                die(f"resize 格式错误：{val}（示例 800x 或 800x600）")
            nw, nh = (int(m.group(1)) if m.group(1) else None, int(m.group(2)) if m.group(2) else None)
            w, h = img.size
            if nw and nh:
                target = (nw, nh)
            elif nw:
                target = (nw, max(1, int(h * nw / w)))
            else:
                target = (max(1, int(w * nh / h)), nh)
            img = img.resize(target, Image.LANCZOS)
        elif key == "crop":
            m = re.match(r"^([\d.]+)(%?)[,;]([\d.]+)(%?)[,;]([\d.]+)(%?)[,;]([\d.]+)(%?)$", val.strip())
            if not m:
                die(f"crop 格式错误：{val}（示例 100,200,700,800 或 10%,20%,70%,60%）")
            w, h = img.size
            vals = []
            for i in range(4):
                num = float(m.group(i * 2 + 1))
                if m.group(i * 2 + 2) == "%":
                    num = num / 100 * (w if i % 2 == 0 else h)
                vals.append(int(num))
            l, t, r, b = vals
            if l < 0 or t < 0 or r <= l or b <= t:
                die(f"crop 范围无效：{vals}")
            img = img.crop((l, t, r, b))
        elif key == "rotate":
            img = img.rotate(float(val), expand=True, resample=Image.BICUBIC)
        elif key == "flip":
            if val.strip().lower() in ("h", "horizontal", "左右"):
                img = ImageOps.mirror(img)
            elif val.strip().lower() in ("v", "vertical", "上下"):
                img = ImageOps.flip(img)
            else:
                die(f"flip 需为 h 或 v：{val}")
        elif key == "brightness":
            img = ImageEnhance.Brightness(img).enhance(float(val))
        elif key == "contrast":
            img = ImageEnhance.Contrast(img).enhance(float(val))
        elif key == "saturation":
            img = ImageEnhance.Color(img).enhance(float(val))
        elif key == "sharpness":
            img = ImageEnhance.Sharpness(img).enhance(float(val))
        elif key == "blur":
            img = img.filter(ImageFilter.GaussianBlur(float(val) if val else 2.0))
        elif key == "sharpen":
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        elif key == "grayscale":
            img = ImageOps.grayscale(img).convert("RGB")
        elif key == "sepia":
            g = ImageOps.grayscale(img)
            sep = np.asarray(g).astype(float)
            tr = np.clip(sep * 1.2 + 10, 0, 255).astype("uint8")
            tg = np.clip(sep * 1.08 + 4, 0, 255).astype("uint8")
            tb = np.clip(sep * 0.8, 0, 255).astype("uint8")
            img = Image.merge("RGB", [Image.fromarray(tr), Image.fromarray(tg), Image.fromarray(tb)])
        elif key == "invert":
            img = ImageOps.invert(img.convert("RGB"))
        elif key == "posterize":
            img = ImageOps.posterize(img, int(val) if val else 4)
        elif key == "vignette":
            require_np()
            w, h = img.size
            y, x = np.ogrid[:h, :w]
            cx, cy = w / 2, h / 2
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            maxd = np.sqrt(cx * cx + cy * cy)
            strength = float(val) if val else 30
            mask = np.clip(1 - (dist / maxd) * (strength / 100), 0, 1)
            mask = mask[..., None]
            arr = np.asarray(img).astype(float)
            arr = arr * mask + 0 * (1 - mask)
            img = Image.fromarray(arr.astype("uint8"))
        else:
            die(f"未知编辑操作：{key}（支持 resize/crop/rotate/flip/brightness/contrast/saturation/sharpness/blur/sharpen/grayscale/sepia/invert/posterize/vignette）")
    return img


def photo_edit_cmd(args):
    require_pil()
    if not os.path.isfile(args.path):
        die(f"找不到文件：{args.path}")
    if not args.op:
        die("需要至少一个 --op 操作")
    img = Image.open(args.path)
    img = _apply_ops(img, args.op)
    out = ensure_out(args.out, os.path.splitext(os.path.basename(args.path))[0] + "_edit.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    if args.format:
        base = os.path.splitext(out)[0]
        out = base + "." + args.format.lower()
    fmt = (args.format or os.path.splitext(out)[1].lstrip(".") or "png").upper()
    if fmt == "JPG":
        fmt = "JPEG"
    img.save(out, format=fmt, quality=args.quality)
    print(f"照片已编辑：{out}（操作链: {' -> '.join(args.op)}）")
    return 0


def photo_canvas_cmd(args):
    require_pil()
    if not args.images:
        die("需要至少一张图片")
    for p in args.images:
        if not os.path.isfile(p):
            die(f"找不到文件：{p}")
    imgs = [Image.open(p) for p in args.images]
    n = len(imgs)
    cols = args.cols or min(n, 4)
    rows = math.ceil(n / cols)
    cell = args.size
    if cell:
        m = re.match(r"^(\d+)[xX](\d+)$", cell)
        if not m:
            die(f"--size 格式错误：{cell}（示例 400x300）")
        cw, ch = int(m.group(1)), int(m.group(2))
    else:
        cw, ch = max(i.size for i in imgs)
    pad = args.pad
    bg = hex2rgb(args.background) if args.background else (245, 245, 245)
    W = cols * cw + (cols + 1) * pad
    H = rows * ch + (rows + 1) * pad
    canvas = Image.new("RGB", (W, H), bg)
    labels = (args.labels or "").split(",") if args.labels else []
    for idx, im in enumerate(imgs):
        r, c = divmod(idx, cols)
        x0 = pad + c * (cw + pad)
        y0 = pad + r * (ch + pad)
        im = im.convert("RGB")
        ratio = max(cw / im.size[0], ch / im.size[1])
        nw, nh = max(1, int(im.size[0] * ratio)), max(1, int(im.size[1] * ratio))
        im = im.resize((nw, nh), Image.LANCZOS)
        ox = max(0, (nw - cw) // 2)
        oy = max(0, (nh - ch) // 2)
        canvas.paste(im.crop((ox, oy, ox + cw, oy + ch)), (x0, y0))
        if labels and idx < len(labels):
            d = ImageDraw.Draw(canvas)
            f = find_font(16)
            d.rectangle([x0, y0, x0 + cw, y0 + 24], fill=(0, 0, 0))
            d.text((x0 + 6, y0 + 3), labels[idx], font=f, fill=(255, 255, 255))
    out = ensure_out(args.out, "canvas.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    canvas.save(out)
    print(f"拼版已生成：{out}（{cols}x{rows}）")
    return 0


def photo_blend_cmd(args):
    require_pil()
    for p in (args.a, args.b):
        if not os.path.isfile(p):
            die(f"找不到文件：{p}")
    a = Image.open(args.a).convert("RGB")
    b = Image.open(args.b).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    mix = float(args.mix)
    if args.mask == "h":
        require_np()
        w, h = a.size
        grad = np.linspace(0, 1, w).astype(float).reshape(1, -1)
        m = np.repeat(grad, h, axis=0)[..., None]
        if mix < 1:
            m = m * mix
        out = a * (1 - m) + b * m
        img = Image.fromarray(out.astype("uint8"))
    elif args.mask == "v":
        require_np()
        w, h = a.size
        grad = np.linspace(0, 1, h).astype(float).reshape(-1, 1)
        m = np.repeat(grad, w, axis=1)[..., None]
        if mix < 1:
            m = m * mix
        out = a * (1 - m) + b * m
        img = Image.fromarray(out.astype("uint8"))
    else:
        img = Image.blend(a, b, alpha=mix)
    out = ensure_out(args.out, "blend.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    img.save(out)
    print(f"混合已生成：{out}（mix={mix}，mask={args.mask or '均匀'}）")
    return 0


def photo_text_cmd(args):
    require_pil()
    if not args.text:
        die("需要 --text 内容（\n 换行）")
    if args.blank:
        img = Image.new("RGB", (args.width, args.height), hex2rgb(args.background) if args.background else (255, 255, 255))
    else:
        if not os.path.isfile(args.path):
            die(f"找不到文件：{args.path}")
        img = Image.open(args.path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = find_font(args.size) or ImageFont.load_default()
    lines = args.text.split("\\n") if "\\n" in args.text else args.text.split("\n")
    w, h = img.size
    line_h = int(args.size * 1.2)
    block_h = line_h * len(lines)
    text_w = max((draw.textlength(l, font=font) for l in lines), default=0)
    pos = args.pos or "center"
    if pos == "center":
        x, y = (w - text_w) / 2, (h - block_h) / 2
    elif pos == "top":
        x, y = (w - text_w) / 2, line_h
    elif pos == "bottom":
        x, y = (w - text_w) / 2, h - block_h - line_h
    elif re.match(r"^\d+,\d+$", pos):
        x, y = (int(v) for v in pos.split(","))
    else:
        die(f"pos 需为 center/top/bottom 或 x,y：{pos}")
    color = hex2rgb(args.color) if args.color else (255, 255, 255)
    shadow = hex2rgb(args.shadow) if args.shadow else (0, 0, 0)
    for i, ln in enumerate(lines):
        yy = y + i * line_h
        draw.text((x + 2, yy + 2), ln, font=font, fill=shadow)
        draw.text((x, yy), ln, font=font, fill=color)
    out = ensure_out(args.out, "text.png")
    if os.path.exists(out):
        die(f"输出已存在，拒绝覆盖：{out}")
    img.save(out)
    print(f"文字已绘制：{out}")
    return 0


def _diagramlib():
    try:
        from diagramlib import (circuit_cmd, ray_cmd, force_cmd, object_cmd,
                                figure_cmd, func_cmd, axes_cmd, three_cmd,
                                chem_molecule_cmd, chem_cell_cmd,
                                chem_reaction_cmd, chem_apparatus_cmd)
        return (circuit_cmd, ray_cmd, force_cmd, object_cmd,
                figure_cmd, func_cmd, axes_cmd, three_cmd,
                chem_molecule_cmd, chem_cell_cmd,
                chem_reaction_cmd, chem_apparatus_cmd)
    except ImportError as exc:
        die(f"缺少 diagramlib 模块（{exc}）：请确认 scripts/ 目录完整")


def physics_circuit_cmd(args):
    _diagramlib()[0](args)


def physics_ray_cmd(args):
    _diagramlib()[1](args)


def physics_force_cmd(args):
    _diagramlib()[2](args)


def physics_object_cmd(args):
    _diagramlib()[3](args)


def math_figure_cmd(args):
    _diagramlib()[4](args)


def math_func_cmd(args):
    _diagramlib()[5](args)


def math_axes_cmd(args):
    _diagramlib()[6](args)


def three_cmd_wrapper(args):
    _diagramlib()[7](args)


def chem_molecule_wrapper(args):
    _diagramlib()[8](args)


def chem_cell_wrapper(args):
    _diagramlib()[9](args)


def chem_reaction_wrapper(args):
    _diagramlib()[10](args)


def chem_apparatus_wrapper(args):
    _diagramlib()[11](args)


def mindmap_wrapper(args):
    require_pil()
    from mindmap import mindmap_cmd
    return mindmap_cmd(args)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="drawkit", description="Drawing Lab: mind maps / SVG / raster / charts / science diagrams / photos")
    sub = ap.add_subparsers(dest="group")
    sub.add_parser("doctor", help="环境诊断").set_defaults(fn=doctor_cmd)

    p = sub.add_parser("mindmap", help="Markdown/JSON → 离线 SVG/PNG 思维导图")
    p.add_argument("out", help="输出 .svg 或 .png")
    p.add_argument("--input", required=True, help="UTF-8 Markdown 大纲或 .json 树")
    p.add_argument("--layout", choices=["balanced", "right", "left"], default="balanced")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--font-size", type=int, default=20)
    p.add_argument("--max-width", type=int, default=220, help="节点文本最大宽度（像素），自动换行")
    p.add_argument("--scale", type=float, default=1.0, help="PNG 分辨率倍数（0.5–4）；SVG 自带矢量缩放")
    p.set_defaults(fn=mindmap_wrapper)

    p = sub.add_parser("svg", help="SVG 场景")
    ssub = p.add_subparsers(dest="cmd")
    sp = ssub.add_parser("scenes", help="列出内置场景")
    sp.set_defaults(fn=svg_scenes_cmd)
    sp = ssub.add_parser("new", help="生成内置 SVG 场景")
    sp.add_argument("out")
    sp.add_argument("--scene", required=True)
    sp.add_argument("--width", type=int, default=800)
    sp.add_argument("--height", type=int, default=600)
    sp.add_argument("--background", default="#fdf6e3")
    sp.add_argument("--seed", type=int, default=1)
    sp.set_defaults(fn=svg_new_cmd)
    sp = ssub.add_parser("check", help="校验 SVG XML 并统计元素")
    sp.add_argument("path")
    sp.set_defaults(fn=svg_check_cmd)
    sp = ssub.add_parser("render", help="SVG 渲染为 PNG（cairosvg → svglib 回退）")
    sp.add_argument("path")
    sp.add_argument("-o", "--out")
    sp.add_argument("--scale", type=float, default=1.0)
    sp.set_defaults(fn=svg_render_cmd)

    p = sub.add_parser("raster", help="Pillow 程序化画面")
    p.add_argument("out")
    p.add_argument("--scene", required=True)
    p.add_argument("--width", type=int, default=960)
    p.add_argument("--height", type=int, default=540)
    p.add_argument("--palette", default="sunset")
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(fn=raster_cmd)
    sub.add_parser("raster-scenes", help="列出 raster 场景与配色").set_defaults(fn=raster_scenes_cmd)

    p = sub.add_parser("ascii", help="ASCII 字符画")
    ssub = p.add_subparsers(dest="cmd")
    sp = ssub.add_parser("render", help="图片 → 字符画文本")
    sp.add_argument("image")
    sp.add_argument("-o", "--out")
    sp.add_argument("--cols", type=int, default=80)
    sp.add_argument("--ratio", type=float, default=None, help="字符高宽比修正")
    sp.add_argument("--chars", default="", help="亮度→字符梯度")
    sp.add_argument("--invert", action="store_true")
    sp.add_argument("--threshold", type=int, default=None, help="二值阈值")
    sp.add_argument("--color", action="store_true", help="ANSI 真彩输出")
    sp.set_defaults(fn=ascii_render_cmd)
    sp = ssub.add_parser("toimage", help="字符画文本 → PNG")
    sp.add_argument("text")
    sp.add_argument("-o", "--out")
    sp.add_argument("--cols", type=int, default=None)
    sp.add_argument("--size", type=int, default=18)
    sp.add_argument("--background", default=None)
    sp.add_argument("--foreground", default=None)
    sp.set_defaults(fn=ascii_toimage_cmd)

    p = sub.add_parser("chart", help="图表（matplotlib，Pillow 回退）")
    p.add_argument("kind", choices=CHART_KINDS)
    p.add_argument("out")
    p.add_argument("--values")
    p.add_argument("--labels")
    p.add_argument("--pairs", help="成对数据，如 1:2,3:4")
    p.add_argument("--data-file", help="JSON: {labels,values} 或 {pairs: [[x,y], ...]}")
    p.add_argument("--title", default="")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--width", type=int, default=900)
    p.add_argument("--height", type=int, default=500)
    p.set_defaults(fn=chart_cmd)

    p = sub.add_parser("photo", help="照片实验室")
    ssub = p.add_subparsers(dest="cmd")
    sp = ssub.add_parser("info", help="照片基本属性与 EXIF")
    sp.add_argument("path")
    sp.set_defaults(fn=photo_info_cmd)
    sp = ssub.add_parser("inspect", help="照片像素统计与主色")
    sp.add_argument("path")
    sp.set_defaults(fn=photo_inspect_cmd)
    sp = ssub.add_parser("edit", help="链式编辑照片")
    sp.add_argument("path")
    sp.add_argument("-o", "--out")
    sp.add_argument("--op", action="append", default=[], help="操作，如 rotate=90 / resize=1600x / sepia")
    sp.add_argument("--format", default=None, help="输出格式 png/jpg")
    sp.add_argument("--quality", type=int, default=90)
    sp.set_defaults(fn=photo_edit_cmd)
    sp = ssub.add_parser("canvas", help="多图拼版")
    sp.add_argument("images", nargs="+")
    sp.add_argument("-o", "--out")
    sp.add_argument("--cols", type=int, default=None)
    sp.add_argument("--size", default=None, help="单元尺寸 WxH")
    sp.add_argument("--labels", default="", help="逗号分隔的标签")
    sp.add_argument("--pad", type=int, default=8)
    sp.add_argument("--background", default=None)
    sp.set_defaults(fn=photo_canvas_cmd)
    sp = ssub.add_parser("blend", help="两张图片混合")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.add_argument("-o", "--out")
    sp.add_argument("--mix", type=float, default=0.5)
    sp.add_argument("--mask", choices=["h", "v", ""], default="", help="渐变遮罩方向")
    sp.set_defaults(fn=photo_blend_cmd)
    sp = ssub.add_parser("text", help="图片/空白画布上写字")
    sp.add_argument("path", nargs="?", default=None)
    sp.add_argument("-o", "--out")
    sp.add_argument("--text", required=True)
    sp.add_argument("--pos", default="center")
    sp.add_argument("--size", type=int, default=48)
    sp.add_argument("--color", default=None)
    sp.add_argument("--shadow", default=None)
    sp.add_argument("--blank", action="store_true", help="用空白画布")
    sp.add_argument("--width", type=int, default=1200)
    sp.add_argument("--height", type=int, default=800)
    sp.add_argument("--background", default="#ffffff")
    sp.set_defaults(fn=photo_text_cmd)

    pg = sub.add_parser("physics", help="物理图：电路 / 光路 / 受力 / 实物")
    pgsub = pg.add_subparsers(dest="cmd")
    c = pgsub.add_parser("circuit", help="电路图（元件 DSL）")
    c.add_argument("out")
    c.add_argument("--spec", required=True, help="元件描述，如 W:R:120;R:D:140;...")
    c.add_argument("--origin", default="100,100", help="链式起点 X,Y")
    c.add_argument("--width", type=int, default=800)
    c.add_argument("--height", type=int, default=560)
    c.add_argument("--grid", action="store_true")
    c.add_argument("--background", default="#ffffff")
    c.add_argument("--ink", default="#111111")
    c.add_argument("--line-width", type=int, default=3)
    c.add_argument("--font-size", type=int, default=18)
    c.set_defaults(fn=physics_circuit_cmd)
    r = pgsub.add_parser("ray", help="光路图（凸/凹透镜与平面镜）")
    r.add_argument("out")
    r.add_argument("--kind", choices=["convex", "concave", "plane"], required=True)
    r.add_argument("--focal", type=int, default=None, help="焦距 px")
    r.add_argument("--object", type=int, default=None, help="物距/物体 x 坐标")
    r.add_argument("--height", type=int, default=None, help="物体高度 px")
    r.add_argument("--width", type=int, default=820)
    r.add_argument("--grid", action="store_true")
    r.add_argument("--background", default="#ffffff")
    r.add_argument("--ink", default="#132a3c")
    r.add_argument("--aux-color", default="#1f77b4")
    r.add_argument("--font-size", type=int, default=18)
    r.set_defaults(fn=physics_ray_cmd)
    f = pgsub.add_parser("force", help="斜面受力图")
    f.add_argument("out")
    f.add_argument("--angle", type=float, default=30.0)
    f.add_argument("--width", type=int, default=900)
    f.add_argument("--height", type=int, default=520)
    f.add_argument("--grid", action="store_true")
    f.add_argument("--friction", action="store_true")
    f.add_argument("--pull", action="store_true")
    f.add_argument("--tension", action="store_true")
    f.add_argument("--free", action="store_true", help="右侧额外画隔离体受力图")
    f.add_argument("--cn", action="store_true", help="中文力名标注")
    f.add_argument("--background", default="#ffffff")
    f.add_argument("--ink", default="#111111")
    f.add_argument("--aux-color", default="#1f77b4")
    f.add_argument("--font-size", type=int, default=18)
    f.set_defaults(fn=physics_force_cmd)
    o = pgsub.add_parser("object", help="实物图场景（斜面/杠杆/滑轮/单摆/弹簧/波动）")
    o.add_argument("out")
    o.add_argument("--scene", choices=["incline", "lever", "pulley", "pendulum", "spring", "wave"], required=True)
    o.add_argument("--angle", type=float, default=30.0, help="斜面角/单摆角（度）")
    o.add_argument("--amplitude", type=int, default=45)
    o.add_argument("--wavelength", type=int, default=110)
    o.add_argument("--cycles", type=int, default=2)
    o.add_argument("--longitudinal", action="store_true", help="纵波（密部/疏部）")
    o.add_argument("--width", type=int, default=820)
    o.add_argument("--height", type=int, default=480)
    o.add_argument("--cn", action="store_true", help="中文标注")
    o.add_argument("--background", default="#ffffff")
    o.add_argument("--ink", default="#111111")
    o.add_argument("--aux-color", default="#1f77b4")
    o.add_argument("--font-size", type=int, default=18)
    o.set_defaults(fn=physics_object_cmd)

    mu = sub.add_parser("math", help="数学图：几何 / 函数 / 坐标系")
    musub = mu.add_subparsers(dest="cmd")
    g = musub.add_parser("figure", help="几何图（点/线段/辅助线/角标记 DSL）")
    g.add_argument("out")
    g.add_argument("--spec", required=True, help="几何描述，如 pt A 100,380;line A-B;...")
    g.add_argument("--width", type=int, default=820)
    g.add_argument("--height", type=int, default=620)
    g.add_argument("--grid", action="store_true")
    g.add_argument("--dots", action="store_true", help="自动标注用到的端点")
    g.add_argument("--background", default="#ffffff")
    g.add_argument("--ink", default="#111111")
    g.add_argument("--aux-color", default="#2563eb")
    g.add_argument("--line-width", type=int, default=3)
    g.add_argument("--point-radius", type=int, default=4)
    g.add_argument("--angle-radius", type=int, default=26)
    g.add_argument("--font-size", type=int, default=18)
    g.set_defaults(fn=math_figure_cmd)
    fn = musub.add_parser("func", help="函数图（轴/切线/渐近线/零点）")
    fn.add_argument("out")
    fn.add_argument("--fn", dest="expr", required=True, help="函数表达式，如 x**2-2 或 1/x")
    fn.add_argument("--xmin", type=float, default=-6.0)
    fn.add_argument("--xmax", type=float, default=6.0)
    fn.add_argument("--ymin", type=float, default=None)
    fn.add_argument("--ymax", type=float, default=None)
    fn.add_argument("--tangent", type=float, default=None, help="画 x0 处切线")
    fn.add_argument("--asymptote-v", type=float, default=None, help="竖直渐近线 x=a")
    fn.add_argument("--asymptote-h", type=float, default=None, help="水平渐近线 y=b")
    fn.add_argument("--roots", action="store_true", help="标记零点")
    fn.add_argument("--label", default=None, help="图内公式文本")
    fn.add_argument("--grid", action="store_true")
    fn.add_argument("--axis-labels", action="store_true")
    fn.add_argument("--width", type=int, default=820)
    fn.add_argument("--height", type=int, default=560)
    fn.add_argument("--background", default="#ffffff")
    fn.add_argument("--ink", default="#111111")
    fn.add_argument("--aux-color", default="#2563eb")
    fn.add_argument("--font-size", type=int, default=18)
    fn.set_defaults(fn=math_func_cmd)
    ax = musub.add_parser("axes", help="坐标系（网格与刻度）")
    ax.add_argument("out")
    ax.add_argument("--xmin", type=float, default=-10.0)
    ax.add_argument("--xmax", type=float, default=10.0)
    ax.add_argument("--ymin", type=float, default=-8.0)
    ax.add_argument("--ymax", type=float, default=8.0)
    ax.add_argument("--grid", action="store_true")
    ax.add_argument("--width", type=int, default=820)
    ax.add_argument("--height", type=int, default=560)
    ax.add_argument("--background", default="#ffffff")
    ax.add_argument("--ink", default="#111111")
    ax.add_argument("--font-size", type=int, default=16)
    ax.set_defaults(fn=math_axes_cmd)

    t3 = sub.add_parser("3d", help="3D 几何图（投影绘制）")
    t3.add_argument("out")
    t3.add_argument("--scene", choices=["axes", "cube", "pyramid", "prism", "cylinder", "sphere"], required=True)
    t3.add_argument("--yaw", type=float, default=35.0)
    t3.add_argument("--pitch", type=float, default=25.0)
    t3.add_argument("--scale", type=float, default=110.0)
    t3.add_argument("--width", type=int, default=820)
    t3.add_argument("--height", type=int, default=620)
    t3.add_argument("--grid", action="store_true")
    t3.add_argument("--palette", default="#dbeafe,#bfdbfe,#93c5fd,#60a5fa,#3b82f6")
    t3.add_argument("--background", default="#ffffff")
    t3.add_argument("--ink", default="#102a43")
    t3.add_argument("--line-width", type=int, default=3)
    t3.add_argument("--label", default="")
    t3.add_argument("--font-size", type=int, default=20)
    t3.set_defaults(fn=three_cmd_wrapper)

    ch = sub.add_parser("chem", help="化学图（分子、晶胞、反应式、器材）")
    chsub = ch.add_subparsers(dest="cmd")
    cm = chsub.add_parser("molecule", help="分子结构图")
    cm.add_argument("out")
    cm.add_argument("--atoms", required=True, help="如 C:260,260;O:390,260;H:210,180")
    cm.add_argument("--bonds", default="", help="如 C:O:2;C:H:1")
    cm.add_argument("--model", choices=["line", "ball"], default="ball")
    cm.add_argument("--width", type=int, default=720)
    cm.add_argument("--height", type=int, default=520)
    cm.add_argument("--atom-color", default="#dbeafe")
    cm.add_argument("--background", default="#ffffff")
    cm.add_argument("--ink", default="#102a43")
    cm.add_argument("--line-width", type=int, default=4)
    cm.add_argument("--font-size", type=int, default=22)
    cm.add_argument("--label", default="")
    cm.set_defaults(fn=chem_molecule_wrapper)
    cc = chsub.add_parser("cell", help="晶胞结构图")
    cc.add_argument("out")
    cc.add_argument("--kind", choices=["sc", "bcc", "fcc"], default="sc")
    cc.add_argument("--width", type=int, default=720)
    cc.add_argument("--height", type=int, default=520)
    cc.add_argument("--site-color", default="#f59e0b")
    cc.add_argument("--background", default="#ffffff")
    cc.add_argument("--ink", default="#102a43")
    cc.add_argument("--font-size", type=int, default=22)
    cc.set_defaults(fn=chem_cell_wrapper)
    cr = chsub.add_parser("reaction", help="化学反应式图")
    cr.add_argument("out")
    cr.add_argument("--equation", required=True, help="如 2H2+O2->2H2O")
    cr.add_argument("--condition", default="点燃")
    cr.add_argument("--width", type=int, default=900)
    cr.add_argument("--height", type=int, default=260)
    cr.add_argument("--background", default="#ffffff")
    cr.add_argument("--ink", default="#102a43")
    cr.add_argument("--font-size", type=int, default=26)
    cr.set_defaults(fn=chem_reaction_wrapper)
    ca = chsub.add_parser("apparatus", help="化学实验器材图")
    ca.add_argument("out")
    ca.add_argument("--kind", choices=["beaker", "flask", "test-tube"], required=True)
    ca.add_argument("--width", type=int, default=700)
    ca.add_argument("--height", type=int, default=520)
    ca.add_argument("--liquid-color", default="#93c5fd")
    ca.add_argument("--background", default="#ffffff")
    ca.add_argument("--ink", default="#102a43")
    ca.add_argument("--font-size", type=int, default=24)
    ca.set_defaults(fn=chem_apparatus_wrapper)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    try:
        out = getattr(args, "out", None)
        if out and os.path.exists(out):
            die(f"输出已存在，拒绝覆盖：{out}")
        return args.fn(args)
    except BrokenPipeError:
        return 0
    except (ValueError, OSError, KeyError) as exc:
        die(str(exc))


if __name__ == "__main__":
    sys.exit(main())
