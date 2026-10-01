import math
from pathlib import Path

import azulene
from PIL import Image, ImageDraw, ImageFilter

colors = {
    1:  (255, 255, 0, 0),       # 红
    2:  (255, 128, 0, 0),       # 栗色
    3:  (255, 255, 255, 0),     # 黄
    4:  (255, 128, 128, 0),     # 橄榄绿
    5:  (255, 0, 255, 0),       # 亮绿
    6:  (255, 0, 128, 0),       # 深绿
    7:  (255, 0, 255, 255),     # 青
    8:  (255, 0, 128, 128),     # 蓝绿
    9:  (255, 0, 0, 255),       # 蓝
    10: (255, 0, 0, 128),       # 藏蓝
    11: (255, 255, 0, 255),     # 洋红
    12: (255, 128, 0, 128),     # 紫
    13: (255, 255, 255, 255),   # 白
    14: (255, 192, 192, 192),   # 银
    15: (255, 128, 128, 128),   # 灰
    16: (255, 0, 0, 0),         # 黑
}

# 七条右半边蝶翼路径的三次贝塞尔数据，运行时不依赖外部 JSON。
# 每段依次为：起点、控制点1、控制点2、终点。
BUTTERFLY_CURVE_SEGMENTS = {1: ((((-0.75, 3.4375), (-0.75, 3.4375), (-0.54160976, 3.60995102), (-0.68706036, 3.59256077)),
      ((-0.68706036, 3.59256077),
       (-0.71866894, 3.58878136),
       (0.23110008, 2.19676495),
       (-0.125, 2.1875)),
      ((-0.125, 2.1875),
       (-0.35140705, 2.18160915),
       (2.35362244, 9.85567522),
       (1.85936356, 8.91783857)),
      ((1.85936356, 8.91783857),
       (0.33250809, 6.02069473),
       (4.9250145, 12.0386169),
       (4.4375, 11.75)),
      ((4.4375, 11.75), (3.12151337, 10.97091389), (7.15170479, 12.56511641), (6.375, 12.4375)),
      ((6.375, 12.4375), (5.54703522, 12.30146146), (8.63575363, 12.02962422), (8.0625, 12.3125)),
      ((8.0625, 12.3125), (7.7896328, 12.44714808), (9.25, 10.875), (9.25, 10.875))),),
 2: ((((-0.4375, 0.8125), (-0.4375, 0.8125), (1.89291191, 2.84353924), (0.8125, 2.0625)),
      ((0.8125, 2.0625), (0.34202957, 1.72239304), (4.15358925, 3.95980358), (3.8125, 3.625)),
      ((3.8125, 3.625), (2.88727188, 2.71682358), (5.33919716, 6.3169899), (5.25, 6.125)),
      ((5.25, 6.125), (4.75221252, 5.053545), (6.64752007, 7.54788303), (6.19392967, 7.25980759)),
      ((6.19392967, 7.25980759), (5.62786293, 6.90029812), (7.93513107, 7.6746254), (7.375, 7.625)),
      ((7.375, 7.625), (7.12946129, 7.60324574), (9.58634949, 7.72964096), (8.9375, 7.75)),
      ((8.9375, 7.75), (8.70476341, 7.75730228), (11.44130898, 7.80934811), (10.75, 7.75)),
      ((10.75, 7.75), (10.38747025, 7.71887684), (12.83165741, 7.75475597), (12.6875, 7.75)),
      ((12.6875, 7.75), (11.9932766, 7.72709846), (13.82270622, 7.14651871), (13.5, 7.5)),
      ((13.5, 7.5), (13.25310898, 7.77043629), (13.16596413, 5.04401779), (13.4375, 5.8125)),
      ((13.4375, 5.8125), (13.67642212, 6.48868179), (12.12133026, 3.19498539), (12.5625, 3.875)),
      ((12.5625, 3.875), (12.71230316, 4.10590363), (10.89916229, 0.7389698), (11.25, 1.375)),
      ((11.25, 1.375), (11.73720932, 2.258255), (10.06580734, -0.84830856), (10.25, -0.4375)),
      ((10.25, -0.4375), (10.39946747, -0.10414314), (8.87486839, -2.89857674), (9.0, -2.6875)),
      ((9.0, -2.6875), (9.46917343, -1.89608192), (7.52783012, -3.81809998), (8.0, -3.625)),
      ((8.0, -3.625), (8.57831955, -3.38849068), (6.05828476, -3.54399872), (6.5, -3.625)),
      ((6.5, -3.625),
       (7.11701965, -3.73814774),
       (4.79423714, -3.29873276),
       (5.22279739, -3.39896393)),
      ((5.22279739, -3.39896393),
       (5.61104012, -3.48976517),
       (3.54505157, -2.95771408),
       (3.99111748, -3.06735802)),
      ((3.99111748, -3.06735802), (4.41851997, -3.17241478), (2.625, -2.8125), (2.625, -2.8125))),),
 3: ((((1.4375, -1.375), (1.4375, -1.375), (2.96591568, -3.55735779), (2.6875, -3.25)),
      ((2.6875, -3.25),
       (2.18184662, -2.691782),
       (4.21604729, -4.59436607),
       (3.63582611, -4.13323402)),
      ((3.63582611, -4.13323402),
       (3.28138542, -3.85154152),
       (5.72422409, -5.32483101),
       (5.25, -5.125)),
      ((5.25, -5.125), (4.76917458, -4.92238808), (7.06157494, -5.56281853), (6.5, -5.5)),
      ((6.5, -5.5), (6.22874451, -5.4696579), (7.80954361, -5.92692375), (7.6875, -5.75)),
      ((7.6875, -5.75),
       (7.50107384, -5.47974396),
       (7.13186073, -7.54039574),
       (7.49666977, -6.83345604)),
      ((7.49666977, -6.83345604),
       (7.78048515, -6.28346634),
       (6.04125404, -8.4332943),
       (6.33604813, -8.23093987)),
      ((6.33604813, -8.23093987),
       (6.70894623, -7.97497177),
       (5.70495605, -9.10737038),
       (5.74389267, -8.79940796)),
      ((5.74389267, -8.79940796),
       (5.77542305, -8.55003166),
       (6.99271393, -10.14366722),
       (6.5, -9.75)),
      ((6.5, -9.75), (6.0518589, -9.39194489), (7.20256233, -10.69869423), (7.25, -10.5625)),
      ((7.25, -10.5625),
       (7.30574226, -10.40246201),
       (6.05597687, -10.54704857),
       (6.62028122, -10.6942997)),
      ((6.62028122, -10.6942997),
       (6.88773155, -10.76408958),
       (5.28768158, -9.49451256),
       (5.45965958, -9.58105087)),
      ((5.45965958, -9.58105087),
       (5.99511909, -9.85049438),
       (3.65418053, -9.6233654),
       (4.0625, -9.5625)),
      ((4.0625, -9.5625), (4.70329285, -9.46697998), (2.58567238, -9.3183136), (3.125, -9.5625)),
      ((3.125, -9.5625),
       (3.41043472, -9.69173431),
       (2.22909164, -7.78679848),
       (2.35677338, -8.3256855)),
      ((2.35677338, -8.3256855),
       (2.4242878, -8.61063385),
       (1.85169601, -6.4227562),
       (1.9375, -6.8125)),
      ((1.9375, -6.8125),
       (2.05657005, -7.3533535),
       (1.27211952, -4.72929001),
       (1.48038483, -5.31754303)),
      ((1.48038483, -5.31754303),
       (1.66797829, -5.84740448),
       (0.45931244, -2.93279076),
       (0.75, -3.5625)),
      ((0.75, -3.5625), (1.02957726, -4.1681385), (-0.125, -1.6875), (-0.125, -1.6875))),),
 4: ((((8.625, 7.375), (8.625, 7.375), (8.83670425, 4.98385429), (8.75203514, 5.64914894)),
      ((8.75203514, 5.64914894),
       (8.68070793, 6.20960617),
       (8.67262077, 3.28238201),
       (8.75203514, 3.61213875)),
      ((8.75203514, 3.61213875),
       (8.94346046, 4.40699673),
       (7.83784676, 1.69595146),
       (8.20725441, 2.33308697)),
      ((8.20725441, 2.33308697),
       (8.48247528, 2.80777359),
       (6.28502846, 0.22955036),
       (6.76239777, 0.62768364)),
      ((6.76239777, 0.62768364),
       (7.34833336, 1.11636353),
       (4.24504089, -0.7265358),
       (4.84381866, -0.48556709)),
      ((4.84381866, -0.48556709),
       (5.66622543, -0.15460396),
       (2.97261238, -0.98297501),
       (2.97261238, -0.98297501))),),
 5: ((((11.5625, 7.125), (11.5625, 7.125), (11.26215935, 5.21625042), (11.4285717, 5.88601017)),
      ((11.4285717, 5.88601017),
       (11.52995682, 6.29405212),
       (10.0908165, 3.21399117),
       (10.67061424, 4.20429325)),
      ((10.67061424, 4.20429325),
       (10.99193001, 4.75310612),
       (10.14631844, 1.92411423),
       (10.03108788, 2.16728306)),
      ((10.03108788, 2.16728306),
       (9.80630493, 2.64163876),
       (10.6942997, 1.62250233),
       (10.6942997, 1.62250233))),),
 6: ((((0.41450691, -2.26202774),
       (0.41450691, -2.26202774),
       (1.77548218, -4.98005104),
       (1.29089546, -4.18060684)),
      ((1.29089546, -4.18060684),
       (0.92694855, -3.58018875),
       (3.27458572, -6.41500664),
       (2.75943756, -5.98075485)),
      ((2.75943756, -5.98075485),
       (2.34484291, -5.63126373),
       (4.67996597, -7.08712959),
       (4.34641075, -6.95188713)),
      ((4.34641075, -6.95188713),
       (3.81059074, -6.73463631),
       (6.00484276, -7.38890266),
       (5.83863831, -7.35455132)),
      ((5.83863831, -7.35455132),
       (5.27584076, -7.23822975),
       (6.33604813, -7.44929695),
       (6.33604813, -7.44929695))),),
 7: ((((0.3125, -0.3125), (0.3125, -0.3125), (1.55168533, -3.42240715), (1.3125, -3.0625)),
      ((1.3125, -3.0625), (0.76667595, -2.24118614), (3.48609924, -5.24580002), (2.875, -4.6875)),
      ((2.875, -4.6875), (2.23405647, -4.10193634), (5.07889366, -6.10606766), (4.5625, -5.875)),
      ((4.5625, -5.875), (3.93501472, -5.59422302), (6.1875, -6.3125), (6.1875, -6.3125))),)}

