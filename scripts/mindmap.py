"""Offline, measured tree layout shared by SVG and PNG mind maps."""
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from fontlib import find_font, find_cjk_font

MAX_NODES = 500
MAX_DEPTH = 12
COLORS = ["#2563eb", "#0f766e", "#b45309", "#9333ea", "#be185d", "#0369a1"]


@dataclass
class Node:
    text: str
    children: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    width: float = 0
    height: float = 0
    span: float = 0
    x: float = 0
    y: float = 0
    color: str = "#2563eb"


def parse_json(data, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    if count[0] > MAX_NODES or depth > MAX_DEPTH:
        raise ValueError(f"思维导图最多 {MAX_NODES} 个节点、{MAX_DEPTH} 层分支；请拆分子图")
    if isinstance(data, str):
        data = {"text": data}
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        raise ValueError('节点需为字符串或 {"text": "主题", "children": [...]}')
    if set(data) - {"text", "children"}:
        raise ValueError("节点只支持 text 和 children 字段")
    text = data["text"].strip()
    if not text or len(text) > 500 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", text):
        raise ValueError("节点文本不能为空，最长 500 字符，且不能含非法控制字符")
    children = data.get("children", [])
    if not isinstance(children, list):
        raise ValueError("children 必须为数组")
    return Node(text, [parse_json(child, depth + 1, count) for child in children])


def parse_markdown(source):
    """One # root, subheadings, and lists indented by two spaces per level."""
    root = None
    headings, bullets = [], []
    for number, raw in enumerate(source.splitlines(), 1):
        if not raw.strip():
            continue
        if "\t" in raw:
            raise ValueError(f"第 {number} 行：缩进请使用两个空格，不要使用 Tab")
        heading = re.fullmatch(r"(#{1,6})\s+(.+?)\s*", raw)
        bullet = re.fullmatch(r"( *)(?:[-+*]|\d+[.)])\s+(.+?)\s*", raw)
        if heading:
            level, text = len(heading[1]), heading[2]
            node = {"text": text, "children": []}
            bullets = []
            if level == 1:
                if root is not None:
                    raise ValueError(f"第 {number} 行：只允许一个 # 中心主题")
                root, headings = node, [node]
            else:
                if root is None or level > len(headings) + 1:
                    raise ValueError(f"第 {number} 行：标题层级不能跳级")
                headings = headings[:level - 1]
                headings[-1]["children"].append(node)
                headings.append(node)
        elif bullet and root is not None:
            indent = len(bullet[1])
            if indent % 2 or indent // 2 > len(bullets):
                raise ValueError(f"第 {number} 行：列表每层缩进两个空格，不能跳级")
            level = indent // 2
            node = {"text": bullet[2], "children": []}
            parent = headings[-1] if level == 0 else bullets[level - 1]
            parent["children"].append(node)
            bullets = bullets[:level] + [node]
        else:
            raise ValueError(f"第 {number} 行：请使用 # 中心主题、下级标题或缩进列表；不支持段落/代码块")
    if root is None:
        raise ValueError("Markdown 需要一个 # 中心主题")
    return parse_json(root)


def load_tree(path):
    source = Path(path).read_text(encoding="utf-8-sig")
    if Path(path).suffix.lower() == ".json":
        return parse_json(json.loads(source))
    return parse_markdown(source)


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def wrap_text(text, draw, font, width):
    lines = []
    for paragraph in text.splitlines():
        line = ""
        for char in paragraph:
            if line and draw.textlength(line + char, font=font) > width:
                # Prefer word boundaries when available; CJK wraps by character.
                space = line.rfind(" ")
                if space > len(line) // 2:
                    lines.append(line[:space].rstrip())
                    line = line[space + 1:] + char
                else:
                    lines.append(line.rstrip())
                    line = char
            else:
                line += char
        lines.append(line.rstrip())
    return lines or [""]


def layout(root, draw, font, font_size=20, max_width=220, mode="balanced"):
    line_height = math.ceil(font_size * 1.5)
    for node in walk(root):
        node.lines = wrap_text(node.text, draw, font, max_width)
        node.width = math.ceil(max(draw.textlength(line, font=font) for line in node.lines)) + 32
        node.height = len(node.lines) * line_height + 20
    gap_y, gap_x = 20, 64

    def measure(node):
        spans = [measure(child) for child in node.children]
        node.span = max(node.height, sum(spans) + gap_y * max(0, len(spans) - 1))
        return node.span

    def place(node, edge, top, direction, color):
        node.x = edge if direction == 1 else edge - node.width
        node.y = top + node.span / 2 - node.height / 2
        node.color = color
        children_height = sum(child.span for child in node.children) + gap_y * max(0, len(node.children) - 1)
        cursor = top + (node.span - children_height) / 2
        for child in node.children:
            place(child, node.x + node.width + gap_x if direction == 1 else node.x - gap_x,
                  cursor, direction, color)
            cursor += child.span + gap_y

    left, right = [], []
    totals = [0, 0]
    for i, child in enumerate(root.children):
        measure(child)
        side = 1 if mode == "right" else 0 if mode == "left" else (0 if totals[0] < totals[1] else 1)
        (left if side == 0 else right).append((child, COLORS[i % len(COLORS)]))
        totals[side] += child.span + gap_y
    root.x, root.y = -root.width / 2, -root.height / 2
    for group, direction in ((left, -1), (right, 1)):
        cursor = -(sum(child.span for child, _ in group) + gap_y * max(0, len(group) - 1)) / 2
        for child, color in group:
            place(child, direction * (root.width / 2 + gap_x), cursor, direction, color)
            cursor += child.span + gap_y
    nodes = list(walk(root))
    min_x, min_y = min(n.x for n in nodes), min(n.y for n in nodes)
    max_x, max_y = max(n.x + n.width for n in nodes), max(n.y + n.height for n in nodes)
    margin = 40
    for node in nodes:
        node.x += margin - min_x
        node.y += margin - min_y
    return math.ceil(max_x - min_x + 2 * margin), math.ceil(max_y - min_y + 2 * margin)


def curves(root):
    for parent in walk(root):
        for child in parent.children:
            right = child.x > parent.x
            x1 = parent.x + parent.width if right else parent.x
            x2 = child.x if right else child.x + child.width
            y1, y2 = parent.y + parent.height / 2, child.y + child.height / 2
            mid = (x1 + x2) / 2
            yield ((x1, y1), (mid, y1), (mid, y2), (x2, y2)), child.color


def render_svg(root, size, font_size, dark):
    bg, ink, fill = ("#111827", "#f3f4f6", "#1f2937") if dark else ("#f8fafc", "#172033", "#ffffff")
    width, height = size
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
           f'<title>{escape(root.text)}</title>', f'<rect width="{width}" height="{height}" fill="{bg}"/>']
    for points, color in curves(root):
        a, b, c, d = points
        svg.append(f'<path d="M {a[0]} {a[1]} C {b[0]} {b[1]}, {c[0]} {c[1]}, {d[0]} {d[1]}" fill="none" stroke="{color}" stroke-width="3"/>')
    font = find_font(font_size)
    family = escape(font.getname()[0], {'"': '&quot;'}) if hasattr(font, "getname") else "sans-serif"
    for node in walk(root):
        is_root = node is root
        svg.append(f'<g><rect x="{node.x}" y="{node.y}" width="{node.width}" height="{node.height}" rx="10" fill="{node.color if is_root else fill}" stroke="{node.color}" stroke-width="2"/>')
        for i, line in enumerate(node.lines):
            x, y = node.x + 16, node.y + 10 + (i + 0.5) * math.ceil(font_size * 1.5)
            svg.append(f'<text x="{x}" y="{y}" dominant-baseline="central" font-size="{font_size}" font-family="{family}, sans-serif" fill="{"#ffffff" if is_root else ink}" xml:space="preserve">{escape(line)}</text>')
        svg.append('</g>')
    svg.append('</svg>')
    return "\n".join(svg)


