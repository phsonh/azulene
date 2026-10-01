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
    shell_vertex_end = [7,8]
    shell_vertex_start = [6,7]
    edge_vertex_end = shell_vertex_start
    edge_vertex_start = [5,6]
    white_vertex_end = edge_vertex_start
    

    main_canvas = azulene.drawing.Canvas(16,16)
    shell_vertex_end_quad = azulene.drawing.Polygon(
        [[sx * shell_vertex_end[0], sy * shell_vertex_end[1]] for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]]
    )
    shell_vertex_start_quad = azulene.drawing.Polygon(
        [[sx * shell_vertex_start[0], sy * shell_vertex_start[1]] for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]]
    )
    edge_vertex_end_quad = azulene.drawing.Polygon(
        [[sx * edge_vertex_end[0], sy * edge_vertex_end[1]] for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]]
    )
    edge_vertex_start_quad = azulene.drawing.Polygon(
        [[sx * edge_vertex_start[0], sy * edge_vertex_start[1]] for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]]
    )
    white_vertex_end_quad = azulene.drawing.Polygon(
        [[sx * white_vertex_end[0], sy * white_vertex_end[1]] for sx, sy in [(1, 1), (1, -1), (-1, -1), (-1, 1)]]
    )
    shell_vertex_end_quad.color,shell_vertex_start_quad.color = [96,255,255,255],[96,255,255,255]
    edge_vertex_end_quad.color, edge_vertex_start_quad.color = (
    [255, *azulene.math.blend_color(color, [255,255,255], 1/5)],
    [255, *azulene.math.blend_color(color, [255,255,255], 1/5)],
)
    origin = azulene.drawing.point(0, 0)
    origin.color,white_vertex_end_quad.color = (255, 255, 255, 255),(255, 255, 255, 255)


    sign_part1_edge_out = azulene.drawing.Polygon([[3,4],[-3,4],[-3,1],[3,1]])
    sign_part1_edge_in = azulene.drawing.Polygon([[2,3],[-2,3],[-2,2],[2,2]])
    sign_part1_edge_out.color,sign_part1_edge_in.color = color,color
    sign_part2_edge_out = azulene.drawing.Polygon([[1,1],[-1,1],[-1,-1],[1,-1]])
    sign_part2_edge_out.color = color

    sign_part1_1_edge_out = azulene.drawing.Polygon([[-4,3],[-4,4],[-3,4],[-3,3]])
    sign_part1_1_edge_out.color = [2*255/3,*color]
    sign_part1_2_edge_out = azulene.drawing.Polygon([[-4,1],[-4,2],[-3,2],[-3,1]])
    sign_part1_2_edge_out.color = [2*255/3,*color]

    sign_part3_edge_out = azulene.drawing.Polygon([[-3,-1],[3,-1],[3,-2],[-3,-2]])
    sign_part3_edge_out.color = color

    sign_part3_1_edge_out = azulene.drawing.Polygon([[-2,0],[-3,0],[-3,-1],[-2,-1]])
    sign_part3_1_edge_out.color = [255/2,*color]

    sign_part4_edge_out = azulene.drawing.Polygon([[3,-2],[2,-2],[2,-3],[3,-3]])
    sign_part4_edge_out.color = color
    sign_part4_1_edge_out = azulene.drawing.Circle(0.75,-2.75,-3.5)
    sign_part4_1_edge_out.color = color
    sign_part4_2_edge_out = azulene.drawing.Circle(0.75,0.25,-4)
    sign_part4_2_edge_out.color = color
    
    main_canvas.fill_color(origin, white_vertex_end_quad, "lerp", "alpha")
    main_canvas.fill_color(edge_vertex_start_quad, edge_vertex_end_quad, "lerp", "alpha")
    main_canvas.fill_color(shell_vertex_start_quad, shell_vertex_end_quad, "lerp", "alpha")
    
    main_canvas.fill_color(sign_part1_edge_in, sign_part1_edge_out, "lerp", "alpha")
    main_canvas.fill_color(sign_part1_1_edge_out, "alpha")
    main_canvas.fill_color(sign_part1_2_edge_out, "alpha")
    main_canvas.fill_color(sign_part2_edge_out, "alpha")
    main_canvas.fill_color(sign_part3_edge_out, "alpha")
    main_canvas.fill_color(sign_part3_1_edge_out, "alpha")
    main_canvas.fill_color(sign_part4_edge_out, "alpha")
    main_canvas.fill_color(sign_part4_1_edge_out, "alpha")
    main_canvas.fill_color(sign_part4_2_edge_out, "alpha")
    main_canvas.rot = 90
    main_canvas.save(name+".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw_square(v,"bullet/card/card"+str(k))
