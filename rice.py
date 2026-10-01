import azulene,math

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

def draw(color,name,number):
    WHITE_HALF_WIDTH = 7.0       # 两端位置：±8
    WHITE_PEAK_HEIGHT = 5.5      # 中心高度，实际返回值会除以 4
    WHITE_POWER = 3.5            # 越小，中间平坦范围越窄
    WHITE_SIDE_TIGHTNESS = 6.0  # 越大，两侧收得越紧
    WHITE_TIP_ROUNDNESS = 0.0   # 越大，端部越饱满
    WHITE_TIP_FOCUS = 0.0       # 越大，调整越集中在端部
    WHITE_END_VALUE = 0.1       # y = -8 和 y = 8 时的函数值

    COLOR_HALF_WIDTH = 8.0       # 两端位置：±8
    COLOR_PEAK_HEIGHT = 4.3      # 中心高度，实际返回值会除以 4
    COLOR_POWER = 3.5            # 越小，中间平坦范围越窄
    COLOR_SIDE_TIGHTNESS = 4.0  # 越大，两侧收得越紧
    COLOR_TIP_ROUNDNESS = 0.0   # 越大，端部越饱满
    COLOR_TIP_FOCUS = 0.0       # 越大，调整越集中在端部
    COLOR_END_VALUE = 0.1       # y = -8 和 y = 8 时的函数值

    def white_pottery_scale(y):
        t = (abs(y) / WHITE_HALF_WIDTH) ** WHITE_POWER
        tip = 1.0 + WHITE_TIP_ROUNDNESS * t ** WHITE_TIP_FOCUS
        shape = math.sqrt(
            max(0.0, 1.0 - t) * tip / (1.0 + WHITE_SIDE_TIGHTNESS * t)
        )
        return WHITE_END_VALUE + (WHITE_PEAK_HEIGHT / 4.0 - WHITE_END_VALUE) * shape

    def color_pottery_scale(y):
        t = (abs(y) / COLOR_HALF_WIDTH) ** COLOR_POWER
        tip = 1.0 + COLOR_TIP_ROUNDNESS * t ** COLOR_TIP_FOCUS
        shape = math.sqrt(
            max(0.0, 1.0 - t) * tip / (1.0 + COLOR_SIDE_TIGHTNESS * t)
        )
        return COLOR_END_VALUE + (COLOR_PEAK_HEIGHT / 4.0 - COLOR_END_VALUE) * shape

    white_poses = [[1.5,2],[-1.5,2],[-1.5,-2],[1.5,-2]]
    color_poses = [[3.5,7],[-3.5,7],[-3.5,-7],[3.5,-7]]
    main_canvas = azulene.drawing.Canvas(16,16)
    white_base = azulene.drawing.Polygon(white_poses)
    color_base = azulene.drawing.Polygon(color_poses)

    white_c = azulene.drawing.Pottery(
        white_base,
        profile=white_pottery_scale,
        y_range=(-6, 6),
        samples=128,
    )
    color_c = azulene.drawing.Pottery(
        color_base,
        profile=color_pottery_scale,
        y_range=(-8, 8),
        samples=128,
    )

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_c, "lerp", "alpha")
    main_canvas.fill_color(white_c, color_c, "2add", "alpha")
    main_canvas.rot = -90
    main_canvas.save("bullet/" + name + "/" + name + number + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"rice",str(k))
