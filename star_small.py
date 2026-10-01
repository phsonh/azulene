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

def draw_star_small(color,name):
    r0 = 8
    r1 = 5
    r_color_0= 3
    r_color_1= 3*(5/8)
    star0_positions_r = []#星星的顶点坐标
    star0_positions_r_color = []
    angle0,angle00 = 0,36#用于计算星星的极坐标角度
    i=1

    while i <= 5:
        star0_positions_r.append([r0*azulene.math.cos(angle0),r0*azulene.math.sin(angle0)])
        star0_positions_r.append([r1*azulene.math.cos(angle00),r1*azulene.math.sin(angle00)])
        star0_positions_r_color.append([r_color_0*azulene.math.cos(angle0),r_color_0*azulene.math.sin(angle0)])
        star0_positions_r_color.append([r_color_1*azulene.math.cos(angle00),r_color_1*azulene.math.sin(angle00)])
        #计算星星的顶点坐标存入star_positions
        i = i + 1
        angle0 += 72
        angle00 += 72
    main_canvas = azulene.drawing.Canvas(16,16)
    star = azulene.drawing.Polygon(star0_positions_r)                 # 大星星
    star_color = azulene.drawing.Polygon(star0_positions_r_color)     # 小星星

    star.color = color
    star_color.color = (255, 255, 255, 255)

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, star_color, "lerp", "alpha")
    main_canvas.fill_color(star_color, star, "2add", "alpha")

    main_canvas.save(name+".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw_star_small(v,"bullet/star_small/star_small"+str(k))
