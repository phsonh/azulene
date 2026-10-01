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
    def pottery_scale(y):
        HALF_WIDTH = 8.0
        PEAK_HEIGHT = 4.25
        POWER = 3.5
        SIDE_TIGHTNESS = 4.0
        TIP_ROUNDNESS = 0  # 越大，端部越饱满
        TIP_FOCUS = 0.0      # 越大，调整越集中在端部
        
        t = (abs(y) / HALF_WIDTH) ** POWER
        tip = 1.0 + TIP_ROUNDNESS * t ** TIP_FOCUS
        if y >=0:
            return (PEAK_HEIGHT / 4.5) * math.sqrt(
                max(0.0, 1.0 - t) * tip / (1.0 + SIDE_TIGHTNESS * t)
            )
        else:
            return 1

    white_poses = [[2,4],[-2,4],[-2,-6],[2,-6]]
    color_poses = [[3.5,7],[-3.5,7],[-3.5,-7],[3.5,-7]]
    main_canvas = azulene.drawing.Canvas(16,16)
    white_base = azulene.drawing.Polygon(white_poses)
    color_base = azulene.drawing.Polygon(color_poses)

    white_c = azulene.drawing.Pottery(
        white_base,
        profile=pottery_scale,
        y_range=(-6, 6),
        samples=128,
    )
    color_c = azulene.drawing.Pottery(
        color_base,
        profile=pottery_scale,
        y_range=(-8, 8),
        samples=128,
    )

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_c, "lerp", "alpha")
    main_canvas.fill_color(white_c, color_c, "lerp", "alpha")
    main_canvas.rot = -90
    main_canvas.save("bullet/" + name + "/" + name + number + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"gun",str(k))
