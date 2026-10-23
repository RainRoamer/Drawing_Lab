---
name: drawing-lab
description: "Create mind maps, diagrams, charts, illustrations, ASCII art, and photo edits using SVG/Canvas, Three.js, Mermaid/Vega-Lite, and Python. 用于思维导图、脑图、知识梳理、画图、数学题配图、图表、插画与修图；不控制已打开的外部绘图应用。"
---

# Drawing Lab

Use the shortest suitable rendering path. 选择最短且可验证的绘图路径：

| Need / 需求 | Route / 路径 | Tool / 工具 |
|---|---|---|
| Mind maps, knowledge outlines / 思维导图、脑图、知识梳理 | Offline measured tree layout | `drawkit mindmap` (SVG/PNG) |
| Geometry, icons, posters / 几何图、图标、海报 | Canvas/SVG | browser preview + `svg check/render` |
| 3D, particles, animation / 3D、粒子、动画 | WebGL/Three.js | self-contained HTML + browser |
| Flow, sequence, charts / 流程、时序、图表 | Mermaid/Vega-Lite | DSL + browser render |
| Physics diagrams / 物理实物图、电路图、光路图、受力图 | Pillow diagram engine | `drawkit physics` |
| Math geometry, auxiliary lines, plots / 数学几何、辅助线、函数图 | Pillow diagram engine | `drawkit math` |
| 3D geometry / 三维几何、立体结构 | Orthographic projection | `drawkit 3d` |
| Chemistry diagrams / 分子、晶胞、反应式、器材 | Chemistry diagram engine | `drawkit chem` |
| Procedural art / 程序化画面 | Python | `drawkit raster/chart/svg` |
| Terminal art / 字符画 | ASCII | `drawkit ascii` |
| Retouching, analysis, compositing / 修图、分析、合成 | Photo Lab | `drawkit photo` |

## Runtime / 运行时

Use Python 3.10+ with local dependencies. Run from the skill directory (or use absolute paths):

```text
python -m pip install -r requirements.txt
python -X utf8 -B scripts/drawkit.py doctor
```

Pillow/numpy are the core dependencies; matplotlib adds charts, and svglib/reportlab/rlPyCairo add general SVG rasterization. Mind maps render SVG/PNG directly with Pillow and do not need a browser, network service, or SVG renderer. `DRAW_FONT` selects a local font file; Chinese labels need a CJK font such as Microsoft YaHei, PingFang, or Noto Sans CJK.

On Windows, `bootstrap.ps1` can resolve an installed interpreter and install dependencies without a fixed workspace layout:

```powershell
$Skill = '<skill directory>'
$Py = & (Join-Path $Skill 'bootstrap.ps1') -Action resolve
$Kit = Join-Path $Skill 'scripts\drawkit.py'
& $Py -X utf8 -B $Kit doctor
```

Resolution order: `DRAW_PYTHON` → activated virtual environment → `.venv` inside the skill → `python` / `python3` on `PATH`. `DRAW_PYTHON` accepts an interpreter file or its containing directory; an invalid explicit override or activated environment fails instead of switching interpreters. No sibling folders or custom agent environment variables are required. Use `DRAW_PIP_INDEX` for package index and `bootstrap.ps1 -Action install` for all dependencies. `doctor` reports optional dependencies but fails only when a core dependency is missing; `bootstrap.ps1 -Action check-deps` checks the full dependency set.

## Fast commands / 快速命令

```text
python scripts/drawkit.py doctor
python scripts/drawkit.py mindmap map.svg --input examples/mindmap.md
python scripts/drawkit.py mindmap map.png --input examples/mindmap.md --layout balanced --scale 2
python scripts/drawkit.py svg new figure.svg --scene concentric --width 800 --height 800 --seed 7
python scripts/drawkit.py svg check figure.svg
python scripts/drawkit.py svg render figure.svg -o figure.png --scale 2
python scripts/drawkit.py raster art.png --scene stars --palette neon --width 960 --height 540 --seed 42
python scripts/drawkit.py chart bar chart.png --values 10,20,30 --labels A,B,C --title "Sales"
python scripts/drawkit.py ascii render photo.jpg -o photo.txt --cols 90
python scripts/drawkit.py ascii toimage photo.txt -o ascii.png --foreground "#f72585" --background "#0d0221"
python scripts/drawkit.py photo info photo.jpg
python scripts/drawkit.py photo inspect photo.jpg
python scripts/drawkit.py photo edit photo.jpg -o fixed.jpg --op brightness=1.15 --op contrast=1.1 --op sharpen
python scripts/drawkit.py photo canvas a.jpg b.jpg -o contact.png --cols 2 --labels before,after
python scripts/drawkit.py photo blend a.jpg b.jpg -o blend.png --mix 0.5 --mask h
python scripts/drawkit.py photo text photo.jpg -o titled.png --text "Title\n2026" --pos center --size 64
python scripts/drawkit.py physics circuit circuit.png --spec "B:(140,120)-(140,420);W:(140,120)-(420,120);R:(420,120)-(420,250);L:(420,250)-(420,420);W:(420,420)-(140,420)"
python scripts/drawkit.py physics ray lens.png --kind convex --focal 90 --object 150 --height 60
python scripts/drawkit.py physics force force.png --angle 30 --friction --free --cn
python scripts/drawkit.py physics object setup.png --scene incline --angle 35 --cn
python scripts/drawkit.py math figure geometry.png --spec "pt A 90,470;pt B 730,470;pt C 410,150;line A-B;line B-C;line C-A;mid M A B;aux C-M;right C A B;ang A C B 45;dot A B C M"
python scripts/drawkit.py math func parabola.png --fn "x**2-2" --xmin -4 --xmax 4 --tangent 1.5 --roots --grid --axis-labels
python scripts/drawkit.py math axes axes.png --xmin -10 --xmax 10 --ymin -8 --ymax 8 --grid
python scripts/drawkit.py 3d cube.png --scene cube --yaw 35 --pitch 25 --grid
python scripts/drawkit.py 3d sphere.png --scene sphere --yaw 35 --pitch 25
python scripts/drawkit.py chem molecule water.png --atoms "O:360,250;H1:250,180;H2:470,180" --bonds "O:H1:1;O:H2:1"
python scripts/drawkit.py chem cell crystal.png --kind bcc
python scripts/drawkit.py chem reaction reaction.png --equation "2H2+O2->2H2O" --condition "点燃"
python scripts/drawkit.py chem apparatus beaker.png --kind beaker --liquid-color "#93c5fd"
```