def render_png(root, size, font, font_size, dark, scale):
    from PIL import Image, ImageDraw
    bg, ink, fill = ("#111827", "#f3f4f6", "#1f2937") if dark else ("#f8fafc", "#172033", "#ffffff")
    scaled = tuple(math.ceil(dimension * scale) for dimension in size)
    if scaled[0] * scaled[1] > 40_000_000:
        raise ValueError("PNG 超过 4000 万像素，请拆分子图、降低 --scale 或输出 SVG")
    image = Image.new("RGB", scaled, bg)
    draw = ImageDraw.Draw(image)
    for points, color in curves(root):
        sampled = []
        for i in range(41):
            t, u = i / 40, 1 - i / 40
            sampled.append(tuple(scale * (u**3 * points[0][j] + 3*u*u*t * points[1][j] +
                                         3*u*t*t * points[2][j] + t**3 * points[3][j]) for j in (0, 1)))
        draw.line(sampled, fill=color, width=max(1, round(3 * scale)))
    scaled_font = find_font(round(font_size * scale))
    for node in walk(root):
        box = tuple(v * scale for v in (node.x, node.y, node.x + node.width, node.y + node.height))
        draw.rounded_rectangle(box, radius=10 * scale, fill=node.color if node is root else fill,
                               outline=node.color, width=max(1, round(2 * scale)))
        for i, line in enumerate(node.lines):
            y = node.y + 10 + (i + 0.5) * math.ceil(font_size * 1.5)
            draw.text(((node.x + 16) * scale, y * scale), line, font=scaled_font,
                      fill="#ffffff" if node is root else ink, anchor="lm")
    return image


def mindmap_cmd(args):
    from PIL import Image, ImageDraw
    if not 10 <= args.font_size <= 72 or not 80 <= args.max_width <= 600:
        raise ValueError("--font-size 需在 10–72，--max-width 需在 80–600")
    if not math.isfinite(args.scale) or not 0.5 <= args.scale <= 4:
        raise ValueError("--scale 需在 0.5–4")
    suffix = Path(args.out).suffix.lower()
    if suffix not in (".svg", ".png"):
        raise ValueError("思维导图输出格式为 .svg 或 .png")
    root = load_tree(args.input)
    if any(re.search(r"[\u3400-\u9fff]", n.text) for n in walk(root)) and not find_cjk_font():
        raise ValueError("未找到中文字体；请安装 Noto Sans CJK 或把 DRAW_FONT 设为本地中文字体路径")
    font = find_font(args.font_size)
    size = layout(root, ImageDraw.Draw(Image.new("RGB", (1, 1))), font,
                  args.font_size, args.max_width, args.layout)
    if suffix == ".svg":
        # Exclusive creation also protects against a file appearing during layout.
        with open(args.out, "x", encoding="utf-8") as stream:
            stream.write(render_svg(root, size, args.font_size, args.theme == "dark"))
    else:
        image = render_png(root, size, font, args.font_size, args.theme == "dark", args.scale)
        with open(args.out, "xb") as stream:
            image.save(stream, format="PNG")
        size = image.size
    print(f"思维导图已生成：{args.out}（{len(list(walk(root)))} 节点，{size[0]}x{size[1]}，{args.layout}）")
    return 0
