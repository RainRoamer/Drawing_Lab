# Math figures / 数学绘图与辅助线

Use `scripts/drawkit.py math` for geometry construction, auxiliary lines, coordinate axes, and function graphs.

## Geometry DSL / 几何 DSL

```text
python scripts/drawkit.py math figure geometry.png --grid --dots --spec "pt A 90,470;pt B 730,470;pt C 410,150;line A-B;line B-C;line C-A;mid M A B;mid D A C;mid E B C;aux C-M;aux D-E;right C A B;ang A C B 45;eq A-C B-C;par A-B D-E;dot A B C M D E;lab 三角形ABC@410,520"
```

Commands are separated by semicolons:

| Command | Meaning |
|---|---|
| `pt A 100,300` | Define point `A` |
| `mid M A B` | Define midpoint `M` of `AB` |
| `line A-B` | Solid segment |
| `ray A-B` | Ray from `A` through `B` |
| `aux A-B` | Dashed auxiliary segment |
| `ext A-B` | Dashed extension through both points |
| `arrow A-B` | Directed segment/vector |
| `circle O 80` | Circle centered at `O` |
| `ang C A B 60` | Angle arc at `C`, optional label |
| `right C A B` | Right-angle marker at `C` |
| `eq A-B C-D` | One equality tick on both segments |
| `eq2 ...`, `eq3 ...` | Two or three equality ticks |
| `par A-B C-D` | Parallel chevrons |
| `dot A B C` | Draw point markers with their names |
| `lab 文本@x,y` | Place a label |

Define points and midpoints before using them. Use `aux` for construction lines such as medians, angle bisectors, perpendiculars, extensions, and circle chords. Use `--aux-color` to make construction geometry distinct from the main figure.

## Function graphs / 函数图

```text
python scripts/drawkit.py math func parabola.png --fn "x**2-2" --xmin -4 --xmax 4 --tangent 1.5 --roots --grid --axis-labels
python scripts/drawkit.py math func reciprocal.png --fn "1/x" --xmin -5 --xmax 5 --asymptote-v 0 --asymptote-h 0 --grid
```

Expressions use a restricted evaluator with NumPy functions: `sin`, `cos`, `tan`, `sqrt`, `abs`, `exp`, `log`, `log10`, `floor`, and `ceil`, plus `x`, `pi`, and `e`. `--tangent x0` adds a numerical tangent, `--asymptote-v` and `--asymptote-h` add dashed asymptotes, and `--roots` marks sign-change zeroes. Set `--ymin/--ymax` when an automatic range would hide important behavior.

## Coordinate axes / 坐标系

```text
python scripts/drawkit.py math axes axes.png --xmin -10 --xmax 10 --ymin -8 --ymax 8 --grid
```

Use `math axes` as a clean base for manually layered coordinate constructions. For exact mathematical claims, keep scale, tick spacing, units, and labels consistent with the problem statement.

## Acceptance / 验收

- Check that auxiliary lines are dashed and do not visually replace the main construction.
- Check angle arcs, right-angle squares, equality ticks, and parallel marks against the referenced segments.
- Check function clipping, discontinuities, tangent position, asymptote placement, and label collisions.
- Render and inspect the PNG; do not treat a successful command exit as visual proof.
