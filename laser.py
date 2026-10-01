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
    white_poses = [[2,8],[-2,8],[-2,-8],[2,-8]]
    color_poses = [[8,8],[-8,8],[-8,-8],[8,-8]]
    main_canvas = azulene.drawing.Canvas(16,16,"w")
    white_c = azulene.drawing.Polygon(white_poses)
    color_c = azulene.drawing.Polygon(color_poses)

    

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)
    main_canvas.set_origin(origin)
    main_canvas.fill_color(origin, color_c, "2add", "alpha")
    main_canvas.rot = -90
    
    main_canvas.save("bullet/" + name + "/" + name + number + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"laser",str(k))
