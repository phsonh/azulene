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
    edge_end_pos = [[4,4],[0,8],[-4,4],[-4,-4],[0,-8],[4,-4]]

    main_canvas = azulene.drawing.Canvas(16,16)
    edge_end = azulene.drawing.Polygon(edge_end_pos)
    edge_start = edge_end.refine_edge(-1)
    
    edge_end.color = (255,*color)
    edge_start.color = (0,*color)
    dy1,dy2 = 0.5,1.5
    #右侧矩形
    part0 = azulene.drawing.Polygon([[4,4],[0,4-dy1],[0,-4-dy2],[4,-4]])
    part0.color = [255,*azulene.math.blend_color(color,[255,255,255],0.5)]

    #右下角
    part1 = azulene.drawing.Polygon([[4,-4],[0,-4-dy2],[0,-8]])
    part1.color = [255,255,255,255]

    #左下角
    part2 = azulene.drawing.Polygon([[-4,-4],[0,-4-dy2],[0,-8]])
    part2.color = [255,*azulene.math.blend_color(color,[255,255,255],0.25)]

    #左侧矩形
    part3 = azulene.drawing.Polygon([[-4,4],[0,4-dy1],[0,-4-dy2],[-4,-4]])
    part3.color = (255,*color)

    #右上角
    part4 = azulene.drawing.Polygon([[4,4],[0,8],[0,4-dy1]])
    part4.color = (255,*color)

    #左上角
    part5 = azulene.drawing.Polygon([[-4,4],[0,8],[0,4-dy1]])
    part5.color = [255,*azulene.math.blend_color(color,[0,0,0],0.5)]


    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.fill_color(part0, "alpha")
    main_canvas.fill_color(part1, "alpha")
    main_canvas.fill_color(part2, "alpha")
    main_canvas.fill_color(part3, "alpha")
    main_canvas.fill_color(part4, "alpha")
    main_canvas.fill_color(part5, "alpha")
    main_canvas.fill_color(edge_start,edge_end,"2add", "alpha")
    main_canvas.rot = 90
    main_canvas.save(name+".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw_square(v,"bullet/neddle/neddle"+str(k))
