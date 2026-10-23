# B. WebGL / Three.js

适合：3D 场景、粒子系统、动态/交互画面、数据可视化大屏、游戏画面。这些场景 DOM 存在不等于渲染正确，必须实际预览并截图，运动类交互要观察多帧。

## 1. Three.js（推荐，WebGL 封装）

写自包含 HTML。Three.js 用 CDN 或本地文件（无网时把 `three.min.js` 放进工作区再引用）：

```html
<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><style>
  html,body{margin:0;overflow:hidden;background:#0d0221}
  canvas{display:block}
  #hud{position:fixed;top:12px;left:12px;color:#01efc8;font:14px monospace;z-index:1}
</style></head>
<body>
<div id="hud">Three.js demo</div>
<script type="importmap">
  {"imports": {"three": "https://unpkg.com/three@0.160.0/build/three.module.js",
               "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"}}
</script>
<script type="module">
  import * as THREE from 'three';
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, innerWidth/innerHeight, 0.1, 1000);
  camera.position.z = 5;
  const renderer = new THREE.WebGLRenderer({antialias:true});
  renderer.setSize(innerWidth, innerHeight);
  document.body.appendChild(renderer.domElement);

  // 四面体 + 线框
  const geo = new THREE.TetrahedronGeometry(1.2, 0);
  const mat = new THREE.MeshStandardMaterial({color:0xf72585, metalness:0.4, roughness:0.3});
  const mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);
  const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({wireframe:true, color:0x01efc8}));
  scene.add(wire);

  // 粒子背景
  const pgeo = new THREE.BufferGeometry();
  const n = 800, pos = new Float32Array(n*3);
  for (let i=0;i<n;i++){ pos[i*3]=(Math.random()-0.5)*20; pos[i*3+1]=(Math.random()-0.5)*20; pos[i*3+2]=(Math.random()-0.5)*20; }
  pgeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  scene.add(new THREE.Points(pgeo, new THREE.PointsMaterial({color:0x8ecae6, size:0.03})));

  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  scene.add(new THREE.DirectionalLight(0xffffff, 1));

  function tick(){
    mesh.rotation.x += 0.008; mesh.rotation.y += 0.012;
    requestAnimationFrame(tick);
    renderer.render(scene, camera);
  }
  tick();
</script>
</body>
</html>
```

## 2. 原生 WebGL（轻量/低依赖）

需要精确控制或避免大库时用。只画几何则手写 shader：

```html
<canvas id="c" width="600" height="600"></canvas>
<script>
  const c = document.getElementById('c'), gl = c.getContext('webgl');
  const vs = `attribute vec2 a; void main(){ gl_Position = vec4(a,0.0,1.0); }`;
  const fs = `precision mediump float; uniform vec2 uR; void main(){
    vec2 p = (gl_FragCoord.xy/uR) * 2.0 - 1.0;
    float d = length(p) - 0.6;                 // 圆到边界的距离
    float a = smoothstep(0.02, -0.02, d);      // 抗锯齿
    gl_FragColor = vec4(0.85, 0.03, 0.52, a);
  }`;
  function sh(t,s){const e=gl.createShader(t);gl.shaderSource(e,s);gl.compileShader(e);return e;}
  const pr = gl.createProgram();
  gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs));
  gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(pr); gl.useProgram(pr);
  gl.uniform2f(gl.getUniformLocation(pr,'uR'), c.width, c.height);
  const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, 1,1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr,'a'); gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
</script>
```

SDF 模板（`length(p)-r` 圆、`max(abs(p.x),abs(p.y))-s` 方、`length(vec2(p.x,p.y-c))` 圆环）配合 smoothstep 是最常用的抗锯齿绘制手法。

## 交付与验收

- 必须用内置浏览器打开页面，确认无控制台错误、画面按预期渲染（截图留证）。
- 动态/交互：至少观察一次动画或操作后的前后帧差异，不能只看首帧。
- 大屏数据可视化优先 Three.js 加 HTML overlay 或直接 SVG/Canvas，避免 WebGL 文字难排版。
- 依赖：Three.js 走 CDN 时注明版本；离线场景把库文件放进工作区并改为相对路径。
