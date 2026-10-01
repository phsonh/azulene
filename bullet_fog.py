import random

import azulene


# 径向随机缩放参数。三层边界共用同一组倍率，避免渐变层互相穿插。
RADIAL_RANDOM_SEED = 20261001
RADIAL_ANGLE_STEP = 0.1
RADIAL_SCALE_MIN = 0.5
RADIAL_SCALE_MAX = 1.2

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
    white_r_end = 8
    color_r_start = 9
    color_r_end = 13.5
    main_canvas = azulene.drawing.Canvas(32,32)
    white_end = azulene.drawing.RadialScale(
        azulene.drawing.Circle(white_r_end),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    color_start = azulene.drawing.RadialScale(
        azulene.drawing.Circle(color_r_start),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )
    color_end = azulene.drawing.RadialScale(
        azulene.drawing.Circle(color_r_end),
        radial_scale,
        angle_step=RADIAL_ANGLE_STEP,
    )

    white_end.color = (255, 255, 255, 255)
    color_start.color = [255,*color[1:]]
    color_end.color = [0,*color[1:]]

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_end, "lerp", "alpha")
    main_canvas.fill_color(white_end, color_start, "1.5add", "alpha")
    main_canvas.fill_color(color_start, color_end, "1.5add", "alpha")
    main_canvas.save(name+".png",2)
for k,v in colors.items():

    draw(v,"bullet/bullet_fog/bullet_fog"+str(k))
