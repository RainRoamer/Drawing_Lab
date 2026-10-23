# Physics drawing / 物理绘图

Use `scripts/drawkit.py physics` for reproducible printable diagrams. Outputs are PNG files made with Pillow; use a white background and dark ink for worksheets.

## Circuit diagrams / 线路图

The circuit command accepts a semicolon-separated mini DSL:

```text
python scripts/drawkit.py physics circuit circuit.png --width 800 --height 560 --spec "B:(140,120)-(140,420);W:(140,120)-(420,120);R:(420,120)-(420,250);L:(420,250)-(420,420);W:(420,420)-(140,420)"
```

Absolute component syntax is `<type>:(x1,y1)-(x2,y2)`. Chain syntax is `<type>:<direction>:<length>` where direction is `R/L/U/D`; `at X,Y` jumps the pen. Available symbols:

- `W` wire, `B` battery, `C` cell
- `R` resistor, `L` bulb/lamp, `S` switch
- `A` ammeter, `V` voltmeter, `M` motor
- `G` ground, `D` junction dot
- `LAB:text@x,y` label

Build the main circuit with wires first, then place components. Use explicit absolute points for branches and measurement instruments so the topology is unambiguous. Verify that the circuit is closed, junctions are visible, and ammeters/voltmeters are placed in the intended series/parallel position.

## Ray diagrams / 光路图

```text
python scripts/drawkit.py physics ray convex.png --kind convex --focal 90 --object 150 --height 60
python scripts/drawkit.py physics ray concave.png --kind concave --focal 90 --object 170 --height 60
python scripts/drawkit.py physics ray mirror.png --kind plane --object 120 --height 60
```

`convex` and `concave` draw the principal axis, focal marks, object, three construction rays, and real/virtual image. `plane` draws a plane mirror, normal, incident/reflected ray, and virtual image. Use `--aux-color` to distinguish dashed extensions. Keep `--focal`, `--object`, and `--height` in pixels; choose values that leave both the optical axis and labels inside the canvas.

## Force diagrams / 受力图

```text
python scripts/drawkit.py physics force force.png --angle 30 --friction --pull --free --cn
```

The scene draws an inclined plane, block, gravity `G`, normal `N`, optional friction `f`, pull `F`, tension `T`, and an optional isolated-body view. Use `--cn` for Chinese force names. The force directions are schematic; adjust the diagram to the stated physical condition before delivery, especially friction direction and whether a tension/pull exists.

## Apparatus scenes / 实物图

```text
python scripts/drawkit.py physics object incline.png --scene incline --angle 35 --cn
python scripts/drawkit.py physics object lever.png --scene lever --cn
python scripts/drawkit.py physics object pulley.png --scene pulley --cn
python scripts/drawkit.py physics object pendulum.png --scene pendulum --angle 25 --cn
python scripts/drawkit.py physics object spring.png --scene spring --cn
python scripts/drawkit.py physics object wave.png --scene wave --amplitude 45 --wavelength 110 --cycles 2 --cn
python scripts/drawkit.py physics object longitudinal.png --scene wave --longitudinal --cn
```

Scenes are clean construction templates for inclined-plane, lever, fixed-pulley, pendulum, spring, transverse-wave, and longitudinal-wave drawings. Add problem-specific dimensions and labels after generation when the diagram is used as a solution figure.

## Acceptance / 验收

- Check canvas bounds, symbol overlap, label readability, arrow direction, and line weight.
- For circuits, verify topology rather than only visual appearance.
- For optics, verify focal-point side, image orientation, and dashed virtual-ray extensions.
- For force diagrams, verify every arrow is justified by the stated constraints.
- Keep generated evidence under `.yanagent/evidence`; do not leave temporary files in the skill root.
