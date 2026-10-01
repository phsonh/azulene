from pathlib import Path

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
    edge_r_end = 15.48
    edge_r_start = 12
    white_x_start_pos = azulene.drawing.point(-16,0)
    white_x_end_pos = azulene.drawing.point(16,0)

    white_x_start_line = azulene.drawing.Polygon([[-16,16],[-16,-16]])
    white_x_end_line = azulene.drawing.Polygon([[16,16],[16,-16]])

    main_canvas = azulene.drawing.Canvas(64,64)
    edge_c_start = azulene.drawing.Circle(edge_r_start)
    edge_c_end = azulene.drawing.Circle(edge_r_end)

    white_x_start_line.color = [255,255,255,255]
    white_x_end_line.color,edge_c_start.color,edge_c_end.color = color,[0,[*color][1],[*color][2],[*color][3]],color

    origin = azulene.drawing.point(0, 0)
    origin.color = (255, 255, 255, 255)

    main_canvas.set_origin(white_x_start_pos)
    main_canvas.interpolation_mode = "w"
    main_canvas.fill_color(white_x_start_line, white_x_end_line, "1.25add", "alpha")
    main_canvas.cut(edge_c_end,"out")

    main_canvas.set_origin(origin)
    main_canvas.fill_color(edge_c_start, edge_c_end, "2add", "alpha")

    average_scale = 2
    edge_scale = 0.0001
    middle_scale = (3.0 * average_scale - edge_scale) / 2.0

    def stretch_scale(x):
        return edge_scale + (middle_scale - edge_scale) * (1.0 - x**2)

    stretched = azulene.drawing.Stretch(
        main_canvas,
        profile=stretch_scale,
        x_range=(-1, 1),
    )
    stretched.scale_y = 1 / 16
    output_canvas = azulene.drawing.Canvas(64,8)
    output_canvas.put(stretched, 0, 0)
    image = output_canvas.render(8)
    image = image.crop((0, 16, image.width, 48))
    destination = Path("bullet") / name / (name + number + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(
        destination,
    )
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"bent_laser",str(k))