# 每条曲线可单独调整：
# center_width：中心色带的总宽度。
# center_alpha：中心色带透明度，0～255。
# edge_width：中心色带左右两侧各自增加的边缘宽度。
# edge_alpha：边缘色带透明度，0～255。
center_width_c = 0.7
center_alpha_c = 96
edge_width_c = 0.8
edge_alpha_c = 0
CURVE_STYLES = {
    1: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},
    2: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},
    3: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},
    4: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},
    5: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},
    6: {"center_width": center_width_c, "center_alpha": center_alpha_c, "edge_width": edge_width_c, "edge_alpha": edge_alpha_c},

    7: {"center_width": 0.35, "center_alpha": 96, "edge_width": 0.55, "edge_alpha": 32},
}

# 最底层白雾：同样沿七条曲线及其镜像绘制。
WHITE_MIST_CENTER_WIDTH = 4.0   # 白雾中心色带总宽度
WHITE_MIST_EDGE_WIDTH = 6.0     # 白雾中心两侧各自增加的宽度
WHITE_MIST_ALPHA = 96           # 白雾中心和边缘统一透明度
WHITE_MIST_EDGE_SOFTNESS = 2.0  # 白雾边缘羽化半径，单位为逻辑像素
WHITE_MIST_SIDE_MARGIN = 0.1   # 左右边界至少保留的透明距离

