#!/usr/bin/env python
# diagramlib.py - physics & math diagram engine for Drawing Lab.
# Pure Pillow drawing, deterministic, no network. Commands are exposed through
# drawkit.py under the `physics` and `math` groups.
import math
import ast
import operator
import os
import re
import sys
from fontlib import find_font

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
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None



def die(msg):
    print(f"[diagramlib] {msg}", file=sys.stderr)
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


def _grid(d, w, h, step=20, color=(228, 228, 232)):
    for x in range(step, w, step):
        d.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(step, h, step):
        d.line([(0, y), (w, y)], fill=color, width=1)


def _dashed(d, p1, p2, fill, width=2, dash=9, gap=6):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-9:
        return
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    t = 0.0
    while t < L:
        e = min(t + dash, L)
        d.line([(x1 + ux * t, y1 + uy * t), (x1 + ux * e, y1 + uy * e)],
               fill=fill, width=width)
        t += dash + gap


def _head(d, p, ang, size, fill, width):
    x, y = p
    for da in (math.radians(26), -math.radians(26)):
        d.line([(x, y), (x - size * math.cos(ang - da),
                         y - size * math.sin(ang - da))], fill=fill, width=width)


def _arrow(d, p1, p2, fill, width=2, head=10, both=False):
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return
    ux, uy = dx / L, dy / L
    a = math.atan2(dy, dx)
    stop = (x2 - ux * head, y2 - uy * head)
    d.line([p1, stop], fill=fill, width=width)
    _head(d, p2, a, head, fill, width)
    if both:
        d.line([p1, (x1 + ux * head, y1 + uy * head)], fill=fill, width=width)
        _head(d, p1, a + math.pi, head, fill, width)


def _dot(d, p, r=4, fill=(0, 0, 0)):
    x, y = p
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _text(d, xy, text, font, fill, center=True):
    if font is None:
        font = ImageFont.load_default()
    x, y = xy
    w = d.textlength(text, font=font)
    try:
        asc, desc = font.getmetrics()
    except Exception:
        asc = desc = font.size
    if center:
        x -= w / 2
        y -= (asc + desc) / 2
    d.text((x, y), text, font=font, fill=fill)


