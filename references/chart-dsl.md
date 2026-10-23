# C. Mermaid / Vega-Lite 图表 DSL

适合：流程图、时序图、甘特、类图、树/图、统计图表、声明式数据可视化。DSL 出图快、可改，但必须先渲染出真实图像并截图取证。思维导图优先用离线 `drawkit mindmap`，参见 [mindmap.md](mindmap.md)。

## 1. Mermaid（流程/时序/甘特/类图）

三种出图方式，按可用性选择：

**a. 已有本地 Mermaid 渲染器**
优先使用环境已提供的渲染器或本地库，不向外部服务发送图的内容。若用户指定使用 mermaid.ink 等服务，需确认内容适合外发；下例展示其地址形式，源码编码以服务接口文档为准：

```text
# 例：https://mermaid.ink/img/<base64(源码)>
# 本地拿图：先编码再打开
```

**b. 本地 HTML + Mermaid 库渲染**（示例从 CDN 加载库，需要网络；离线时改为本地库路径）

```html
<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"></head>
<body>
<pre class="mermaid">
graph TD
  A[收集需求] --> B{范围}
  B -->|大| C[分层设计]
  B -->|小| D[直接实现]
  C --> E[实现] --> F[验收]
  D --> F
</pre>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'base'});</script>
</body>
</html>
```

Mermaid 常用语法速记：

```text
graph TD / LR         # 流程图（TD 上到下，LR 左到右）
  A --> B              # 箭头
  A -- 标签 --> B      # 带文字箭头
  A -.虚线.-> B
  A ==> B              # 粗箭头
  subgraph 组名        # 子图
  A[矩形] B(圆角) C{菱形} D>旗帜] E((圆形))   # 节点形状

sequenceDiagram        # 时序图
  Alice->>Bob: 请求
  Bob-->>Alice: 响应

gantt                  # 甘特图
  section 阶段1
  任务A :a1, 2026-01-01, 7d

classDiagram            # 类图
  Animal <|-- Duck
  Animal : +int age
```

## 2. Vega-Lite（统计图表，声明式 JSON）

用本地 HTML + Vega-Lite 库渲染：

```html
<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
  <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
</head><body>
<div id="vis"></div>
<script>
const spec = {
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "width": 600, "height": 360,
  "data": {
    "values": [
      {"月份": "1月", "销量": 12}, {"月份": "2月", "销量": 30},
      {"月份": "3月", "销量": 22}, {"月份": "4月", "销量": 40}
    ]
  },
  "mark": {"type": "bar", "cornerRadius": 4},
  "encoding": {
    "x": {"field": "月份", "type": "ordinal", "axis": {"labelAngle": 0}},
    "y": {"field": "销量", "type": "quantitative"},
    "color": {"value": "#268bd2"}
  },
  "config": {"font": "Microsoft YaHei"}
};
vegaEmbed('#vis', spec, {"theme": "light"});
</script>
</body>
</html>
```

Vega-Lite 速记：`mark` 为 `bar/line/area/point/circle/square/tick/rect/text/arc(饼)`；`encoding` 绑定 `x/y/color/size/shape/opacity`；`transform` 支持 `filter/calculate/aggregate/bin`；多图层用 `layer: [...]`，交互用 `params`（`{"select":"point","bind":"legend"}`）。

## 3. 对比与选型

| 需求 | 选 | 理由 |
| --- | --- | --- |
| 流程图/时序/甘特/组织架构 | Mermaid | 文本短、结构直观 |
| 统计图表、可交互、数据驱动 | Vega-Lite | 声明式、响应式、默认美观 |
| 精绘手调像素级 | Canvas/SVG 或 drawkit chart | DSL 样式控制有限 |

## 交付与验收

- 渲染成功标准：浏览器打开后看到完整图形，控制台无错误，截图留证。
- 中文标签乱码/豆腐块时：Mermaid 指定 `fontFamily: 'Microsoft YaHei'`；Vega-Lite 设 `config.font`。
- 外部渲染服务不可用时改用本地 HTML 渲染；离线时使用已有本地库文件并以相对路径引用。
- 数据较大（>500 点）优先 Vega-Lite + `transform: aggregate`，避免单个 JSON 过长。
