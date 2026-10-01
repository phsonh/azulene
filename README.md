# Azulene

Azulene 是一套用于制作和渲染 **东方 Project 正作风格高分辨率子弹贴图** 的 Python 模块。

它使用几何边界、颜色插值和高倍率内部栅格化来生成透明 PNG，适合批量制作圆弹、星弹、刀弹、激光、火焰等弹幕素材。项目根目录中的脚本是现成示例，生成结果默认放在 `bullet/` 下。

## 特点

优点：

- 使用逻辑分辨率描述图形，可以方便地对照其他分辨率贴图重绘。
- 导出时内部按 32 倍分辨率栅格化，再缩小得到平滑的透明边缘。
- 原生支持 ARGB 颜色、透明度、非线性渐变和多种混合模式。
- 圆形、多边形、隐式方程、径向扰动和一维形变可以组合使用。
- 固定随机种子后可以稳定生成逐帧一致、各颜色一致的素材。
- 适合用同一套结构批量导出东方风格的 16 色子弹。

限制：

- 当前是 CPU 软件渲染，复杂多边形、高采样数和大量图片会比较慢。
- 主要面向中心对称或接近中心对称的 2D 子弹贴图，不是通用矢量编辑器。

## 安装

需要 Python 3.10 或更高版本。

```powershell
python -m pip install -e .
```

依赖会自动安装：

- NumPy 2.0+
- Pillow 11.0+

## 基本约定

### 坐标

- 画布中心是 `(0, 0)`。
- x 轴向右为正，y 轴向上为正。
- 所有旋转角度都使用角度制，逆时针为正。
- `Canvas(x, y)` 表示 x × y 的逻辑画布。

### 颜色

颜色可使用列表或元组：

```python
[255, 255, 0, 0]  # ARGB：完全不透明的红色
(255, 0, 0)       # RGB：省略 alpha 时默认为 255
```

四通道顺序是 **ARGB**，不是 RGBA。通道值允许暂时超出 `0..255`，最终栅格化时才会限制到有效范围。

## 最小示例

```python
import azulene

canvas = azulene.drawing.Canvas(32, 32)

origin = azulene.drawing.point(0, 0)
white = azulene.drawing.Circle(5)
edge = azulene.drawing.Circle(12)

origin.color = (255, 255, 255, 255)
white.color = (255, 255, 255, 255)
edge.color = (0, 255, 0, 0)

canvas.fill_color(origin, white, "lerp", "alpha")
canvas.fill_color(white, edge, "2add", "alpha")
canvas.save("output.png", 2)
```

这里的导出倍率 `2` 会生成 64×64 PNG。

## 核心图形 API

### 点

```python
p1 = azulene.drawing.point(0, 0)
p2 = azulene.drawing.point([2, 3])
p1.color = (255, 255, 255, 255)
```

点通常作为插值的颜色起点。

### 多边形

```python
polygon = azulene.drawing.Polygon([
    (0, 8),
    (-6, -5),
    (6, -5),
])

polygon.color = (255, 255, 0, 0)
polygon.scale_x = 0.8
polygon.scale_y = 1.2
polygon.rot = 30
```

常用方法：

```python
larger = polygon.refine_edge(1)    # 边缘向外偏移 1
smaller = polygon.refine_edge(-1)  # 边缘向内偏移 1
scaled = polygon.scale_uniform(0.8) # 围绕局部原点等比缩放
```

只传两个点时会得到零宽度线段：

```python
line = azulene.drawing.Polygon([(-4, 0), (4, 0)])
```

### 圆形

```python
circle = azulene.drawing.Circle(8)        # 半径 8，圆心 (0, 0)
circle2 = azulene.drawing.Circle(8, 2, 3) # 半径 8，圆心 (2, 3)

circle.scale_x = 0.5  # 变成椭圆
circle.scale_y = 1.0
circle.rot = 45
```

圆形同样支持 `refine_edge()` 和 `scale_uniform()`。

### 隐式闭合曲线

```python
heart = azulene.drawing.Implicit(
    lambda x, y: (x*x + y*y - 1) ** 3 - x*x * y ** 3,
    x_range=(-1.5, 1.5),
    y_range=(-1.5, 1.5),
    samples=512,
)
```

`Implicit` 会从 `equation(x, y) == level` 中提取面积最大的闭合边界。

### 径向缩放

`RadialScale` 根据角度函数改变圆在各方向上的半径，并返回一个可正常填色的闭合多边形。

```python
import random

rng = random.Random(1234)
step = 2.5
scales = [rng.uniform(0.9, 1.1) for _ in range(round(360 / step))]

def profile(angle):
    return scales[int(round(angle / step)) % len(scales)]

edge = azulene.drawing.RadialScale(
    azulene.drawing.Circle(12),
    profile,
    angle_step=step,
)
```

需要制作多层渐变时，各层应共用同一个 `profile`，否则边界可能互相穿插。