Run `drawkit --help` and subcommand `--help` for authoritative syntax. Built-in lists: `svg scenes`, `raster-scenes`. Outputs refuse overwrite by default.

## Math diagrams / 数学题配图

For geometry, coordinate systems, functions, number lines, statistics, and proof annotations, use `drawkit math`. Always encode labels, coordinates, lengths, angles, formulas, scale, and auxiliary lines explicitly. For a solution, separate `construction` from `explanation`: draw the figure first, then annotate the reasoning. Read `references/math-figure.md` for the DSL.

Recommended workflow:

1. Parse entities and constraints / 提取点、线、角、长度、坐标和约束。
2. Choose coordinates and scale / 选坐标系与比例。
3. Generate SVG/Canvas or Python output / 生成矢量图或 Python 图。
4. Render and inspect / 实际渲染并检查标签、比例、遮挡和方向。
5. Browser-preview web outputs; verify file size/dimensions for Python outputs / 网页用浏览器预览，Python 产物核验尺寸与文件。

## Mind maps / 思维导图

For a central topic with hierarchical branches, use `drawkit mindmap`. Read [references/mindmap.md](references/mindmap.md) for the input schema, layout choices, examples, and acceptance checks. Organize the user's material into concise labels while preserving its hierarchy, terminology, and uncertainties; do not invent missing facts. Return the Markdown/JSON source alongside the SVG/PNG so the user can revise it. SVG keeps editable text and paths, not a native XMind file.

Use `balanced` for a central topic with two sides, or `right`/`left` for a reading-order tree. Large maps should be split into an overview and linked submaps before shrinking the text. A workflow with decision edges is a flowchart; use Mermaid/SVG for those relations. Mind-map branch connectors normally have no arrows. If Mermaid source is requested, use its `mindmap` syntax and verify it with an available renderer; do not assume a Markdown viewer supports it.

## Evidence & safety / 验收与边界

- Physics and math diagrams must be checked for clipping, overlaps, readable labels, correct arrow direction, and explicit auxiliary-line style before delivery. 物理图和数学图交付前必须检查裁切、重叠、标签可读性、箭头方向和辅助线样式。

- Web outputs must be opened in the browser and visually checked; animation/interaction needs a post-action check. 网页必须真实预览，动态交互要检查操作后的状态。
- Python outputs must be rendered to files and inspected; code alone is not evidence. Python 必须真实落盘并核验，不能只给代码。
- Mind maps must be visually checked for hierarchy, complete labels, legible CJK glyphs, clipping, overlapping nodes, and consistent branch colors. 思维导图交付前核验层级、文字完整、中文字体、裁切、重叠与分支颜色。
- Use `photo info/inspect` before editing; preserve the source and write a clear operation chain. 修图前先分析，保留原图并记录操作链。
- SVG rasterization supports common SVG 1.1; complex filters/scripts/external resources may require browser rendering. 复杂 SVG 改用浏览器验证。
- Photo Lab does not provide semantic inpainting, face recognition, super-resolution, or object removal. 超出 Pillow 能力要明确说明。
- Handle private photos only with authorization. 私人照片只在授权范围内处理。

## Verification / 验证

```text
python -X utf8 -B tests/test_drawkit.py
python -X utf8 -B -m unittest discover -s tests -p "test_regressions.py"
```

Tests use isolated temporary directories and cover mind maps, SVG, raster scenes, charts, ASCII, photos, science diagrams, input validation, and overwrite protection. The full smoke suite requires all dependencies. 测试不修改用户文件，缺少可选依赖时必须如实报告。

Read only the relevant reference when needed / 按需读取参考：
- `references/vector-code.md`
- `references/webgl-threejs.md`
- `references/chart-dsl.md`
- `references/mindmap.md`
- `references/python-plot.md`
- `references/ascii-art.md`
- `references/photo-lab.md`
- `references/physics-drawing.md`
- `references/math-figure.md`
- `references/3d-drawing.md`
- `references/chemistry-drawing.md`
