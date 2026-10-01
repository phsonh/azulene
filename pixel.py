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

def draw(color,name,number):
    pos = [
        [0,4],
        [-3,1],
        [-3,-1],
        [0,-4],
        [3,-1],
        [3,1]
    ]
    color_rz = 1
    white_rz = 0.5
    color_pos = []
    white_pos = []
    for i in pos:
        color_pos.append([i[0]*color_rz,i[1]*color_rz])
        white_pos.append([i[0]*white_rz,i[1]*white_rz])
    
    main_canvas = azulene.drawing.Canvas(8,8)
    white_c = azulene.drawing.Polygon(white_pos)
    color_c = azulene.drawing.Polygon(color_pos)

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    color_c.rot = 90
    white_c.rot = 90

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(origin, white_c, "lerp", "alpha")
    main_canvas.fill_color(white_c, color_c, "2add", "alpha")

    main_canvas.save("bullet/" + name + "/" + name + str(number) + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"pixel",k)
