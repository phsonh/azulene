import math

import azulene


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


color_end_r = 14.0
black_solid_start_r = 14.75
black_end_r = 15.0
outer_y_radius = 15.0

#贝塞尔曲线的控制点
heart_bezier_controls = [
    (0.0, -16.0),
    (0.8, -16.0),
    (1.6, -12.0),
    (8.0, 4.0),
    (6.2453, 14.0),
    (0.7023, 18.0),
    (0.4676, 20.0),
    (0.2799, 20.0),
    (0.1408, 11.0),
    (0.0704, 5.6),
    (0.0, 3.8),
    (-0.0704, 5.6),
    (-0.1408, 11.0),
    (-0.2799, 20.0),
    (-0.4676, 20.0),
    (-0.7023, 18.0),
    (-6.2453, 14.0),
    (-8.0, 4.0),
    (-1.6, -12.0),
    (-0.8, -16.0),
    (0.0, -16.0),
]
bezier_samples = 1024
bezier_degree = 40
upper_x_scale = 0.73515


def elevate_bezier_controls(controls, target_degree):
    elevated = [tuple(point) for point in controls]
    while len(elevated) - 1 < target_degree:
        degree = len(elevated) - 1
        next_controls = [elevated[0]]
        for index in range(1, degree + 1):
            amount = index / (degree + 1)
            before = elevated[index - 1]
            after = elevated[index]
            next_controls.append(
                (
                    amount * before[0] + (1 - amount) * after[0],
                    amount * before[1] + (1 - amount) * after[1],
                )
            )
        next_controls.append(elevated[-1])
        elevated = next_controls
    return elevated


def smooth_heart_boundary(x_radius, y_radius):
    base_controls = [list(point) for point in heart_bezier_controls]
    for index in list(range(4, 10)) + list(range(11, 17)):
        base_controls[index][0] *= upper_x_scale
    controls = elevate_bezier_controls(
        base_controls,
        bezier_degree,
    )
    lower_line_slope = 3.8
    lower_line_x = (0.8, 1.4, 2.1, 2.9, 3.7)
    for index, x in enumerate(lower_line_x, start=2):
        y = -16.0 + lower_line_slope * x
        controls[index] = (x, y)
        controls[-index - 1] = (-x, y)

    degree = len(controls) - 1
    positions = []
    for sample in range(bezier_samples):
        amount = sample / bezier_samples
        inverse = 1 - amount
        x = 0.0
        y = 0.0
        for index, (control_x, control_y) in enumerate(controls):
            weight = (
                math.comb(degree, index)
                * inverse ** (degree - index)
                * amount**index
            )
            x += weight * control_x
            y += weight * control_y
        positions.append((x, y))

    maximum_x = max(abs(x) for x, _ in positions)
    minimum_y = min(y for _, y in positions)
    maximum_y = max(y for _, y in positions)
    y_center = (minimum_y + maximum_y) / 2
    y_scale = 2 * y_radius / (maximum_y - minimum_y)
    return [
        (
            x / maximum_x * x_radius,
            (y - y_center) * y_scale,
        )
        for x, y in positions
    ]


outer_positions = smooth_heart_boundary(black_end_r, outer_y_radius)
black_solid_positions = smooth_heart_boundary(
    black_solid_start_r,
    outer_y_radius * black_solid_start_r / black_end_r,
)
color_positions = smooth_heart_boundary(
    color_end_r,
    outer_y_radius * color_end_r / black_end_r,
)
white_positions = smooth_heart_boundary(8, 8)


def draw(color, name, number):
    outer_heart = azulene.drawing.Polygon(outer_positions)
    black_solid_heart = azulene.drawing.Polygon(black_solid_positions)
    color_heart = azulene.drawing.Polygon(color_positions)
    white_heart = azulene.drawing.Polygon(white_positions)

    outer_heart.color = (255, 0, 0, 0)
    black_solid_heart.color = (255, 0, 0, 0)
    color_heart.color = color
    white_heart.color = (255, 255, 255, 255)
    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas = azulene.drawing.Canvas(32, 32)
    main_canvas.set_origin(origin)
    main_canvas.fill_color(origin, white_heart, "2add", "alpha")
    main_canvas.fill_color(white_heart, color_heart, "2add", "alpha")
    main_canvas.fill_color(
        color_heart,
        black_solid_heart,
        "lerp",
        "alpha",
    )
    main_canvas.fill_color(
        black_solid_heart,
        outer_heart,
        "lerp",
        "alpha",
    )
    main_canvas.rot = 90
    main_canvas.save("bullet/" + name + "/" + name + str(number) + ".png", 2)
    print(name + "/" + name + str(number) + ".png渲染完成" )


for k, v in colors.items():
    draw(v, "heart", k)
    
