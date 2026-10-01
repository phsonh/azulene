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

def draw_ball_mid(color,name):
    white_r = 6
    color_r = 13
    black_r_start = 11.5
    black_r_end = 13

    main_canvas = azulene.drawing.Canvas(32,32)
    white_c = azulene.drawing.Circle(white_r)
    color_c = azulene.drawing.Circle(color_r)
    black_c_start = azulene.drawing.Circle(black_r_start)
    black_c_end = azulene.drawing.Circle(black_r_end)

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    black_c_start.color = (0,0,0,0)
    black_c_end.color = (255,0,0,0)
    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_c, "lerp", "alpha")
    main_canvas.fill_color(white_c, color_c, "2add", "alpha")
    main_canvas.fill_color(black_c_start, black_c_end, "2add", "alpha")
    main_canvas.cut(black_c_end,"out")
    main_canvas.save(name+".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw_ball_mid(v,"bullet/ball_mid/ball_mid"+str(k))
