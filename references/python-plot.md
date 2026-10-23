# D. Python 绘图库（drawkit）

适合：程序化画面、数学/几何图形、统计图表、批量出图。统一走 `scripts/drawkit.py`，使用已安装依赖的 Python 3.10+；Windows 也可通过 `bootstrap.ps1 -Action resolve` 查找本机解释器或虚拟环境：

```powershell
$Py = & '<本 skill 所在目录>\bootstrap.ps1' -Action resolve
$Kit = Join-Path '<本 skill 所在目录>' 'scripts\drawkit.py'
& $Py -X utf8 -B $Kit --help
```

## 1. 程序化画面（Pillow 场景）

```text
python scripts/drawkit.py raster 画面.png --scene stars --seed 42 --width 960 --height 540 --palette neon
python scripts/drawkit.py raster 画面.png --scene waves --palette ocean
python scripts/drawkit.py raster-scenes          # 列出场景与配色
```

场景：`gradient / stripes / checker / dots / rings / waves / blobs / stars / sunburst / city / spiral`，配色：`sunset / ocean / forest / neon / paper / mono`，`--seed` 固定随机让结果可复现。需要更自由的自定义画面时，用解析出的解释器直接写 Pillow/numpy 脚本（见参考文件内模板），产出到工作区。

## 2. 图表（matplotlib，Pillow 回退）

```text
python scripts/drawkit.py chart bar    销量.png --values 12,30,22,40 --labels 春,夏,秋,冬 --title "四季销量"
python scripts/drawkit.py chart line   趋势.png --values 5,8,6,12,9 --theme dark
python scripts/drawkit.py chart pie    占比.png --values 30,20,50 --labels A,B,C
python scripts/drawkit.py chart scatter 散点.png --pairs 1:2,2:3,3:1,4:5
python scripts/drawkit.py chart bar 数据.png --data-file data.json      # {"labels":[...],"values":[...]}
python scripts/drawkit.py chart scatter 散点数据.png --data-file points.json  # {"pairs":[[x,y],...]}
```

中文字体：搜索 Windows 微软雅黑、macOS PingFang、Linux Noto Sans CJK；`DRAW_FONT` 可指定本地字体路径。目标环境需安装可用中文字体，并实际检查缺字。

## 3. 内置 SVG 生成

```text
python scripts/drawkit.py svg new 图.svg --scene concentric --width 800 --height 800 --seed 7
python scripts/drawkit.py svg scenes
```

## 4. 需要手写 Python 时的模板

```python
from PIL import Image, ImageDraw
img = Image.new("RGB", (800, 600), "#0d0221")
d = ImageDraw.Draw(img)
for i in range(24):
    d.line([(400, 300), (400 + 300*__import__('math').cos(2*3.14159*i/24), 300 + 300*__import__('math').sin(2*3.14159*i/24))],
           fill="#01efc8", width=2)
img.save("rays.png")
```

numpy 数学图像：网格化坐标 → 公式 → `Image.fromarray(arr.astype('uint8'))` 最直接；比如分形/极坐标/噪声图都适合这条路。matplotlib 自定义图表可另写脚本，但 `chart` 子命令已覆盖常规需求。

## 交付与验收

- 每次产出必须实际生成文件并核验：`photo info` / 打开预览确认尺寸与内容，不能只给代码。
- `doctor` 标出的缺失依赖不得假装可用；缺 matplotlib 时 `chart` 走 Pillow 回退并在输出注明。
- 输出路径写入交付说明；脚本模板类自定义产出放在用户指定位置，用完清理一次性脚本。