_SUBSCRIPT = str.maketrans("0123456789+-=()", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
_SUPERSCRIPT = str.maketrans("0123456789+-=()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾")


def _chem_runs(text):
    runs = []
    i = 0
    while i < len(text):
        if text[i] in "_^":
            mode = text[i]
            i += 1
            if i < len(text) and text[i] == "{":
                end = text.find("}", i + 1)
                if end < 0:
                    end = len(text)
                value = text[i + 1:end]
                i = min(end + 1, len(text))
            elif i < len(text):
                value = text[i]
                i += 1
            else:
                value = ""
            runs.append((value, "superscript" if mode == "^" else "subscript"))
            continue
        start = i
        while i < len(text) and text[i] not in "_^":
            i += 1
        value = text[start:i]
        if value:
            for match in re.finditer(r"[A-Za-z]+|\d+|[^A-Za-z\d]+", value):
                part = match.group(0)
                if part.isdigit() and runs and runs[-1][1] == "normal":
                    runs.append((part, "subscript"))
                elif part in ("+", "-") and match.end() == len(value) and runs:
                    runs.append((part, "superscript"))
                else:
                    runs.append((part, "normal"))
    return runs


def _chem_text(d, xy, text, font, fill, center=True):
    """Draw a chemical formula with baseline-aware subscript and superscript runs."""
    if font is None:
        font = ImageFont.load_default()
    runs = _chem_runs(str(text))
    normal_size = getattr(font, "size", 18)
    small = find_font(max(10, int(normal_size * 0.68))) or font
    widths = [d.textlength(value, font=(small if mode != "normal" else font)) for value, mode in runs]
    total = sum(widths)
    x, baseline = xy
    if center:
        x -= total / 2
    for (value, mode), width in zip(runs, widths):
        use_font = small if mode != "normal" else font
        bbox = d.textbbox((0, 0), value, font=use_font)
        y = baseline - bbox[3] / 2
        if mode == "subscript":
            y += normal_size * 0.25
        elif mode == "superscript":
            y -= normal_size * 0.35
        d.text((x, y), value, font=use_font, fill=fill)
        x += width


def _arc_mark(d, center, pa, pb, radius, fill, width=2):
    cx, cy = center
    a0 = math.atan2(pa[1] - cy, pa[0] - cx)
    a1 = math.atan2(pb[1] - cy, pb[0] - cx)
    while a1 < a0:
        a1 += 2 * math.pi
    bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
    d.arc(bbox, math.degrees(a0), math.degrees(a1), fill=fill, width=width)


def _right_mark(d, vertex, pa, pb, fill, size=15, width=2):
    cx, cy = vertex
    ua = (pa[0] - cx, pa[1] - cy)
    ub = (pb[0] - cx, pb[1] - cy)
    la = math.hypot(*ua) or 1
    lb = math.hypot(*ub) or 1
    ua = (ua[0] / la * size, ua[1] / la * size)
    ub = (ub[0] / lb * size, ub[1] / lb * size)
    q1 = (cx + ua[0], cy + ua[1])
    q2 = (cx + ub[0], cy + ub[1])
    corner = (cx + ua[0] + ub[0], cy + ua[1] + ub[1])
    d.line([q1, corner], fill=fill, width=width)
    d.line([q2, corner], fill=fill, width=width)


def _eq_ticks(d, p1, p2, count, fill, width=2):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-9:
        return
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    tl = max(8.0, min(13.0, L * 0.06))
    spacing = tl * 0.9
    for i in range(count):
        off = (i - (count - 1) / 2.0) * spacing
        cx = mx + ux * off
        cy = my + uy * off
        d.line([(cx - nx * tl / 2, cy - ny * tl / 2),
                (cx + nx * tl / 2, cy + ny * tl / 2)], fill=fill, width=width)


def _par_chevrons(d, p1, p2, fill, width=2):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-9:
        return
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    cs = max(7.0, min(11.0, L * 0.05))
    for frac in (0.30, 0.62):
        ax = x1 + ux * L * frac
        ay = y1 + uy * L * frac
        d.line([(ax - ux * cs - nx * cs, ay - uy * cs - ny * cs), (ax, ay)],
               fill=fill, width=width)
        d.line([(ax - ux * cs + nx * cs, ay - uy * cs + ny * cs), (ax, ay)],
               fill=fill, width=width)


# ---------------------------------------------------------------------------
# physics circuit: mini DSL of components on a canvas.
#   W:R:120     wire to the right 120 px (chain, dir in R/L/U/D)
#   R:D:140     resistor going down 140 px
#   R:(100,200)-(300,200)   resistor between two absolute points
#   LAB:电压表:R:10          label near the current point
#   at X,Y      jump the pen to an absolute point
# Types: W wire, R resistor, B battery, C cell, L bulb, S switch,
#        A ammeter, V voltmeter, M motor, G ground, D dot.
# ---------------------------------------------------------------------------

_DIRS = {"R": (1, 0), "L": (-1, 0), "U": (0, -1), "D": (0, 1)}


def _zigzag(p1, p2, steps=8):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-9:
        return [p1, p2]
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    amp = max(6.0, min(12.0, L * 0.12))
    pts = [p1]
    for i in range(1, steps):
        t = i / steps
        x, y = x1 + ux * L * t, y1 + uy * L * t
        side = 1 if i % 2 else -1
        if i == steps - 1:
            pts.append(p2)
        else:
            pts.append((x + nx * amp * side, y + ny * amp * side))
    pts.append(p2)
    return pts


def _battery(d, p1, p2, cells, ink, width):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    nx, ny = -uy, ux
    d.line([p1, (x1 + ux * L * 0.08, y1 + uy * L * 0.08)], fill=ink, width=width)
    d.line([p2, (x2 - ux * L * 0.08, y2 - uy * L * 0.08)], fill=ink, width=width)
    for i in range(cells):
        t = (i + 0.5) / cells
        x, y = x1 + ux * L * t, y1 + uy * L * t
        d.line([(x - ux * 4 - nx * 5, y - uy * 4 - ny * 5),
                (x - ux * 4 + nx * 5, y - uy * 4 + ny * 5)], fill=ink, width=width)
        d.line([(x + ux * 4 - nx * 10, y + uy * 4 - ny * 10),
                (x + ux * 4 + nx * 10, y + uy * 4 + ny * 10)], fill=ink, width=width)


def _component(d, ctype, p1, p2, ink, width=3):
    (x1, y1), (x2, y2) = p1, p2
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 1e-9:
        return
    ux, uy = (x2 - x1) / L, (y2 - y1) / L
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    c = ctype.lower()
    if c in ("w", "wire"):
        d.line([p1, p2], fill=ink, width=width)
    elif c in ("r", "resistor"):
        d.line(_zigzag(p1, p2), fill=ink, width=width, joint="curve")
    elif c in ("b", "battery"):
        _battery(d, p1, p2, 3, ink, width)
    elif c in ("c", "cell"):
        _battery(d, p1, p2, 1, ink, width)
    elif c in ("l", "bulb", "lamp"):
        r = max(10.0, min(16.0, L * 0.20))
        lead = min(r, L * 0.18)
        d.line([p1, (mx - ux * r, my - uy * r)], fill=ink, width=width)
        d.line([(mx + ux * r, my + uy * r), p2], fill=ink, width=width)
        d.ellipse([mx - r, my - r, mx + r, my + r], outline=ink, width=width)
        d.line([(mx - r, my - r), (mx + r, my + r)], fill=ink, width=width)
        d.line([(mx - r, my + r), (mx + r, my - r)], fill=ink, width=width)
    elif c in ("a", "ammeter", "v", "voltmeter"):
        r = max(12.0, min(18.0, L * 0.22))
        d.line([p1, (mx - ux * r, my - uy * r)], fill=ink, width=width)
        d.line([(mx + ux * r, my + uy * r), p2], fill=ink, width=width)
        d.ellipse([mx - r, my - r, mx + r, my + r], outline=ink, width=width)
        _text(d, (mx, my), "A" if c == "a" else "V", find_font(int(r * 1.1)), ink)
    elif c in ("m", "motor"):
        r = max(12.0, min(18.0, L * 0.22))
        d.line([p1, (mx - ux * r, my - uy * r)], fill=ink, width=width)
        d.line([(mx + ux * r, my + uy * r), p2], fill=ink, width=width)
        d.ellipse([mx - r, my - r, mx + r, my + r], outline=ink, width=width)
        _text(d, (mx, my), "M", find_font(int(r * 1.1)), ink)
    elif c in ("s", "switch"):
        px, py = x1 + ux * L * 0.35, y1 + uy * L * 0.35
        d.line([p1, (px, py)], fill=ink, width=width)
        dx, dy = (x2 - x1), (y2 - y1)
        ang = math.atan2(dy, dx) - math.radians(32)
        bl = L * 0.45
        bx, by = px + math.cos(ang) * bl, py + math.sin(ang) * bl
        d.line([(px, py), (bx, by)], fill=ink, width=width)
        _dot(d, p1, r=3, fill=ink)
    elif c in ("g", "ground"):
        d.line([(mx, my), (mx, my + 16)], fill=ink, width=width)
        d.line([(mx - 7, my + 16), (mx + 7, my + 16)], fill=ink, width=width)
        d.line([(mx - 11, my + 20), (mx + 11, my + 20)], fill=ink, width=width)
        d.line([(mx - 15, my + 24), (mx + 15, my + 24)], fill=ink, width=width)
    elif c in ("d", "dot"):
        _dot(d, (mx, my), r=5, fill=ink)
    else:
        die(f"未知电路元件：{c}（W/R/B/C/L/S/A/V/M/G/D）")


def _parse_pair(s):
    m = re.match(r"^\(?([-\d.]+)\s*,\s*([-\d.]+)\)?$", s.strip())
    if not m:
        die(f"坐标格式错误：{s}（应为 X,Y）")
    return float(m.group(1)), float(m.group(2))


def circuit_cmd(args):
    require_pil()
    if not args.spec:
        die("需要 --spec 电路描述")
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    if args.grid:
        _grid(d, W, H)
    ink = hex2rgb(args.ink)
    ox, oy = _parse_pair(args.origin)
    x, y = ox, oy
    tokens = [t for t in args.spec.split(";") if t.strip()]
    for tok in tokens:
        tok = tok.strip()
        if tok.lower().startswith("at"):
            x, y = _parse_pair(tok[2:])
            continue
        if tok.lower().startswith("lab"):
            rest = tok[3:].strip()
            if "@" in rest:
                txt, _, pos = rest.rpartition("@")
                lx, ly = _parse_pair(pos)
            elif ":" in rest:
                txt, _, rest2 = rest.partition(":")
                parts = rest2.split(":")
                if len(parts) >= 3 and parts[0].upper() in _DIRS:
                    dd = parts[0].upper()
                    ln = float(parts[1])
                    dx, dy = _DIRS[dd]
                    lx, ly = x + dx * ln, y + dy * ln
                else:
                    lx, ly = x, y
            else:
                txt, lx, ly = rest, x, y
            _text(d, (lx, ly), txt, find_font(args.font_size), ink)
            continue
        m = re.match(r"^([A-Za-z]+):\(([-\d.]+),([-\d.]+)\)-\(([-\d.]+),([-\d.]+)\)$", tok)
        if m:
            ctype = m.group(1)
            p1 = (float(m.group(2)), float(m.group(3)))
            p2 = (float(m.group(4)), float(m.group(5)))
            _component(d, ctype, p1, p2, ink, args.line_width)
            x, y = p2
            continue
        parts = tok.split(":")
        if len(parts) == 3 and parts[1].upper() in _DIRS:
            ctype, dirl, ln = parts[0], parts[1].upper(), float(parts[2])
            dx, dy = _DIRS[dirl]
            p1, p2 = (x, y), (x + dx * ln, y + dy * ln)
            _component(d, ctype, p1, p2, ink, args.line_width)
            x, y = p2
            continue
        die(f"电路语法错误：{tok}（示例 W:R:120 或 R:(100,200)-(300,200)）")
    img.save(args.out)
    print(f"电路图已生成：{args.out}")


# ---------------------------------------------------------------------------
# physics ray: optical ray diagrams (lens / mirror).
# ---------------------------------------------------------------------------

def _lens_symbol(d, lx, ax, ink, convex, span=95, width=3):
    d.line([(lx, ax - span), (lx, ax + span)], fill=ink, width=width)
    out = 14
    if convex:
        _head(d, (lx, ax - span), -math.pi / 2, out, ink, width)
        _head(d, (lx, ax + span), math.pi / 2, out, ink, width)
    else:
        _head(d, (lx, ax - span), math.pi / 2, out, ink, width)
        _head(d, (lx, ax + span), -math.pi / 2, out, ink, width)


def _emergent(d, lp, tip, virtual, ink, aux):
    if virtual is None:
        d.line([lp, (lp[0] + 150, lp[1])], fill=ink, width=2)
        _head(d, (lp[0] + 120, lp[1]), 0, 9, ink, 2)
        return
    if virtual:
        d.line([lp, (lp[0] + 150, lp[1])], fill=ink, width=2)
        _head(d, (lp[0] + 120, lp[1]), 0, 9, ink, 2)
        _dashed(d, lp, tip, fill=aux)
    else:
        dx, dy = tip[0] - lp[0], tip[1] - lp[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        ux, uy = dx / L, dy / L
        ext = (tip[0] + ux * 60, tip[1] + uy * 60)
        d.line([lp, ext], fill=ink, width=2)
        _head(d, tip, math.atan2(dy, dx), 9, ink, 2)


def _focal_mark(d, x, ax, label, ink, font):
    if x <= 20 or x >= 900:
        return
    d.line([(x, ax), (x, ax + 10)], fill=ink, width=2)
    d.line([(x - 5, ax + 10), (x + 5, ax + 10)], fill=ink, width=2)
    _text(d, (x, ax + 22), label, font, ink)


def _plane_mirror_cmd(d, W, ax, object_x, oh, ink, aux, font):
    mx = int(W * 0.30)
    d.line([(mx, ax - 100), (mx, ax + 100)], fill=ink, width=4)
    for yy in range(int(ax - 84), int(ax + 84), 16):
        d.line([(mx, yy), (mx + 9, yy - 6)], fill=ink, width=2)
    T = (object_x, ax - oh)
    _arrow(d, (object_x, ax), T, ink, width=3)
    _text(d, (object_x, ax + 22), "物", font, ink)
    vx, vy = 2 * mx - object_x, ax - oh
    _dashed(d, (vx, ax), (vx, vy), fill=aux)
    _head(d, (vx, vy), -math.pi / 2, 9, aux, 2)
    _text(d, (vx + 12, vy + 14), "虚像", font, aux)
    ym = ax - oh * 0.55
    _arrow(d, T, (mx, ym), ink, width=2)
    _dashed(d, (mx - 70, ym), (mx + 70, ym), fill=aux)
    _text(d, (mx - 86, ym + 14), "法线", font, aux)
    rv = (-(mx - object_x), ym - T[1])
    rl = math.hypot(*rv)
    ux, uy = rv[0] / rl, rv[1] / rl
    rx, ry = mx + ux * 120, ym + uy * 120
    _arrow(d, (mx, ym), (rx, ry), ink, width=2)
    _text(d, (mx + 26, ym + 20), "反射光线", font, ink)
    _text(d, (object_x + 14, T[1] - 18), "入射光线", font, ink)
    _text(d, (mx + 20, ax - 92), "平面镜", font, ink)


def ray_lens_cmd(args):
    require_pil()
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    if args.grid:
        _grid(d, W, H)
    ink = hex2rgb(args.ink)
    aux = hex2rgb(args.aux_color)
    font = find_font(args.font_size)
    ax = H * 0.60
    d.line([(30, ax), (W - 30, ax)], fill=ink, width=2)
    lens_x = int(W * 0.60)
    f = abs(args.focal or 90)
    if args.kind == "concave":
        f = -f
    object_x = args.object or int(lens_x - f * 2.2)
    oh = args.height
    if oh is None or oh <= 0:
        oh = 60
    T = (object_x, ax - oh)
    _arrow(d, (object_x, ax), T, ink, width=3)
    _text(d, (object_x, ax + 22), "物", font, ink)

    _lens_symbol(d, lens_x, ax, ink, convex=(args.kind == "convex"))
    for x, lb in ((lens_x - f, "F"), (lens_x - 2 * f, "2F"),
                  (lens_x + f, "F'"), (lens_x + 2 * f, "2F'")):
        _focal_mark(d, x, ax, lb, ink, font)
    u = lens_x - object_x
    if abs(u) < 1e-6 or abs(u - f) < 1e-6:
        virtual = None
    else:
        v = u * f / (u - f)
        m = -v / u
        ix = lens_x + v
        iy = ax - m * oh
        virtual = v < 0
    lp1 = (lens_x, T[1])
    _arrow(d, T, lp1, ink, width=2)
    lp2 = (lens_x, ax)
    _arrow(d, T, lp2, ink, width=2)
    far = lens_x + abs(f) if args.kind == "concave" else lens_x - abs(f)
    slope = (ax - T[1]) / max((far - object_x), 1e-6)
    y_hit = T[1] + slope * (lens_x - object_x)
    lp3 = (lens_x, y_hit)
    _arrow(d, T, lp3, ink, width=2)
    if virtual is None:
        for lp in (lp1, lp2, lp3):
            _emergent(d, lp, None, None, ink, aux)
        _text(d, (lens_x + 40, ax - 30), "不成像（平行射出）", font, ink)
    else:
        tip = (ix, iy)
        for lp in (lp1, lp2, lp3):
            _emergent(d, lp, tip, virtual, ink, aux)
        _arrow(d, (ix, ax), (ix, iy), aux if virtual else ink, width=3)
        _text(d, (ix + 12, iy + 16), "虚像" if virtual else "实像", font, ink)
    img.save(args.out)
    print(f"光路图已生成：{args.out}（{args.kind}）")


def ray_cmd(args):
    require_pil()
    if args.kind == "plane":
        W, H = args.width, args.height
        img = Image.new("RGB", (W, H), hex2rgb(args.background))
        d = ImageDraw.Draw(img)
        if args.grid:
            _grid(d, W, H)
        ink = hex2rgb(args.ink)
        aux = hex2rgb(args.aux_color)
        font = find_font(args.font_size)
        ax = H * 0.60
        d.line([(30, ax), (W - 30, ax)], fill=ink, width=2)
        oh = args.height if args.height and args.height > 0 else 60
        _plane_mirror_cmd(d, W, ax, args.object or int(W * 0.12), oh, ink, aux, font)
        img.save(args.out)
        print(f"光路图已生成：{args.out}（plane）")
        return 0
    return ray_lens_cmd(args)


# ---------------------------------------------------------------------------
# physics force: inclined plane free-body / on-plane force diagram.
# ---------------------------------------------------------------------------

def _force_diagram(d, bc, angle, glen, ink, font, show_friction,
                   show_pull, show_tension, cn):
    th = math.radians(angle)
    p = (math.cos(th), -math.sin(th))
    n = (math.sin(th), math.cos(th))
    fx, fy = bc
    _arrow(d, bc, (fx, fy + glen), ink, width=3)
    _text(d, (fx - 12, fy + glen + 6), "G" + ("(重力)" if cn else ""), font, ink)
    nl = glen * math.cos(th)
    _arrow(d, bc, (fx + n[0] * nl, fy + n[1] * nl), ink, width=3)
    _text(d, (fx + n[0] * nl + 12, fy + n[1] * nl - 8), "N" + ("(支持力)" if cn else ""), font, ink)
    fl = glen * 0.45
    if show_friction:
        _arrow(d, bc, (fx + p[0] * fl, fy + p[1] * fl), ink, width=3)
        _text(d, (fx + p[0] * fl + 14, fy + p[1] * fl - 6), "f" + ("(摩擦力)" if cn else ""), font, ink)
    if show_pull:
        pl = glen * 0.72
        _arrow(d, bc, (fx + p[0] * pl, fy + p[1] * pl), ink, width=3)
        _text(d, (fx + p[0] * pl + 16, fy + p[1] * pl - 6), "F" + ("(拉力)" if cn else ""), font, ink)
    if show_tension:
        tl = glen * 0.72
        _arrow(d, bc, (fx + p[0] * tl, fy + p[1] * tl), ink, width=3)
        _text(d, (fx + p[0] * tl + 16, fy + p[1] * tl - 6), "T" + ("(张力)" if cn else ""), font, ink)


def force_cmd(args):
    require_pil()
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    if args.grid:
        _grid(d, W, H)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    th = math.radians(args.angle)
    ground_y = H - 70
    d.line([(10, ground_y), (W - 10, ground_y)], fill=ink, width=6)
    p = (math.cos(th), -math.sin(th))
    origin = (70, ground_y)
    plane_len = min(W, H) * 0.5
    plane_end = (origin[0] + p[0] * plane_len, origin[1] + p[1] * plane_len)
    d.line([origin, plane_end], fill=ink, width=6)
    _arc_mark(d, origin, (origin[0] + 46, ground_y), (origin[0] + 46 * math.cos(th),
                                                      ground_y - 46 * math.sin(th)), 46, ink)
    _text(d, (origin[0] + 56, ground_y - 12), f"θ={args.angle}°", font, ink)
    bc = (origin[0] + p[0] * plane_len * 0.52, origin[1] + p[1] * plane_len * 0.52)
    c, s = math.cos(th), math.sin(th)
    bw, bh = 64, 40
    corners = []
    for wx, wy in ((-bw / 2, -bh / 2), (bw / 2, -bh / 2), (bw / 2, bh / 2), (-bw / 2, bh / 2)):
        corners.append((bc[0] + wx * c - wy * s, bc[1] + wx * s + wy * c))
    d.polygon(corners, outline=ink, width=4)
    _text(d, (bc[0], bc[1] - 34), "物体 m" if args.cn else "m", font, ink)
    _force_diagram(d, bc, args.angle, 95, ink, font,
                   args.friction, args.pull, args.tension, args.cn)
    if args.free:
        bc2 = (W * 0.80, ground_y - 140)
        d.polygon([(bc2[0] - 32, bc2[1] - 24), (bc2[0] + 32, bc2[1] - 24),
                   (bc2[0] + 32, bc2[1] + 24), (bc2[0] - 32, bc2[1] + 24)],
                  outline=ink, width=4)
        _text(d, (bc2[0], bc2[1] - 30), "m", font, ink)
        _force_diagram(d, bc2, args.angle, 75, ink, font,
                       args.friction, args.pull, args.tension, args.cn)
        _text(d, (W * 0.80, ground_y - 190), "隔离体（受力分析）", font, ink)
    img.save(args.out)
    print(f"受力图已生成：{args.out}（θ={args.angle}°）")


# ---------------------------------------------------------------------------
# physics object: common physical-setup scenes.
# ---------------------------------------------------------------------------

def _obj_incline(d, W, H, angle, ink, font, cn, aux):
    th = math.radians(angle)
    ground_y = H - 70
    d.line([(10, ground_y), (W - 10, ground_y)], fill=ink, width=6)
    p = (math.cos(th), -math.sin(th))
    origin = (70, ground_y)
    plane_len = min(W, H) * 0.45
    plane_end = (origin[0] + p[0] * plane_len, origin[1] + p[1] * plane_len)
    d.line([origin, plane_end], fill=ink, width=6)
    _arc_mark(d, origin, (origin[0] + 42, ground_y), (origin[0] + 42 * math.cos(th),
                                                      ground_y - 42 * math.sin(th)), 42, ink)
    _text(d, (origin[0] + 54, ground_y - 12), f"θ={angle}°", font, ink)
    bc = (origin[0] + p[0] * plane_len * 0.5, origin[1] + p[1] * plane_len * 0.5)
    c, s = math.cos(th), math.sin(th)
    corners = []
    for wx, wy in ((-40, -26), (40, -26), (40, 26), (-40, 26)):
        corners.append((bc[0] + wx * c - wy * s, bc[1] + wx * s + wy * c))
    d.polygon(corners, outline=ink, width=4)
    _text(d, (bc[0], bc[1] - 34), "物体" if cn else "m", font, ink)
    _text(d, (plane_end[0] - 40, plane_end[1] - 26), "斜面", font, ink)


def _obj_lever(d, W, H, ink, font, cn):
    ground_y = H - 60
    d.line([(10, ground_y), (W - 10, ground_y)], fill=ink, width=6)
    fx = W * 0.5
    d.polygon([(fx - 26, ground_y), (fx + 26, ground_y), (fx, ground_y - 34)],
              outline=ink, width=3)
    bar_y = ground_y - 40
    d.line([(W * 0.15, bar_y), (W * 0.85, bar_y)], fill=ink, width=6)
    d.line([(fx, ground_y - 30), (fx, bar_y)], fill=ink, width=3)
    for xf, lb in ((W * 0.30, "F₁"), (W * 0.70, "F₂")):
        d.rectangle([xf - 26, bar_y - 44, xf + 26, bar_y - 4], outline=ink, width=3)
        _text(d, (xf, bar_y - 24), lb, font, ink)
    _text(d, (fx, ground_y - 16), "支点", font, ink)
    y1 = bar_y + 30
    for xa, xb, lb in ((W * 0.16, fx, "L₁"), (fx, W * 0.84, "L₂")):
        _arrow(d, (xa, y1), (xb, y1), ink, width=2, both=True)
        _text(d, ((xa + xb) / 2, y1 + 16), lb, font, ink)


def _obj_pulley(d, W, H, ink, font, cn):
    d.rectangle([W * 0.18, 36, W * 0.82, 50], outline=ink, width=5)
    cx = W * 0.5
    py = 60
    d.ellipse([cx - 24, py - 24, cx + 24, py + 24], outline=ink, width=4)
    d.ellipse([cx - 6, py - 6, cx + 6, py + 6], outline=ink, width=2)
    d.line([(cx - 22, py), (cx + 22, py)], fill=ink, width=3)
    d.line([(cx, py - 24), (cx, 50)], fill=ink, width=3)
    d.line([(cx - 22, py), (cx - 22, py + 150)], fill=ink, width=3)
    d.line([(cx + 22, py), (cx + 22, py + 118)], fill=ink, width=3)
    d.rectangle([cx - 30, py + 150, cx + 14, py + 188], outline=ink, width=3)
    _text(d, (cx - 8, py + 169), "m", font, ink)
    _arrow(d, (cx + 22, py + 86), (cx + 22, py + 114), ink, width=3)
    _text(d, (cx + 34, py + 96), "F", font, ink)
    _text(d, (cx, py - 46), "定滑轮" if cn else "pulley", font, ink)


def _obj_pendulum(d, W, H, angle, ink, aux, font, cn):
    d.line([W * 0.2, 36, W * 0.8, 36], fill=ink, width=6)
    px, py = W * 0.4, 36
    _dot(d, (px, py), r=5, fill=ink)
    th = math.radians(angle)
    L0 = 180
    bx, by = px + L0 * math.sin(th), py + L0 * math.cos(th)
    _dashed(d, (px, py + 10), (px, py + L0), fill=aux)
    d.line([(px, py), (bx, by)], fill=ink, width=3)
    d.ellipse([bx - 16, by - 16, bx + 16, by + 16], outline=ink, width=3)
    _text(d, (bx + 22, by - 6), "小球 m" if cn else "m", font, ink)
    _text(d, ((px + bx) / 2 + 12, (py + by) / 2), "摆长", font, ink)
    _arc_mark(d, (px, py), (px + 40, py), (px + 40 * math.sin(th), py + 40 * math.cos(th)), 40, ink)
    _text(d, (px + 26, py + 24), f"θ={angle}°", font, ink)


def _obj_spring(d, W, H, ink, font, cn):
    d.line([W * 0.2, 36, W * 0.8, 36], fill=ink, width=6)
    cx = W * 0.5
    seg = 24
    pts = [(cx, 46)]
    y = 46
    amp = 22
    nseg = 6
    for i in range(nseg):
        y += seg
        off = amp if i % 2 == 0 else -amp
        pts.append((cx + off, y))
    pts.append((cx, y + seg / 2))
    d.line(pts, fill=ink, width=4, joint="curve")
    my = pts[-1][1]
    d.rectangle([cx - 32, my, cx + 32, my + 36], outline=ink, width=3)
    _text(d, (cx, my + 18), "m", font, ink)
    _text(d, (cx + 44, my + 18), "弹簧" if cn else "spring", font, ink)
    _arrow(d, (cx - 46, 46), (cx - 46, my - 10), ink, width=2, both=True)
    _text(d, (cx - 60, (46 + my) / 2), "x", font, ink)


def _obj_wave(d, W, H, args, ink, aux, font, cn):
    ax = H * 0.5
    x0 = W * 0.12
    wl = args.wavelength or 110
    amp = args.amplitude or 45
    cycles = args.cycles or 2
    span = wl * cycles
    if x0 + span > W - 40:
        cycles = max(1, int((W - 40 - x0) / wl))
        span = wl * cycles
    if args.longitudinal:
        base = 26
        n = int(span / base)
        for i in range(n):
            ph = 2 * math.pi * i * base / wl
            xs = x0 + i * base + amp * 0.25 * math.sin(ph)
            _dot(d, (xs, ax), r=4, fill=ink)
        _text(d, (x0 + span / 2, ax + 30), "纵波（密部/疏部）" if cn else "longitudinal", font, ink)
        for fx, lb in ((x0 + wl * 0.12, "密部"), (x0 + wl * 0.62, "疏部")):
            _text(d, (fx, ax - 22), lb, font, aux)
    else:
        _dashed(d, (x0 - 10, ax), (x0 + span + 10, ax), fill=aux)
        pts = []
        for i in range(int(span) + 1):
            ph = 2 * math.pi * i / wl
            pts.append((x0 + i, ax - amp * math.sin(ph)))
        d.line(pts, fill=ink, width=3)
        crest = (x0 + wl * 0.25, ax - amp)
        trough = (x0 + wl * 0.75, ax + amp)
        _dot(d, crest, r=4, fill=ink)
        _dot(d, trough, r=4, fill=ink)
        _text(d, (crest[0], crest[1] - 16), "波峰", font, ink)
        _text(d, (trough[0], trough[1] + 16), "波谷", font, ink)
        _arrow(d, (x0 + span, ax - amp), (x0 + span + 40, ax - amp), ink, width=3)
        _text(d, (x0 + span + 24, ax - amp - 14), "v", font, ink)
        yb = ax + 34
        _arrow(d, (x0, yb), (x0 + wl, yb), ink, width=2, both=True)
        _text(d, (x0 + wl / 2, yb + 16), "λ", font, ink)
        _arrow(d, (crest[0], ax), (crest[0], crest[1]), ink, width=2, both=True)
        _text(d, (crest[0] + 10, (ax + crest[1]) / 2), "A", font, ink)


def object_cmd(args):
    require_pil()
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    aux = hex2rgb(args.aux_color)
    font = find_font(args.font_size)
    scene = args.scene
    if scene == "incline":
        _obj_incline(d, W, H, args.angle, ink, font, args.cn, aux)
    elif scene == "lever":
        _obj_lever(d, W, H, ink, font, args.cn)
    elif scene == "pulley":
        _obj_pulley(d, W, H, ink, font, args.cn)
    elif scene == "pendulum":
        _obj_pendulum(d, W, H, args.angle, ink, aux, font, args.cn)
    elif scene == "spring":
        _obj_spring(d, W, H, ink, font, args.cn)
    elif scene == "wave":
        _obj_wave(d, W, H, args, ink, aux, font, args.cn)
    else:
        die(f"未知实物场景：{scene}（可选 incline/lever/pulley/pendulum/spring/wave）")
    img.save(args.out)
    print(f"实物图已生成：{args.out}（{scene}）")


# ---------------------------------------------------------------------------
# math figure: geometry DSL.
#   pt A 100,380              define point
#   mid D A B                 define midpoint of A-B
#   line A-B                  solid segment
#   ray A-B                   ray from A through B to edge
#   ext A-B                   dashed extension line through A and B
#   aux A-B                   dashed auxiliary segment (辅助线)
#   arrow A-B                 arrow segment (vector)
#   circle C 120              circle centered C radius 120
#   ang C A B [deg]           angle arc at C between rays to A and B
#   right C A B               right-angle mark at C
#   eq A-B C-D                one equality tick on both segments
#   eq2 / eq3                 two / three ticks
#   par A-B C-D               parallel chevrons on both segments
#   dot A                     draw a dot at point A
#   lab 名称@x,y              draw text at position
# ---------------------------------------------------------------------------

def _segpts(s, pts):
    a, _, b = s.partition("-")
    if a not in pts or b not in pts:
        die(f"未知点：{s}（已定义 {', '.join(pts)}）")
    return pts[a], pts[b]


def _extend_ray(p1, p2, W, H):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return p2
    t = max(1.0, W / max(abs(dx), 1e-9), H / max(abs(dy), 1e-9))
    return (p1[0] + dx * t, p1[1] + dy * t)


def figure_cmd(args):
    require_pil()
    if not args.spec:
        die("需要 --spec 几何描述")
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    if args.grid:
        _grid(d, W, H)
    ink = hex2rgb(args.ink)
    aux = hex2rgb(args.aux_color)
    font = find_font(args.font_size)
    pts = {}
    tokens = [t for t in args.spec.split(";") if t.strip()]
    for t in tokens:
        parts = t.split()
        if not parts:
            continue
        op = parts[0].lower()
        if op == "pt" and len(parts) >= 3:
            pts[parts[1]] = _parse_pair(parts[2])
        elif op == "mid" and len(parts) >= 4:
            a = pts.get(parts[2])
            b = pts.get(parts[3])
            if a is None or b is None:
                die(f"mid 需要已定义的点：{t}")
            pts[parts[1]] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    used = set()
    labeled = set()
    for t in tokens:
        parts = t.split()
        if not parts:
            continue
        op = parts[0].lower()
        if op in ("pt", "mid"):
            continue
        if op == "line" and len(parts) >= 2:
            p1, p2 = _segpts(parts[1], pts)
            d.line([p1, p2], fill=ink, width=args.line_width)
            used |= {parts[1].partition("-")[0], parts[1].partition("-")[2]}
        elif op == "ray" and len(parts) >= 2:
            p1, p2 = _segpts(parts[1], pts)
            d.line([p1, _extend_ray(p1, p2, W, H)], fill=ink, width=args.line_width)
        elif op == "ext" and len(parts) >= 2:
            p1, p2 = _segpts(parts[1], pts)
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            t = max(1.0, W / max(abs(dx), 1e-9), H / max(abs(dy), 1e-9))
            q1 = (p1[0] - dx * t, p1[1] - dy * t)
            q2 = (p2[0] + dx * t, p2[1] + dy * t)
            _dashed(d, q1, q2, fill=aux, width=args.line_width)
        elif op == "aux" and len(parts) >= 2:
            p1, p2 = _segpts(parts[1], pts)
            _dashed(d, p1, p2, fill=aux, width=args.line_width)
        elif op == "arrow" and len(parts) >= 2:
            p1, p2 = _segpts(parts[1], pts)
            _arrow(d, p1, p2, ink, width=args.line_width, head=12)
        elif op == "dot" and len(parts) >= 2:
            for name in parts[1:]:
                if name not in pts:
                    die(f"未知点：{name}")
                point = pts[name]
                _dot(d, point, r=args.point_radius, fill=ink)
                if name not in labeled:
                    _text(d, (point[0] + 14, point[1] - 14), name, font, ink)
                    labeled.add(name)
        elif op == "circle" and len(parts) >= 3:
            c = pts.get(parts[1])
            if c is None:
                die(f"未知点：{parts[1]}")
            r = float(parts[2])
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=ink, width=args.line_width)
        elif op == "ang" and len(parts) >= 4:
            v, a, b = pts.get(parts[1]), pts.get(parts[2]), pts.get(parts[3])
            if v is None or a is None or b is None:
                die(f"ang 需要已定义的点：{t}")
            _arc_mark(d, v, a, b, args.angle_radius, ink)
            if len(parts) >= 5:
                va = math.atan2(a[1] - v[1], a[0] - v[0])
                vb = math.atan2(b[1] - v[1], b[0] - v[0])
                mid = (va + vb) / 2
                rr = args.angle_radius + 16
                _text(d, (v[0] + rr * math.cos(mid), v[1] + rr * math.sin(mid)),
                      parts[4], font, ink)
        elif op == "right" and len(parts) >= 4:
            v, a, b = pts.get(parts[1]), pts.get(parts[2]), pts.get(parts[3])
            if v is None or a is None or b is None:
                die(f"right 需要已定义的点：{t}")
            _right_mark(d, v, a, b, ink, size=args.angle_radius)
        elif op in ("eq", "eq2", "eq3") and len(parts) >= 3:
            nticks = {"eq": 1, "eq2": 2, "eq3": 3}[op]
            for seg in parts[1:]:
                p1, p2 = _segpts(seg, pts)
                _eq_ticks(d, p1, p2, nticks, ink, width=args.line_width)
        elif op == "par" and len(parts) >= 3:
            for seg in parts[1:]:
                p1, p2 = _segpts(seg, pts)
                _par_chevrons(d, p1, p2, ink, width=args.line_width)
        elif op == "lab" and len(parts) >= 2:
            rest = parts[1]
            if "@" not in rest:
                die(f"lab 格式应为 文本@x,y：{t}")
            txt, _, pos = rest.rpartition("@")
            lx, ly = _parse_pair(pos)
            _text(d, (lx, ly), txt, font, ink)
        else:
            die(f"未知几何指令：{t}")
    if args.dots:
        for name in sorted(used - labeled):
            if name in pts:
                _dot(d, pts[name], r=args.point_radius, fill=ink)
                _text(d, (pts[name][0] + 14, pts[name][1] - 14), name, font, ink)
    img.save(args.out)
    print(f"几何图已生成：{args.out}")


# ---------------------------------------------------------------------------
# math func / axes: coordinate-system plotting with auxiliary elements.
# ---------------------------------------------------------------------------

def _eval_fn(expr, x):
    require_np()
    if len(expr) > 1000:
        raise ValueError("函数表达式过长")
    ns = {
        "pi": math.pi, "e": math.e, "inf": float("inf"),
        "sin": np.sin, "cos": np.cos, "tan": np.tan,
        "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
        "exp": np.exp, "log": np.log, "log10": np.log10, "log2": np.log2,
        "sqrt": np.sqrt, "abs": np.abs, "floor": np.floor, "ceil": np.ceil,
    }
    ns["x"] = x
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in ns and not callable(ns[node.id]):
            return ns[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.Call) and not node.keywords and len(node.args) == 1:
            name = node.func.id if isinstance(node.func, ast.Name) else None
            # Compatibility with documented NumPy-style math calls, never arbitrary attributes.
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "np":
                name = node.func.attr
            if name in ns and callable(ns[name]):
                return ns[name](visit(node.args[0]))
        raise ValueError("表达式只允许数字、x、数学常量、四则运算和白名单数学函数")
    try:
        tree = ast.parse(expr, mode="eval")
        with np.errstate(all="ignore"):
            result = visit(tree.body)
            return np.broadcast_to(np.asarray(result, dtype=float), np.shape(x))
    except (SyntaxError, TypeError, OverflowError, ZeroDivisionError, RecursionError) as exc:
        raise ValueError(f"无效函数表达式：{expr}") from exc


def _plot_setup(d, W, H, xmin, xmax, ymin, ymax, grid_on, ink):
    if not all(math.isfinite(v) for v in (xmin, xmax, ymin, ymax)) or xmin >= xmax or ymin >= ymax:
        raise ValueError("坐标范围必须为有限数，且 min < max")
    xl, xr = 58, W - 22
    yt, yb = 26, H - 44

    def px(x):
        return xl + (x - xmin) / (xmax - xmin) * (xr - xl)

    def py(y):
        return yb - (y - ymin) / (ymax - ymin) * (yb - yt)

    if grid_on:
        for gx in range(int(math.ceil(xmin)), int(math.floor(xmax)) + 1):
            if xmin < gx < xmax:
                d.line([(px(gx), yt), (px(gx), yb)], fill=(228, 228, 232), width=1)
        for gy in range(int(math.ceil(ymin)), int(math.floor(ymax)) + 1):
            if ymin < gy < ymax:
                d.line([(xl, py(gy)), (xr, py(gy))], fill=(228, 228, 232), width=1)
    if ymin < 0 < ymax:
        d.line([(xl, py(0)), (xr, py(0))], fill=ink, width=2)
    if xmin < 0 < xmax:
        d.line([(px(0), yt), (px(0), yb)], fill=ink, width=2)
    if ymin < 0 < ymax:
        _head(d, (xr - 1, py(0)), 0, 10, ink, 2)
    if xmin < 0 < xmax:
        _head(d, (px(0), yt + 1), -math.pi / 2, 10, ink, 2)
    return px, py


def _tick_labels(d, px, py, xmin, xmax, ymin, ymax, ink, font, show_axis):
    for gx in range(int(math.ceil(xmin)), int(math.floor(xmax)) + 1):
        if gx == 0 or not (xmin < gx < xmax):
            continue
        xv = px(gx)
        if not show_axis or not (ymin < 0 < ymax):
            continue
        y0 = py(0)
        d.line([(xv, y0 - 4), (xv, y0 + 4)], fill=ink, width=2)
        _text(d, (xv, y0 + 14), str(gx), font, ink)
    for gy in range(int(math.ceil(ymin)), int(math.floor(ymax)) + 1):
        if gy == 0 or not (ymin < gy < ymax):
            continue
        yv = py(gy)
        if show_axis and xmin < 0 < xmax:
            x0 = px(0)
            d.line([(x0 - 4, yv), (x0 + 4, yv)], fill=ink, width=2)
            _text(d, (x0 - 14, yv), str(gy), font, ink)


def func_cmd(args):
    require_pil()
    require_np()
    W, H = args.width, args.height
    xs = np.linspace(args.xmin, args.xmax, 1600)
    ys = _eval_fn(args.expr, xs)
    finite = np.isfinite(ys)
    if not np.any(finite):
        die(f"函数在区间内无有限值：{args.expr}")
    ymin = args.ymin
    ymax = args.ymax
    if ymin is None or ymax is None:
        f = ys[finite]
        lo, hi = float(f.min()), float(f.max())
        span = max(1e-6, hi - lo)
        pad = span * 0.12
        if ymin is None:
            ymin = math.floor(lo - pad)
        if ymax is None:
            ymax = math.ceil(hi + pad)
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    aux = hex2rgb(args.aux_color)
    font = find_font(args.font_size)
    px, py = _plot_setup(d, W, H, args.xmin, args.xmax, ymin, ymax, args.grid, ink)
    pts = []
    for i in range(len(xs)):
        if not finite[i] or (pts and abs(float(ys[i]) - float(ys[i - 1])) > (ymax - ymin)):
            if len(pts) > 1:
                d.line(pts, fill=ink, width=3)
            pts = []
            continue
        pts.append((px(float(xs[i])), py(float(ys[i]))))
    if len(pts) > 1:
        d.line(pts, fill=ink, width=3)
    show_axis = args.xmin < 0 < args.xmax and ymin < 0 < ymax
    if show_axis:
        _tick_labels(d, px, py, args.xmin, args.xmax, ymin, ymax, ink, font, True)
    if args.tangent is not None:
        x0 = float(args.tangent)
        y0 = float(_eval_fn(args.expr, np.array([x0]))[0])
        h = max(1e-4, (args.xmax - args.xmin) * 1e-4)
        slope = (float(_eval_fn(args.expr, np.array([x0 + h]))[0]) -
                 float(_eval_fn(args.expr, np.array([x0 - h]))[0])) / (2 * h)
        _dashed(d, (px(args.xmin), py(y0 + slope * (args.xmin - x0))),
                (px(args.xmax), py(y0 + slope * (args.xmax - x0))), fill=aux, width=2)
        _text(d, (px(x0) + 10, py(y0) - 12), f"切线 y'={slope:.2f}", font, aux)
    if args.asymptote_v is not None:
        xa = float(args.asymptote_v)
        if args.xmin < xa < args.xmax:
            _dashed(d, (px(xa), 26), (px(xa), H - 44), fill=aux, width=2)
            _text(d, (px(xa) + 8, 26), f"x={args.asymptote_v}", font, aux)
    if args.asymptote_h is not None:
        ya = float(args.asymptote_h)
        if ymin < ya < ymax:
            _dashed(d, (58, py(ya)), (W - 22, py(ya)), fill=aux, width=2)
            _text(d, (W - 90, py(ya) - 14), f"y={args.asymptote_h}", font, aux)
    if args.roots:
        roots = []
        for i in range(len(xs) - 1):
            if finite[i] and finite[i + 1] and ys[i] * ys[i + 1] < 0:
                lo, hi = float(xs[i]), float(xs[i + 1])
                flo = float(ys[i])
                for _ in range(40):
                    mid = (lo + hi) / 2
                    fm = float(_eval_fn(args.expr, np.array([mid]))[0])
                    if flo * fm <= 0:
                        hi = mid
                    else:
                        lo, flo = mid, fm
                candidate = (lo + hi) / 2
                residual = float(_eval_fn(args.expr, np.array([candidate]))[0])
                if math.isfinite(residual) and abs(residual) < 1e-6:
                    roots.append(candidate)
        for r in roots:
            if args.xmin < r < args.xmax and show_axis:
                _dot(d, (px(r), py(0)), r=5, fill=ink)
                _text(d, (px(r) + 8, py(0) + 14), f"x≈{r:.2f}", font, ink)
    label = args.label or ("y = " + args.expr)
    _text(d, (66, 6), label, font, ink)
    if args.axis_labels:
        if ymin < 0 < ymax:
            _text(d, (W - 18, py(0) - 6), "x", font, ink)
        if args.xmin < 0 < args.xmax:
            _text(d, (px(0) + 6, 18), "y", font, ink)
    img.save(args.out)
    print(f"函数图已生成：{args.out}（y = {args.expr}）")


def axes_cmd(args):
    require_pil()
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    px, py = _plot_setup(d, W, H, args.xmin, args.xmax, args.ymin, args.ymax,
                         args.grid, ink)
    show = args.xmin < 0 < args.xmax and args.ymin < 0 < args.ymax
    if show:
        _tick_labels(d, px, py, args.xmin, args.xmax, args.ymin, args.ymax,
                     ink, font, True)
        _text(d, (W - 18, py(0) - 6), "x", font, ink)
        _text(d, (px(0) + 6, 18), "y", font, ink)
        _text(d, (px(0) - 16, py(0) + 14), "O", font, ink)
    img.save(args.out)
    print(f"坐标系已生成：{args.out}")


def _project3(p, yaw, pitch, scale, center):
    x, y, z = p
    a, b = math.radians(yaw), math.radians(pitch)
    x1 = x * math.cos(a) - z * math.sin(a)
    z1 = x * math.sin(a) + z * math.cos(a)
    y1 = y * math.cos(b) - z1 * math.sin(b)
    return (center[0] + x1 * scale, center[1] - y1 * scale)


def _poly3(d, points, fill, outline, width):
    d.polygon(points, fill=fill)
    d.line(points + [points[0]], fill=outline, width=width, joint="curve")


def _solid3d_faces(d, vertices, faces, yaw, pitch, scale, center, palette, ink, width):
    items = []
    for index, face in enumerate(faces):
        depth = sum(vertices[i][2] for i in face) / len(face)
        items.append((depth, index, face))
    for _, index, face in sorted(items):
        pts = [_project3(vertices[i], yaw, pitch, scale, center) for i in face]
        _poly3(d, pts, palette[index % len(palette)], ink, width)


def three_cmd(args):
    require_pil()
    W, H = args.width, args.height
    img = Image.new("RGB", (W, H), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    palette = [hex2rgb(c) for c in args.palette.split(",")]
    center = (W / 2, H / 2 + 18)
    scale = args.scale
    yaw, pitch = args.yaw, args.pitch
    font = find_font(args.font_size)
    if args.grid:
        _grid(d, W, H, 24)
    scene = args.scene
    if scene == "axes":
        for p1, p2, label in [((-3, 0, 0), (3, 0, 0), "X"), ((0, -3, 0), (0, 3, 0), "Y"), ((0, 0, -3), (0, 0, 3), "Z")]:
            q1, q2 = _project3(p1, yaw, pitch, scale, center), _project3(p2, yaw, pitch, scale, center)
            _arrow(d, q1, q2, ink, width=3)
            _text(d, q2, label, font, ink)
    elif scene == "cube":
        v = [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]
        faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7), (1, 5, 6, 2), (0, 3, 7, 4)]
        _solid3d_faces(d, v, faces, yaw, pitch, scale, center, palette, ink, args.line_width)
    elif scene in ("pyramid", "prism"):
        if scene == "pyramid":
            v = [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), (0, 1.2, 0)]
            faces = [(0, 1, 2, 3), (0, 4, 1), (1, 4, 2), (2, 4, 3), (3, 4, 0)]
        else:
            v = [(-1, -1, -0.8), (1, -1, -0.8), (0.2, 1, -0.8), (-0.8, 1, -0.8), (-1, -1, 0.8), (1, -1, 0.8), (0.2, 1, 0.8), (-0.8, 1, 0.8)]
            faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        _solid3d_faces(d, v, faces, yaw, pitch, scale, center, palette, ink, args.line_width)
    elif scene in ("cylinder", "sphere"):
        n = 24
        if scene == "cylinder":
            v = []
            for y in (-1.2, 1.2):
                v += [(math.cos(2 * math.pi * i / n), y, math.sin(2 * math.pi * i / n)) for i in range(n)]
            faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
            _solid3d_faces(d, v, faces, yaw, pitch, scale, center, palette, ink, args.line_width)
            for ring in (0, n):
                pts = [_project3(v[ring + i], yaw, pitch, scale, center) for i in range(n)]
                d.line(pts + [pts[0]], fill=ink, width=args.line_width)
        else:
            for lat in range(1, 8):
                phi = math.pi * lat / 8
                pts = [_project3((math.sin(phi) * math.cos(2 * math.pi * i / n), math.cos(phi), math.sin(phi) * math.sin(2 * math.pi * i / n)), yaw, pitch, scale, center) for i in range(n)]
                d.line(pts + [pts[0]], fill=ink, width=1)
            for i in range(12):
                theta = 2 * math.pi * i / 12
                pts = [_project3((math.sin(phi) * math.cos(theta), math.cos(phi), math.sin(phi) * math.sin(theta)), yaw, pitch, scale, center) for phi in [math.pi * j / 24 for j in range(25)]]
                d.line(pts, fill=ink, width=1)
    else:
        die(f"未知 3D 场景：{scene}（可选 axes/cube/pyramid/prism/cylinder/sphere）")
    if args.label:
        _text(d, (W / 2, 24), args.label, font, ink)
    img.save(args.out)
    print(f"3D 图已生成：{args.out}（{scene}）")