BEZIER_SAMPLES_PER_UNIT = 6


def cubic_bezier(segment, amount):
    """Evaluate one [start, control1, control2, end] cubic segment."""

    start, control1, control2, end = segment
    remaining = 1.0 - amount
    return (
        remaining ** 3 * start[0]
        + 3.0 * remaining ** 2 * amount * control1[0]
        + 3.0 * remaining * amount ** 2 * control2[0]
        + amount ** 3 * end[0],
        remaining ** 3 * start[1]
        + 3.0 * remaining ** 2 * amount * control1[1]
        + 3.0 * remaining * amount ** 2 * control2[1]
        + amount ** 3 * end[1],
    )


def sample_subpath(segments):
    """Sample connected cubic segments densely enough for the 32×32 canvas."""

    points = []
    for segment_index, segment in enumerate(segments):
        if len(segment) != 4:
            raise ValueError("each Bezier segment must contain four points")
        control_length = sum(
            math.hypot(
                segment[index + 1][0] - segment[index][0],
                segment[index + 1][1] - segment[index][1],
            )
            for index in range(3)
        )
        steps = max(8, math.ceil(control_length * BEZIER_SAMPLES_PER_UNIT))
        first_step = 0 if segment_index == 0 else 1
        points.extend(
            cubic_bezier(segment, step / steps)
            for step in range(first_step, steps + 1)
        )
    return points


