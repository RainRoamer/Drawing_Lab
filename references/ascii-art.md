# E. ASCII / 字符画

适合：终端艺术、文字海报、代码风视觉、把照片转字符画。

## 1. 图片 → 字符画文本

```text
python scripts/drawkit.py ascii render 照片.jpg -o 照片.txt --cols 80
python scripts/drawkit.py ascii render 照片.jpg -o 黑白.txt --cols 60 --threshold 128      # 二值
python scripts/drawkit.py ascii render 照片.jpg -o 反色.txt --cols 60 --invert
python scripts/drawkit.py ascii render 照片.jpg -o 彩色.txt --cols 60 --color              # ANSI 真彩
```

亮度→字符梯度默认 `" .:-=+*#%@"`（暗→亮），`--chars` 可换。字符单元高宽比约 2:1，`--cols` 指定列数即可保持原图比例，`--ratio` 微调。

## 2. 字符画 → PNG（把文本渲染成图）

```text
python scripts/drawkit.py ascii toimage 照片.txt -o 照片字符.png --size 16 --foreground "#01efc8" --background "#0d0221"
```

## 3. 直接创作字符画

把文本/图案写进 `.txt`，然后 `ascii toimage` 出图。或用 Pillow 画字符网格后按列输出。手工字符画风格参考：

```text
  ██   ██████  ██     ██    ██  ██████   ██ ██ ██
```

## 交付与验收

- 检查字符画的轮廓/明暗与原图一致：看文本前几行密度与目标亮度分布是否对应。
- `--color` 输出是终端 ANSI 转义，存 `.txt` 没问题；转图片时去掉 `--color`。
- 中文窄字符可混合英文符号，避免字符宽度不齐破坏对齐。
