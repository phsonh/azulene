import random
from pathlib import Path

import azulene


# 径向随机缩放参数。所有同心层共用同一组倍率，避免渐变层彼此穿插。
RADIAL_RANDOM_SEED = 2026
RADIAL_ANGLE_STEP = 2.5
RADIAL_SCALE_MIN = 0.75
RADIAL_SCALE_MAX = 1

_radial_random = random.Random(RADIAL_RANDOM_SEED)
_radial_scales = [
    _radial_random.uniform(RADIAL_SCALE_MIN, RADIAL_SCALE_MAX)
    for _ in range(round(360 / RADIAL_ANGLE_STEP))
]


def radial_scale(angle):
    """返回当前角度对应的固定随机径向倍率。"""
    index = int(round(angle / RADIAL_ANGLE_STEP)) % len(_radial_scales)
    return _radial_scales[index]

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

def draw(color,name):

    r_black_end = 10.5
    r_color_begin = 16
    r_color_end = 18
    r_white_begin = 26
    r_edge = 30
    
    main_canvas = azulene.drawing.Canvas(64,64)
    sub_canvas = azulene.drawing.Canvas(64,64)
    origin = azulene.drawing.point(0, 0)
    sub_white_c = azulene.drawing.Circle(r_edge)
    black_end_c = azulene.drawing.RadialScale(
        azulene.drawing.Circle(r_black_end),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    color_begin_c = azulene.drawing.RadialScale(
        azulene.drawing.Circle(r_color_begin),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    color_end_c = azulene.drawing.RadialScale(
        azulene.drawing.Circle(r_color_end),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    white_begin_c = azulene.drawing.RadialScale(
        azulene.drawing.Circle(r_white_begin),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    edge_c = azulene.drawing.RadialScale(
        azulene.drawing.Circle(r_edge),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )

    origin.color,black_end_c.color = [255,255,255,255],[255,0,0,0]
    color_begin_c.color,color_end_c.color = color,color
    white_begin_c.color,edge_c.color = (255, 255, 255, 255),(255, 255, 255, 255)
    sub_white_c.color = (255, 255, 255, 255)

    # sub 先画完整的白色底圆。
    sub_canvas.fill_color(sub_white_c, "alpha")

    # main 单独完成径向随机轮廓和各层颜色。
    main_canvas.fill_color(black_end_c, "alpha")
    main_canvas.fill_color(black_end_c, color_begin_c, "1add", "alpha")
    main_canvas.fill_color(color_begin_c, color_end_c, "1add", "alpha")
    main_canvas.fill_color(color_end_c, white_begin_c, "1add", "alpha")
    main_canvas.fill_color(white_begin_c, edge_c, "1add", "alpha")

    # 两张逻辑画布分别以目标倍率栅格化，再把 main 盖到 sub 上。
    # 这样透明区域会露出白色底圆，同时保留两层各自的抗锯齿边缘。
    output = sub_canvas.render(2)
    output.alpha_composite(main_canvas.render(2))
    destination = Path(name + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"bullet/ball_big/ball_big"+str(k))