def stroke_polygon(points, width):
    """Create a closed ribbon polygon centred on a sampled open curve."""

    if width <= 0:
        raise ValueError("curve widths must be positive")
    clean_points = [points[0]]
    for point in points[1:]:
        if math.hypot(
            point[0] - clean_points[-1][0],
            point[1] - clean_points[-1][1],
        ) > 1e-9:
            clean_points.append(point)
    if len(clean_points) < 2:
        raise ValueError("a Bezier subpath must contain two different points")

    half_width = width / 2.0
    left = []
    right = []
    for index, point in enumerate(clean_points):
        if index == 0:
            tangent_x = clean_points[1][0] - point[0]
            tangent_y = clean_points[1][1] - point[1]
        elif index == len(clean_points) - 1:
            tangent_x = point[0] - clean_points[index - 1][0]
            tangent_y = point[1] - clean_points[index - 1][1]
        else:
            tangent_x = clean_points[index + 1][0] - clean_points[index - 1][0]
            tangent_y = clean_points[index + 1][1] - clean_points[index - 1][1]
        tangent_length = math.hypot(tangent_x, tangent_y)
        normal_x = -tangent_y / tangent_length
        normal_y = tangent_x / tangent_length
        left.append(
            (
                point[0] + normal_x * half_width,
                point[1] + normal_y * half_width,
            )
        )
        right.append(
            (
                point[0] - normal_x * half_width,
                point[1] - normal_y * half_width,
            )
        )
    return azulene.drawing.Polygon(left + list(reversed(right)))


def build_curves():
    curves = []
    for curve_number, subpaths in BUTTERFLY_CURVE_SEGMENTS.items():
        for segments in subpaths:
            curves.append(
                (
                    curve_number,
                    sample_subpath(segments),
                )
            )
    return curves


BUTTERFLY_CURVES = build_curves()


def draw_curve_layer(canvas, color, styles=CURVE_STYLES):
    rgb = color[1:]
    layers = []
    for curve_number, source_points in BUTTERFLY_CURVES:
        style = styles[curve_number]
        center_width = float(style["center_width"])
        center_alpha = float(style["center_alpha"])
        edge_width = float(style["edge_width"])
        edge_alpha = float(style["edge_alpha"])
        if not 0 <= center_alpha <= 255 or not 0 <= edge_alpha <= 255:
            raise ValueError("curve alpha values must be between 0 and 255")
        if center_width <= 0 or edge_width < 0:
            raise ValueError("curve widths must be positive")

        for mirror in (1.0, -1.0):
            points = [(mirror * x, y) for x, y in source_points]
            center = stroke_polygon(points, center_width)
            outer = stroke_polygon(points, center_width + 2.0 * edge_width)
            layers.append((outer, edge_alpha, center, center_alpha))

    # 彩色曲线先统一铺边缘，再以 replace 写入中心色带，使两组
    # alpha 参数彼此独立。原来的球会在本函数返回后绘制到最上层。
    for outer, edge_alpha, _center, _center_alpha in layers:
        if edge_alpha > 0:
            outer.color = (edge_alpha, *rgb)
            canvas.fill_color(outer, "alpha")
    for _outer, _edge_alpha, center, center_alpha in layers:
        if center_alpha > 0:
            center.color = (center_alpha, *rgb)
            canvas.fill_color(center, "replace")


