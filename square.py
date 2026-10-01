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

def draw_square(color,name):
    white_a = 8*0.5
    white_b = 5*0.5
    color_a = 8
    color_b = 5

    main_canvas = azulene.drawing.Canvas(16,16)
    white_s = azulene.drawing.Polygon([(white_a,0),(0,white_b),(-white_a,0),(0,-white_b)])
    color_s = azulene.drawing.Polygon([(color_a,0),(0,color_b),(-color_a,0),(0,-color_b)])

    color_s.color = (255,*color)
    white_s.color = (255, 255, 255, 255)

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_s, "lerp", "alpha")
    main_canvas.fill_color(white_s, color_s, "2add", "alpha")
    main_canvas.save(name+".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw_square(v,"bullet/square/square"+str(k))
