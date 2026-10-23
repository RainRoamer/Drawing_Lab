# 3D drawing / 三维绘图

`drawkit 3d` produces deterministic PNGs with an orthographic projection. It is适合立方体、棱锥、棱柱、圆柱、球面线框和坐标轴示意图，不依赖 WebGL。

```text
python scripts/drawkit.py 3d cube.png --scene cube --yaw 35 --pitch 25 --grid
python scripts/drawkit.py 3d pyramid.png --scene pyramid --yaw 35 --pitch 25
python scripts/drawkit.py 3d sphere.png --scene sphere --yaw 35 --pitch 25
python scripts/drawkit.py 3d axes.png --scene axes --yaw 35 --pitch 25 --label "空间直角坐标系"
```

- `--yaw` controls horizontal view angle.
- `--pitch` controls vertical view angle.
- `--scale` controls projected size.
- `--palette` accepts comma-separated hex colors for faces.
- `--grid` adds a construction grid; omit it for a clean worksheet figure.

Scenes: `axes`, `cube`, `pyramid`, `prism`, `cylinder`, `sphere`.

For a physical setup or interactive 3D scene, use the existing WebGL/Three.js reference instead. For mathematical solids, keep the camera angle, face order, labels, and proportions explicit, then inspect the PNG for hidden-face ambiguity and clipping.
