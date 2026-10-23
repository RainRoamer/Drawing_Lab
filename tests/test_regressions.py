"""Behavior checks for mind-map layout and publication-review fixes."""
import contextlib
import io
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import drawkit
import diagramlib
import mindmap
from fontlib import find_font
from PIL import Image, ImageDraw
import numpy as np


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="drawing-lab-regression-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def cli(self, *args, expected=0):
        log = io.StringIO()
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            try:
                result = drawkit.main([str(arg) for arg in args]) or 0
            except SystemExit as exc:
                result = exc.code
        self.assertEqual(result, expected, log.getvalue())
        self.assertNotIn("Traceback", log.getvalue())
        return log.getvalue()

    def test_markdown_preserves_hierarchy_and_order(self):
        root = mindmap.parse_markdown("# Plan\n## Research\n- Interviews\n  - Notes\n- Feedback\n## Delivery\n- Release")
        self.assertEqual([n.text for n in root.children], ["Research", "Delivery"])
        self.assertEqual([n.text for n in root.children[0].children], ["Interviews", "Feedback"])
        self.assertEqual(root.children[0].children[0].children[0].text, "Notes")

    def test_invalid_outline_is_rejected(self):
        for source in ("", "# A\n# B", "# A\n### C", "# A\n  - jump", "# A\n- A\n   - B", "# A\nparagraph", "# A\n\t- B"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                mindmap.parse_markdown(source)
        for tree in ({"text": ""}, {"text": "a", "children": {}}, {"text": "a", "url": "file"}, {"text": "\x00"}, {"text": "a" * 501}):
            with self.subTest(tree=tree), self.assertRaises(ValueError):
                mindmap.parse_json(tree)
        with self.assertRaises(ValueError):
            mindmap.parse_json({"text": "root", "children": ["leaf"] * 500})
        tree = "leaf"
        for _ in range(13):
            tree = {"text": "branch", "children": [tree]}
        with self.assertRaises(ValueError):
            mindmap.parse_json(tree)

    def test_dense_layout_has_no_overlap_or_clipping(self):
        data = {"text": "A central topic", "children": [
            {"text": f"Branch {i} with longer label", "children": [
                {"text": "A long label " * (j + 1), "children": [f"Detail {i}.{j}"]}
                for j in range(i % 4 + 1)
            ]} for i in range(14)
        ]}
        font = find_font(20)
        draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        for mode in ("balanced", "right", "left"):
            root = mindmap.parse_json(data)
            width, height = mindmap.layout(root, draw, font, max_width=150, mode=mode)
            nodes = list(mindmap.walk(root))
            for node in nodes:
                self.assertGreaterEqual(node.x, 0)
                self.assertGreaterEqual(node.y, 0)
                self.assertLessEqual(node.x + node.width, width)
                self.assertLessEqual(node.y + node.height, height)
            for a, b in itertools.combinations(nodes, 2):
                overlap = (a.x < b.x + b.width and b.x < a.x + a.width and
                           a.y < b.y + b.height and b.y < a.y + a.height)
                self.assertFalse(overlap, (mode, a.text, b.text))
            if mode == "right":
                self.assertTrue(all(n.x > root.x for n in nodes[1:]))
            if mode == "left":
                self.assertTrue(all(n.x + n.width < root.x for n in nodes[1:]))

    def test_mindmap_cli_exports_readable_files_and_escapes_xml(self):
        source = self.directory / "tree.json"
        source.write_text(json.dumps({"text": 'A & <B> "C"', "children": ["One", "Two", "Long label " * 10]}), encoding="utf-8-sig")
        svg, png = self.directory / "map.svg", self.directory / "map.png"
        self.cli("mindmap", svg, "--input", source)
        self.cli("mindmap", png, "--input", source, "--theme", "dark", "--scale", 2)
        xml = ET.parse(svg).getroot()
        self.assertEqual(xml.find("{*}title").text, 'A & <B> "C"')
        self.assertGreater(len(xml.findall(".//{*}text")), 4)
        self.assertFalse(xml.findall(".//{*}script"))
        with Image.open(png) as image:
            self.assertEqual(image.size, (int(xml.attrib["width"]) * 2, int(xml.attrib["height"]) * 2))
            self.assertGreater(len(image.getcolors(image.width * image.height)), 3)
        before = svg.read_bytes()
        self.cli("mindmap", svg, "--input", source, expected=1)
        self.assertEqual(svg.read_bytes(), before)

    def test_mindmap_cli_handles_malformed_and_unsupported_input(self):
        source = self.directory / "bad.json"
        source.write_text('{"text":', encoding="utf-8")
        out = self.directory / "bad.svg"
        self.cli("mindmap", out, "--input", source, expected=1)
        self.assertFalse(out.exists())
        self.cli("mindmap", self.directory / "map.pdf", "--input", source, expected=1)
        self.cli("mindmap", out, "--input", source, "--scale", "nan", expected=1)

    def test_science_commands_preserve_existing_file(self):
        out = self.directory / "keep.png"
        out.write_bytes(b"user-owned content")
        for args in (
            ["physics", "force", out], ["math", "axes", out],
            ["3d", out, "--scene", "cube"], ["chem", "cell", out],
        ):
            self.cli(*args, expected=1)
            self.assertEqual(out.read_bytes(), b"user-owned content")

    def test_svg_scale_is_relative_to_source_dimensions(self):
        source = self.directory / "input.svg"
        source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="red"/></svg>', encoding="utf-8")
        self.cli("svg", "render", source, "-o", self.directory / "normal.png", "--scale", 2)
        with Image.open(self.directory / "normal.png") as image:
            self.assertEqual(image.size, (640, 360))
        # Exercise the declared svglib fallback even if CairoSVG is installed.
        with patch.dict(sys.modules, {"cairosvg": None}):
            self.cli("svg", "render", source, "-o", self.directory / "fallback.png", "--scale", 2)
        with Image.open(self.directory / "fallback.png") as image:
            self.assertEqual(image.size, (640, 360))
        self.cli("svg", "render", source, "-o", self.directory / "invalid.png", "--scale", 0, expected=1)
        source.write_text("<html/>", encoding="utf-8")
        self.cli("svg", "check", source, expected=1)

    def test_doctor_does_not_require_optional_packages(self):
        import importlib
        original = importlib.import_module
        def import_core(name):
            if name not in ("PIL", "numpy"):
                raise ImportError(name)
            return original(name)
        with patch("importlib.import_module", side_effect=import_core):
            self.cli("doctor")

    def test_function_evaluator_handles_constants_and_math(self):
        xs = np.array([-1.0, 0, 1.0])
        np.testing.assert_allclose(diagramlib._eval_fn("3", xs), [3, 3, 3])
        np.testing.assert_allclose(diagramlib._eval_fn("np.sin(x)+x**2", xs), np.sin(xs) + xs**2)
        for expr in ("x.__class__", "np.load('file')", "__import__('os')", "[x for x in ()]", "(lambda: 1)()", "np.__dict__", "open('file')"):
            with self.subTest(expr=expr), self.assertRaises(ValueError):
                diagramlib._eval_fn(expr, xs)
        self.cli("math", "func", self.directory / "constant.png", "--fn", "3")
        self.cli("math", "axes", self.directory / "invalid.png", "--xmin", 2, "--xmax", 1, expected=1)

    def test_duplicate_atoms_and_invalid_bonds_are_rejected(self):
        out = self.directory / "molecule.png"
        self.cli("chem", "molecule", out, "--atoms", "O:10,10;O:20,20", expected=1)
        self.cli("chem", "molecule", out, "--atoms", "O:10,10;H:20,20", "--bonds", "O:H:9", expected=1)
        self.assertFalse(out.exists())
        self.cli("chem", "molecule", out, "--atoms", "O1:180,260;C:360,260;O2:540,260", "--bonds", "O1:C:2;C:O2:2")

    def test_chart_json_pairs_and_validation(self):
        source = self.directory / "points.json"
        source.write_text('{"pairs": [[-2, 3], [0, 1], [4, -2]]}', encoding="utf-8")
        self.cli("chart", "scatter", self.directory / "scatter.png", "--data-file", source)
        self.cli("chart", "pie", self.directory / "bad.png", "--values", "0,0", expected=1)
        self.cli("chart", "bar", self.directory / "bad.png", "--values", "nan", expected=1)
        self.cli("chart", "bar", self.directory / "bad.png", "--values", "1,2", "--labels", "one", expected=1)

    def test_pillow_chart_fallback_handles_hbar_zeros_and_negatives(self):
        with patch.object(drawkit, "matplotlib", None):
            for kind in ("bar", "hbar", "line"):
                for case, values in (("zero", "0,0,0"), ("signed", "-2,0,4")):
                    out = self.directory / f"{kind}-{case}.png"
                    self.cli("chart", kind, out, "--values=" + values)
                    with Image.open(out) as image:
                        self.assertGreater(len(image.getcolors(image.width * image.height)), 1)

    def test_geometry_dot_marks_and_names_every_requested_point(self):
        with patch.object(diagramlib, "_text", wraps=diagramlib._text) as text:
            self.cli("math", "figure", self.directory / "points.png", "--spec",
                     "pt A 100,100;pt B 300,100;pt C 300,300;dot A B C")
        self.assertEqual([call.args[2] for call in text.call_args_list], ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
