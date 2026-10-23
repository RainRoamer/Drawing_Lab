# A. Canvas / SVG 矢量代码

适合：图标、插画、海报、示意图、生成式图案、可缩放徽标。两种载体：

## 1. SVG（静态矢量，最轻）

**直接写 SVG 文件**（`.svg`），用本 skill 的 drawkit 校验和落 PNG：

```text
python scripts/drawkit.py svg check 图标.svg        # 校验 XML 与元素统计
python scripts/drawkit.py svg render 图标.svg -o 图标.png --scale 2   # 落 PNG（svglib+reportlab）
```

手写 SVG 要点：

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#023047"/>
      <stop offset="100%" stop-color="#8ecae6"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#sky)"/>
  <circle cx="320" cy="70" r="40" fill="#ffb703"/>
  <path d="M0 240 C 100 180, 200 260, 400 200 L 400 300 L 0 300 Z" fill="#219ebc"/>
</svg>
```

常用元素：`rect / circle / ellipse / line / polyline / polygon / path`（d=M..C..L..Z 贝塞尔与直线）、`text`、`g` 分组、`transform`（translate/rotate/scale）、`defs`（linearGradient/radialGradient/pattern/clipPath）。属性以 `fill / stroke / stroke-width / stroke-linecap / opacity / rx / cy / cx` 为主。坐标统一用 viewBox 思维，别依赖像素直觉。

内置场景快速起步（`drawkit svg new`）可选：`grid / concentric / mountains / waves / skyline / spiral`，生成后再手工改。

注意：本 skill 的 SVG→PNG 渲染基于 svglib，支持 SVG 1.1 基本子集；滤镜、脚本、外部引用、复杂 `text` 布局不保证保真。复杂 SVG 用浏览器预览（把 `.svg` 拖进内置浏览器再截图）作为权威视觉证据。

## 2. Canvas 2D（HTML/JS，动态或交互）

写一个自包含 HTML：

```html
<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><style>
  html,body{margin:0;background:#0d0221;display:flex;justify-content:center;align-items:center;height:100vh}
  canvas{background:#0d0221}
</style></head>
<body>
<canvas id="c" width="800" height="600"></canvas>
<script>
  const c = document.getElementById('c'), ctx = c.getContext('2d');
  ctx.fillStyle = '#0d0221'; ctx.fillRect(0, 0, 800, 600);
  // 星空
  for (let i = 0; i < 120; i++) {
    ctx.beginPath();
    ctx.arc(Math.random()*800, Math.random()*600, Math.random()*2, 0, Math.PI*2);
    ctx.fillStyle = '#01efc8'; ctx.fill();
  }
  // 圆环
  for (let r = 20; r <= 280; r += 20) {
    ctx.beginPath(); ctx.arc(400, 300, r, 0, Math.PI*2);
    ctx.strokeStyle = `hsl(${(r*1.2)%360} 80% 60%)`; ctx.lineWidth = 2; ctx.stroke();
  }
</script>
</body>
</html>
```

Canvas 2D API 速记：`fillRect/strokeRect`、`beginPath→moveTo/lineTo/arc/quadraticCurveTo/bezierCurveTo→fill/stroke`、`save/restore`、`translate/rotate/scale`、`globalAlpha`、`createLinearGradient/createRadialGradient`、`createPattern`、`fillText`（配合 `ctx.font='48px Microsoft YaHei'`）。

## 交付与验收

- 用浏览器打开 HTML/SVG 文件实际预览并截图；SVG 可先 `svg render` 落 PNG。
- 检查：元素是否按预期定位、颜色/渐变是否正确、文字是否有豆腐块（中文优先微软雅黑）、小尺寸下是否清晰。
- 输出路径、预览截图、渲染 PNG 都要写进交付说明。
