import azulene

colors = {
    1:  (255, 0, 0),       # 红
    2:  (128, 0, 0),       # 栗色
    3:  (255, 255, 0),     # 黄
    4:  (128, 128, 0),     # 橄榄绿
    5:  (0, 255, 0),       # 亮绿
    6:  (0, 128, 0),       # 深绿
    7:  (0, 255, 255),     # 青
    8:  (0, 128, 128),     # 蓝绿
    9:  (0, 0, 255),       # 蓝
    10: (0, 0, 128),       # 藏蓝
    11: (255, 0, 255),     # 洋红
    12: (128, 0, 128),     # 紫
    13: (255, 255, 255),   # 白
    14: (192, 192, 192),   # 银
    15: (128, 128, 128),   # 灰
    16: (0, 0, 0),         # 黑
}

def draw(color,name,number):
    light_ring_r_end = 32
    color_r_start = 16
    color_r_end = 17
    color_r_end2 = 20
    white_r_end = 5

    main_canvas = azulene.drawing.Canvas(64,64)
    white_r_end_c = azulene.drawing.Circle(white_r_end)
    color_r_start_c = azulene.drawing.Circle(color_r_start)
    color_r_end_c = azulene.drawing.Circle(color_r_end)
    light_ring_r_end_c = azulene.drawing.Circle(light_ring_r_end)
    color_r_end2_c = azulene.drawing.Circle(color_r_end2)
    #light_ring_r_end_c.color = (0,*color)
    white_r_end_c.color = (255,255,255,255)
    color_r_start_c.color,color_r_end_c.color = (255,*color),(255,*color)

    color_r_end2_c.color = (0,*color)
    origin = azulene.drawing.point(0, 0)
    #origin.color = (255,255,255,255)
    c = [*color]
    t1 = 0.5
    t2 = 0
    c1 = (
        int(c[0] + (255 - c[0]) * t1),
        int(c[1] + (255 - c[1]) * t1),
        int(c[2] + (255 - c[2]) * t1)
    )
    c2 = (
            int(c[0] + (255 - c[0]) * t2),
            int(c[1] + (255 - c[1]) * t2),
            int(c[2] + (255 - c[2]) * t2)
        )
    origin.color = (255,*c1)
    light_ring_r_end_c.color = (0,*c2)

    main_canvas.fill_color(origin, light_ring_r_end_c, "1.1add", "alpha")
    origin.color = (255,255,255,255)
    main_canvas.fill_color(origin, white_r_end_c, "lerp", "alpha")
    main_canvas.fill_color(white_r_end_c, color_r_start_c, "3add", "alpha")
    main_canvas.fill_color(color_r_start_c, color_r_end_c, "lerp", "alpha")
    main_canvas.fill_color(color_r_end_c, color_r_end2_c, "2.5sub", "alpha")
    main_canvas.save("bullet/" + name + "/" + name + number + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"ball_light",str(k))