def _bond_line(d, p1, p2, order, color, width):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy) or 1
    nx, ny = -dy / length, dx / length
    for i in range(order):
        off = (i - (order - 1) / 2) * 6
        d.line([(p1[0] + nx * off, p1[1] + ny * off), (p2[0] + nx * off, p2[1] + ny * off)], fill=color, width=width)


def chem_molecule_cmd(args):
    require_pil()
    img = Image.new("RGB", (args.width, args.height), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    atoms = {}
    for item in args.atoms.split(";"):
        name, _, pos = item.partition(":")
        if not name or name in atoms:
            raise ValueError(f"原子 ID 不能为空或重复：{name}；同元素请使用 O1、O2 等独立 ID")
        atoms[name] = _parse_pair(pos)
    for item in args.bonds.split(";") if args.bonds else []:
        parts = item.split(":")
        if len(parts) < 2 or parts[0] not in atoms or parts[1] not in atoms:
            die(f"化学键格式错误：{item}")
        order = int(parts[2]) if len(parts) > 2 else 1
        if order not in (1, 2, 3):
            raise ValueError("化学键级必须为 1、2 或 3")
        _bond_line(d, atoms[parts[0]], atoms[parts[1]], order, ink, args.line_width)
    radii = {"H": 12, "C": 18, "N": 17, "O": 16, "F": 15, "Cl": 19, "Na": 20, "S": 19}
    for name, pos in atoms.items():
        element = re.match(r"[A-Z][a-z]?", name.split("@")[0])
        element = element.group(0) if element else name.split("@")[0]
        r = radii.get(element, 17) if args.model == "ball" else 2
        if args.model == "ball":
            d.ellipse([pos[0] - r, pos[1] - r, pos[0] + r, pos[1] + r], fill=hex2rgb(args.atom_color), outline=ink, width=2)
        _chem_text(d, pos, element, font, ink)
    if args.label:
        _text(d, (args.width / 2, 24), args.label, font, ink)
    img.save(args.out)
    print(f"分子图已生成：{args.out}")


def chem_cell_cmd(args):
    require_pil()
    img = Image.new("RGB", (args.width, args.height), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    pts = [(160, 390), (440, 390), (600, 300), (320, 300), (160, 170), (440, 170), (600, 80), (320, 80)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]
    for a, b in edges:
        d.line([pts[a], pts[b]], fill=ink, width=3)
    sites = [(160, 390), (440, 390), (600, 300), (320, 300), (160, 170), (440, 170), (600, 80), (320, 80)]
    if args.kind == "bcc":
        sites.append((380, 235))
    if args.kind == "fcc":
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        sites += [(sum(pts[i][0] for i in face) / 4, sum(pts[i][1] for i in face) / 4)
                  for face in faces]
    for p in sites:
        _dot(d, p, 8, hex2rgb(args.site_color))
    _text(d, (args.width / 2, 30), args.kind.upper() + " 晶胞", font, ink)
    img.save(args.out)
    print(f"晶胞图已生成：{args.out}（{args.kind}）")


def chem_reaction_cmd(args):
    require_pil()
    img = Image.new("RGB", (args.width, args.height), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    left, right = args.equation.split("->", 1) if "->" in args.equation else args.equation.split("→", 1)
    _chem_text(d, (args.width * 0.25, args.height * 0.5), left.strip(), font, ink)
    _arrow(d, (args.width * 0.42, args.height * 0.5), (args.width * 0.62, args.height * 0.5), ink, width=3)
    _chem_text(d, (args.width * 0.52, args.height * 0.40), args.condition, font, ink)
    _chem_text(d, (args.width * 0.75, args.height * 0.5), right.strip(), font, ink)
    img.save(args.out)
    print(f"反应式图已生成：{args.out}")


def chem_apparatus_cmd(args):
    require_pil()
    img = Image.new("RGB", (args.width, args.height), hex2rgb(args.background))
    d = ImageDraw.Draw(img)
    ink = hex2rgb(args.ink)
    font = find_font(args.font_size)
    if args.kind == "beaker":
        d.line([(180, 120), (180, 390), (520, 390), (520, 120)], fill=ink, width=4)
        d.line([(180, 120), (220, 130), (480, 130), (520, 120)], fill=ink, width=4)
        d.line([(210, 270), (490, 270)], fill=hex2rgb(args.liquid_color), width=8)
        _text(d, (350, 440), "烧杯", font, ink)
    elif args.kind == "flask":
        d.line([(300, 100), (300, 220), (190, 390), (510, 390), (400, 220), (400, 100)], fill=ink, width=4, joint="curve")
        d.line([(260, 100), (440, 100)], fill=ink, width=4)
        d.polygon([(220, 330), (480, 330), (510, 390), (190, 390)], fill=hex2rgb(args.liquid_color))
        _text(d, (350, 440), "锥形瓶", font, ink)
    elif args.kind == "test-tube":
        d.line([(220, 100), (220, 380)], fill=ink, width=4)
        d.line([(380, 100), (380, 380)], fill=ink, width=4)
        d.line([(212, 100), (388, 100)], fill=ink, width=4)
        d.arc([220, 300, 380, 460], 0, 180, fill=ink, width=4)
        d.line([(220, 380), (380, 380)], fill=hex2rgb(args.liquid_color), width=10)
        _text(d, (300, 490), "试管", font, ink)
    else:
        die(f"未知化学器材：{args.kind}（可选 beaker/flask/test-tube）")
    img.save(args.out)
    print(f"化学器材图已生成：{args.out}（{args.kind}）")