def render_white_mist(multiplier):
    """Render all Bezier strokes into one clean, constant-alpha union mask."""

    supersampling = 32
    logical_size = 32
    raster_size = logical_size * supersampling
    work_size = 48 * supersampling
    total_width = WHITE_MIST_CENTER_WIDTH + 2.0 * WHITE_MIST_EDGE_WIDTH
    stroke_width = max(1, round(total_width * supersampling))
    stroke_radius = stroke_width / 2.0
    mask = Image.new("L", (work_size, work_size), 0)
    painter = ImageDraw.Draw(mask)

    def to_screen(point):
        return (
            work_size / 2.0 + point[0] * supersampling,
            work_size / 2.0 - point[1] * supersampling,
        )

    for _curve_number, source_points in BUTTERFLY_CURVES:
        for mirror in (1.0, -1.0):
            points = [to_screen((mirror * x, y)) for x, y in source_points]
            painter.line(
                points,
                fill=255,
                width=stroke_width,
                joint="curve",
            )
            for point in (points[0], points[-1]):
                painter.ellipse(
                    (
                        point[0] - stroke_radius,
                        point[1] - stroke_radius,
                        point[0] + stroke_radius,
                        point[1] + stroke_radius,
                    ),
                    fill=255,
                )

    if WHITE_MIST_EDGE_SOFTNESS > 0:
        mask = mask.filter(
            ImageFilter.GaussianBlur(
                radius=WHITE_MIST_EDGE_SOFTNESS * supersampling
            )
        )

    # 根据羽化后的真实包围箱等比例缩放宽高，避免左右越界的同时
    # 保持原始曲线的纵横比例。
    bounds = mask.getbbox()
    if bounds is not None:
        content_width = bounds[2] - bounds[0]
        content_height = bounds[3] - bounds[1]
        allowed_width = max(
            1,
            round(
                (logical_size - 2.0 * WHITE_MIST_SIDE_MARGIN)
                * supersampling
            ),
        )
        allowed_height = raster_size
        uniform_scale = min(
            1.0,
            allowed_width / content_width,
            allowed_height / content_height,
        )
        if uniform_scale < 1.0:
            mask = mask.resize(
                (
                    max(1, round(mask.width * uniform_scale)),
                    max(1, round(mask.height * uniform_scale)),
                ),
                Image.Resampling.LANCZOS,
            )

    # 以中心为准裁到正式画布；前面的等比缩放保证不会改变纵横比例。
    left = (mask.width - raster_size) // 2
    top = (mask.height - raster_size) // 2
    if left >= 0 and top >= 0:
        mask = mask.crop(
            (left, top, left + raster_size, top + raster_size)
        )
    else:
        centred = Image.new("L", (raster_size, raster_size), 0)
        source_left = max(0, -left)
        source_top = max(0, -top)
        source_right = min(mask.width, source_left + raster_size)
        source_bottom = min(mask.height, source_top + raster_size)
        cropped = mask.crop(
            (source_left, source_top, source_right, source_bottom)
        )
        centred.paste(
            cropped,
            (
                max(0, (raster_size - cropped.width) // 2),
                max(0, (raster_size - cropped.height) // 2),
            ),
        )
        mask = centred

    alpha = mask.point(
        lambda value: round(value * WHITE_MIST_ALPHA / 255.0)
    )
    mist = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    mist.putalpha(alpha)
    output_size = max(1, round(logical_size * multiplier))
    return (
        mist.convert("RGBa")
        .resize((output_size, output_size), Image.Resampling.HAMMING)
        .convert("RGBA")
    )

def draw(color,name):
    white_r = 3.25
    color_end_r = 5.5
    color_start_r = 4.25
    main_canvas = azulene.drawing.Canvas(32,32)
    white_c = azulene.drawing.Circle(white_r)
    color_end_c = azulene.drawing.Circle(color_end_r)
    color_start_c = azulene.drawing.Circle(color_start_r)
    edge_c = color_end_c.refine_edge(4)
    edge_c.color = (0, 255, 255, 255)
    color_end_c.color = color
    color_start_c.color = color
    white_c.color = (255, 255, 255, 255)

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    # 彩色曲线位于白雾上方；中心弹体最后遮住曲线根部。
    draw_curve_layer(main_canvas, color)
    main_canvas.fill_color(origin, white_c, "lerp", "alpha")
    main_canvas.fill_color(white_c, color_start_c, "lerp", "alpha")
    main_canvas.fill_color(color_start_c, color_end_c, "lerp", "alpha")
    main_canvas.fill_color(color_end_c, edge_c, "2sub", "alpha")
    
    main_canvas.rot = -90
    output_multiplier = 2
    foreground = main_canvas.render(output_multiplier)
    result = render_white_mist(output_multiplier)
    if main_canvas.rot % 360.0 != 0.0:
        result = (
            result.convert("RGBa")
            .rotate(
                main_canvas.rot,
                resample=Image.Resampling.BILINEAR,
                expand=False,
                fillcolor=(0, 0, 0, 0),
            )
            .convert("RGBA")
        )
    result.alpha_composite(foreground)
    output_path = Path(name + ".png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"bullet/butterfly/butterfly"+str(k))
