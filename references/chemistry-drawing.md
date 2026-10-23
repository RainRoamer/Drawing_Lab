# Chemistry drawing / 化学图像绘制

`drawkit chem` provides printable chemistry illustrations without extra packages.

## Molecules / 分子结构

```text
python scripts/drawkit.py chem molecule water.png --atoms "O:360,250;H1:250,180;H2:470,180" --bonds "O:H1:1;O:H2:1"
python scripts/drawkit.py chem molecule carbon-dioxide.png --atoms "O1:180,260;C:360,260;O2:540,260" --bonds "O1:C:2;C:O2:2" --model ball
```

`--atoms` uses `ID:x,y`; use IDs such as `H1` and `H2` when an element occurs more than once. `--bonds` uses `ID:ID:order`. Bond order `1`, `2`, or `3` draws single, double, or triple bonds. `--model line` produces skeletal labels; `--model ball` adds atom circles.

## Crystal cells / 晶胞

```text
python scripts/drawkit.py chem cell sc.png --kind sc
python scripts/drawkit.py chem cell bcc.png --kind bcc
python scripts/drawkit.py chem cell fcc.png --kind fcc
```

The command draws simple cubic, body-centered cubic, and face-centered cubic site layouts. Use it as a teaching diagram rather than a crystallographic measurement tool.

## Reaction equations / 化学反应式

```text
python scripts/drawkit.py chem reaction combustion.png --equation "2H2+O2->2H2O" --condition "点燃"
```

The equation accepts `->` or `→`; `--condition` places the catalyst, temperature, light, or other reaction condition above the arrow.

## Apparatus / 实验器材

```text
python scripts/drawkit.py chem apparatus beaker.png --kind beaker
python scripts/drawkit.py chem apparatus flask.png --kind flask --liquid-color "#93c5fd"
python scripts/drawkit.py chem apparatus tube.png --kind test-tube
```

Available scenes: `beaker`, `flask`, `test-tube`. These are clean schematic templates; add stoppers, tubes, burners, labels, or measurement marks in a follow-up figure when the experiment needs them.

## Acceptance / 验收

Check atom labels, bond order, reaction arrow direction, crystal-site placement, liquid level, clipping, and label overlap in the rendered PNG. Chemical notation is a diagram aid; verify valence, charge, stereochemistry, and reaction balance against the problem before treating it as a scientific answer.
