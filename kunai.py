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

    hole_white_r_start = 1
    hole_white_r_end = 2
    hole_color_r_start = hole_white_r_end
    hole_color_r_end = 3
    color_r = 4
    main_canvas = azulene.drawing.Canvas(16,16)
    hole_white_c_start = azulene.drawing.Circle(hole_white_r_start,0,5)
    hole_white_c_end = azulene.drawing.Circle(hole_white_r_end,0,5)
    hole_color_c_start = azulene.drawing.Circle(hole_color_r_start,0,5)
    hole_color_c_end = azulene.drawing.Circle(hole_color_r_end,0,5)

    hole_white_c_start.color,hole_white_c_end.color = (255, 255, 255, 255),(255, 255, 255, 255)
    hole_color_c_start.color,hole_color_c_end.color = color,color
    origin = azulene.drawing.point(0, 0)
    hole = azulene.drawing.point(0, 5)
    origin.color = (255, 255, 255, 255)


    head_part1_pos = [[3.5,0.5],[0,0.5],[0,-7]]
    head_part2_pos = [[-3.5,0.5],[0,0.5],[0,-7]]
    head_edge_start_pos = [[2.5,0],[-2.5,0],[0,-7]]
    head_edge_end_pos = [[4,1],[-4,1],[0,-8]]
    connect_handle_pos = [[1,1],[1,2],[-1,2],[-1,1]]

    head_part1 = azulene.drawing.Polygon(head_part1_pos)
    head_part2 = azulene.drawing.Polygon(head_part2_pos)
    connect_handle = azulene.drawing.Polygon(connect_handle_pos)

    head_edge_start = azulene.drawing.Polygon(head_edge_start_pos)
    
    head_edge_end = azulene.drawing.Polygon(head_edge_end_pos)

    connect_handle.color = color
    head_part1.color = [255,255,255,255]
    c = list(color[1:4])
    head_part2.color = [255,c[0],c[1],c[2]]
    
    head_edge_start.color = [128,c[0],c[1],c[2]]
    head_edge_end.color = color

    main_canvas.fill_color(hole_white_c_start, hole_white_c_end, "lerp", "alpha")
    main_canvas.fill_color(hole_color_c_start, hole_color_c_end, "2add", "alpha")
    main_canvas.fill_color(connect_handle,blend_mode="alpha")

    main_canvas.fill_color(head_part1,blend_mode="alpha")
    main_canvas.fill_color(head_part2,blend_mode="alpha")
    head_part2.color = [128,255,255,255]
    main_canvas.fill_color(head_part2,blend_mode="alpha")

    main_canvas.fill_color(head_edge_start, head_edge_end, "2add", "alpha")
    main_canvas.rot = 90
    main_canvas.save("bullet/" + name + "/" + name + str(number) + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"kunai",k)