## Canvas API

### 创建和放置

```python
canvas = azulene.drawing.Canvas(64, 64)
canvas.put(shape, 3, -2)
canvas.put(shape, [3, -2])
```

`put()` 记录图形相对画布中心的偏移。直接使用以 `(0, 0)` 为中心创建的图形时通常不需要调用它。

### 填充单个闭合图形

```python
shape.color = (255, 255, 0, 0)
canvas.fill_color(shape, "alpha")
```

也可以显式写为：

```python
canvas.fill_color(shape, blend_mode="alpha")
```

### 在两个边界之间插值

```python
canvas.fill_color(inner, outer, "2add", "alpha")
```

插值曲线：

- `"lerp"` 或 `"1"`：线性插值。
- `"数字add"`：幂次增加，例如 `"1.5add"`、`"2add"`。
- `"数字sub"`：幂次减少，例如 `"1.564sub"`、`"3sub"`。

指数会自动解析，不需要预先枚举。

混合模式：

- `"replace"`：直接替换。
- `"alpha"`：标准 Alpha 混合。
- `"add"`：加色。
- `"sub"`：减色。
- `"mul"`：乘色。

### 插值方向和原点

```python
canvas.interpolation_mode = "r"  # 径向
canvas.interpolation_mode = "w"  # 横向，从原点向左右
canvas.interpolation_mode = "h"  # 纵向，从原点向上下

origin = azulene.drawing.point(4, 0)
canvas.set_origin(origin)
```

如果没有调用 `set_origin()`，插值原点默认为 `(0, 0)`。

### 边缘着色

```python
canvas.shade_edge(
    boundary,
    (160, 0, 0, 0),
    radius=2,
    method="2add",
)
```

`shade_edge()` 会沿真实边缘的内法线向内部渐变，适合制作描边和背光。它只改变已有像素的 RGB，保留原 Alpha。

### 裁切

```python
result = canvas.cut(boundary, "out") # 清除边界外部
result = canvas.cut(boundary, "in")  # 清除边界内部
```

`cut()` 会直接修改画布，并返回一个携带当前图像快照的多边形或圆形对象。零宽度线段不能用于裁切。

### 旋转和导出

```python
canvas.rot = 90

canvas.save("output.png", 2)       # x、y 都放大 2 倍
canvas.save("output.png", 2, 3)    # x 放大 2 倍，y 放大 3 倍

image = canvas.render(2)            # 返回 Pillow RGBA Image
```

## 一维形变

### Pottery

`Pottery` 是交叉方向形变：

- `y_range`：让 `scale_x` 随 y 变化。
- `x_range`：让 `scale_y` 随 x 变化。

```python
shape = azulene.drawing.Pottery(
    base_shape,
    profile=lambda y: 0.6 + 0.4 * (1 - (y / 8) ** 2),
    y_range=(-8, 8),
    samples=256,
)
```

### Stretch

`Stretch` 是同方向局部拉伸：

- `x_range`：让局部 `scale_x` 随 x 变化。
- `y_range`：让局部 `scale_y` 随 y 变化。

```python
stretched = azulene.drawing.Stretch(
    canvas,
    profile=lambda x: 1.0 + 0.5 * (1 - (x / 8) ** 2),
    x_range=(-8, 8),
)
stretched.save("stretched.png", 2)
```

两者都接受 `Polygon`、`Circle` 或 `Canvas`。从画布创建时，它们可以作为独立渲染目标调用 `save()`。

## 火焰

```python
flame = azulene.drawing.Flame(
    size=(64, 96),
    frames=6,
    seed=2009307696,
)

frames = flame.render((255, 255, 0, 0))
atlas = flame.atlas((255, 255, 0, 0))
flame.save("fire.png", (255, 255, 0, 0))
```

`Flame` 使用固定随机种子的流场生成动画帧。更完整的参数示例见 [fire.py](fire.py)。

## 数学辅助

三角函数使用角度制：

```python
azulene.math.sin(90)  # 1.0
azulene.math.cos(60)  # 0.5
azulene.math.tan(45)  # 1.0
```

混合两个 RGB 颜色：

```python
mixed = azulene.math.blend_color(
    [255, 0, 0],
    [255, 255, 255],
    0.5,
)
```

`alpha` 是第二个颜色的权重，返回一个三元素列表。颜色通道不会在这里提前限制。

## 示例脚本

项目根目录包含多种子弹的完整生成脚本，例如：

- [ball_big.py](ball_big.py)：多层圆弹与随机径向边缘。
- [star_big.py](star_big.py)：星形弹。
- [heart.py](heart.py)：高分辨率心形弹。
- [butterfly.py](butterfly.py)：贝塞尔纹路与雾层。
- [knife.py](knife.py)：刀形弹。
- [fire.py](fire.py)：多帧火焰。

这些脚本也是当前 API 最直接的使用参考。
