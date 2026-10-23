# F. 照片实验室（调试 / 修图 / 创作）

统一走 `scripts/drawkit.py photo ...`，使用已安装依赖的 Python 3.10+；Windows 也可用 `bootstrap.ps1 -Action resolve` 查找解释器。修图从原图副本开始，绝不破坏原件；输出已存在时默认拒绝覆盖。

## 1. 先诊断再动手

```text
python scripts/drawkit.py photo info 照片.jpg           # 尺寸/模式/格式/EXIF
python scripts/drawkit.py photo inspect 照片.jpg         # 亮度分布/主色/EXIF，判断过曝、欠曝、偏色
```

`inspect` 输出：亮度均值与标准差（过低=欠曝，过高=过曝）、10 档亮度分布、6 个主色占比。**先看数据再决定调什么**，不要盲调。

## 2. 修图（链式操作，`--op` 可叠加）

```text
python scripts/drawkit.py photo edit 照片.jpg -o 修复.jpg --op rotate=90 --op crop=10%,10%,90%,90% --op resize=1600x
python scripts/drawkit.py photo edit 照片.jpg -o 提亮.jpg --op brightness=1.15 --op contrast=1.1
python scripts/drawkit.py photo edit 照片.jpg -o 复古.jpg --op sepia --op vignette=40
python scripts/drawkit.py photo edit 照片.jpg -o 黑白.jpg --op grayscale --op contrast=1.2
python scripts/drawkit.py photo edit 照片.jpg -o 柔化.jpg --op blur=1.5
python scripts/drawkit.py photo edit 照片.jpg -o 锐化.jpg --op sharpen
python scripts/drawkit.py photo edit 照片.jpg -o 海报.jpg --op posterize=4
python scripts/drawkit.py photo edit 照片.jpg -o 左右镜像.jpg --op flip=h
```

操作表：

| 操作 | 值 | 说明 |
| --- | --- | --- |
| `resize` | `800x` 或 `800x600` | 单边等比或固定尺寸 |
| `crop` | `左,上,右,下`（px 或 `10%,20%`） | 裁剪 |
| `rotate` | 角度 | 任意旋转 |
| `flip` | `h` / `v` | 镜像/上下翻转 |
| `brightness / contrast / saturation / sharpness` | 倍数 | 明暗/对比/饱和/锐度 |
| `blur` | 半径 | 高斯模糊 |
| `sharpen` | 无 | USM 锐化 |
| `grayscale` | 无 | 转黑白 |
| `sepia` | 无 | 复古棕 |
| `invert` | 无 | 反色 |
| `posterize` | 位数 | 色彩分级 |
| `vignette` | 强度 0-100 | 暗角 |

`--format png/jpg` 换格式，`--quality` 控制 JPG 质量。

## 3. 创作 / 合成

```text
# 多图拼版（可加标签，适合交付对比）
python scripts/drawkit.py photo canvas a.jpg b.jpg 修复.jpg -o 对比拼版.png --cols 3 --labels 原图,修正,修复

# 两图混合（均匀或渐变）
python scripts/drawkit.py photo blend 晨.jpg 昏.jpg -o 混合.png --mix 0.5
python scripts/drawkit.py photo blend a.jpg b.jpg -o 左右渐变.png --mask h

# 图上写字（描边阴影保证可读性）
python scripts/drawkit.py photo text 风景.jpg -o 加字.png --text "山海之间\n2026" --pos bottom --size 56 --color "#ffffff" --shadow "#000000"

# 空白画布写字（做标题图/海报底）
python scripts/drawkit.py photo text -o 海报.png --text "新品发布" --blank --width 1200 --height 800 --size 96 --color "#f72585" --background "#0d0221"

# 程序化画面当作"创作"素材
python scripts/drawkit.py raster 背景.png --scene gradient --palette sunset --width 1200 --height 800
```

## 4. 照片"创作"边界

- 程序化生成/合成/滤镜/调色是本 skill 的创作范围；位图生成模型（扩散等）不在 drawkit 内。
- 去噪、超分、去水印、人像语义修复超出 Pillow 能力时明确说明，不假装完成。
- 有 EXIF 的照片，交付前如需去除隐私用 `photo info` 查看后另行脱敏。
- 涉及他人照片只做用户授权处理，结果不外传。

## 交付与验收

- 每次编辑后 `photo info` / 打开预览核验尺寸与效果，把修改前后对比拼版图作为交付证据。
- 写明输出路径与操作链；无法达到的目标（如语义修复）如实列出替代方案。
