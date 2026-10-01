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

    body_main_left_pos = [[-3,5],[0,5],[0,-16],[-3,-16]]
    body_main_right_pos = [[3,5],[0,5],[0,-16],[3,-16]]
    crossguard_pos_up = [[7,6.5],[-7,6.5]]
    crossguard_pos_down = [[-7,5.5],[7,5.5]]

    def blade_scale(y):
        if y >= -10:
            return 1.0
        amount = min(1.0, max(0.0, (-10.0 - y) / 6.0))
        return 1.0 - amount**2

    body_main_left_base = azulene.drawing.Polygon(body_main_left_pos)
    body_main_right_base = azulene.drawing.Polygon(body_main_right_pos)
    blade_outer_left_base = azulene.drawing.Polygon(
        [[-3.8,5.7],[0,5.7],[0,-16.7],[-3.8,-16.7]]
    )
    blade_outer_right_base = azulene.drawing.Polygon(
        [[3.8,5.7],[0,5.7],[0,-16.7],[3.8,-16.7]]
    )
    crossguard_up = azulene.drawing.Polygon(crossguard_pos_up)
    crossguard_down = azulene.drawing.Polygon(crossguard_pos_down)

    # 手柄略窄于刀刃，圆帽半径始终等于手柄半宽。
    handle_half_width = 2
    handle_outer_half_width = 3.1
    handle_cap_y = 12.6
    handle_cap_radius = handle_half_width
    handle_outer_cap_radius = 3.0
    handle_bottom_y = 6.5
    handle_inner_pos = [
        [-handle_half_width,handle_bottom_y],
        [handle_half_width,handle_bottom_y],
        [handle_half_width,handle_cap_y],
    ]
    handle_inner_pos.extend([
        [handle_half_width * azulene.math.cos(angle),
         handle_cap_y + handle_cap_radius * azulene.math.sin(angle)]
        for angle in range(10,181,10)
    ])
    handle_outer_pos = [
        [-handle_outer_half_width,6.2],
        [handle_outer_half_width,6.2],
        [handle_outer_half_width,handle_cap_y],
    ]
    handle_outer_pos.extend([
        [handle_outer_half_width * azulene.math.cos(angle),
         handle_cap_y + handle_outer_cap_radius * azulene.math.sin(angle)]
        for angle in range(10,181,10)
    ])

    handle_inner = azulene.drawing.Polygon(handle_inner_pos)
    handle_outer = azulene.drawing.Polygon(handle_outer_pos)

    body_main_left = azulene.drawing.Pottery(
        body_main_left_base,
        profile=blade_scale,
        samples=256,
    )
    body_main_right = azulene.drawing.Pottery(
        body_main_right_base,
        profile=blade_scale,
        samples=256,
    )
    blade_outer_left = azulene.drawing.Pottery(
        blade_outer_left_base,
        profile=blade_scale,
        samples=256,
    )
    blade_outer_right = azulene.drawing.Pottery(
        blade_outer_right_base,
        profile=blade_scale,
        samples=256,
    )
    
    left_rgb = azulene.math.blend_color(
        color[1:],
        (255,255,255),
        0.5,
    )
    edge_rgb = azulene.math.blend_color(
        color[1:],
        (0,0,0),
        0.25,
    )
    handle_dark_rgb = azulene.math.blend_color(
        color[1:],
        (0,0,0),
        0.60,
    )
    handle_light_rgb = azulene.math.blend_color(
        color[1:],
        (0,0,0),
        0.15,
    )
    body_main_left.color = [color[0], *edge_rgb]
    crossguard_up.color = [color[0], *left_rgb]
    crossguard_down.color = [color[0], *edge_rgb]
    body_main_right.color = [255,255,255,255]
    blade_outer_left.color = [0, *edge_rgb]
    blade_outer_right.color = [0,255,255,255]
    handle_middle_rgb = azulene.math.blend_color(
        handle_dark_rgb,
        handle_light_rgb,
        0.5,
    )
    handle_inner.color = [color[0], *handle_middle_rgb]
    handle_outer.color = [0, *handle_middle_rgb]
    main_canvas = azulene.drawing.Canvas(32,32)

    # 刀刃轮廓先向外衰减，再在内部绘制原有的左右明暗。
    blade_edge_origin = azulene.drawing.point(0,-5)
    main_canvas.set_origin(blade_edge_origin)
    main_canvas.interpolation_mode = "r"
    main_canvas.fill_color(
        body_main_left,
        blade_outer_left,
        "1.5add",
        "alpha",
    )
    main_canvas.fill_color(
        body_main_right,
        blade_outer_right,
        "1.5add",
        "alpha",
    )

    # 从深色左刃，经浅色中轴，连续过渡到纯白右刃。
    blade_origin = azulene.drawing.point(0,0)
    blade_origin.color = [color[0], *left_rgb]
    main_canvas.set_origin(blade_origin)
    main_canvas.interpolation_mode = "w"
    main_canvas.fill_color(blade_origin,body_main_left,"1","alpha")
    main_canvas.fill_color(blade_origin,body_main_right,"1","alpha")

    # 护手下方将过渡范围扩大到4个逻辑单位。
    connection_top = azulene.drawing.Polygon([[-3,5.5],[3,5.5]])
    connection_bottom = azulene.drawing.Polygon([[-3,1.5],[3,1.5]])
    connection_top.color = [136, *edge_rgb]
    connection_bottom.color = [0, *edge_rgb]
    connection_origin = azulene.drawing.point(0,5.5)
    main_canvas.set_origin(connection_origin)
    main_canvas.interpolation_mode = "h"
    main_canvas.fill_color(connection_top,connection_bottom,"1","alpha")

    # 手柄软边与内部渐变都沿完整圆角轮廓连续计算。
    handle_edge_origin = azulene.drawing.point(0,11)
    main_canvas.set_origin(handle_edge_origin)
    main_canvas.interpolation_mode = "r"
    main_canvas.fill_color(handle_inner,handle_outer,"1.5add","alpha")
    # 完整轮廓先铺底，保证顶端不会因左右渐变薄片收束而漏像素。
    main_canvas.fill_color(handle_inner,"alpha")
    # 左上角最暗、右下角最亮。分成细横片后，每片内部继续横向插值，
    # 因而最终明暗轴线是连续的对角线，而不是两块生硬的色带。
    def handle_width(y):
        if y <= handle_cap_y:
            return handle_half_width
        ratio = (y - handle_cap_y) / handle_cap_radius
        return handle_half_width * max(0.0, 1.0 - ratio**2) ** 0.5

    handle_top_y = handle_cap_y + handle_cap_radius
    handle_slices = 48
    for index in range(handle_slices):
        y0 = handle_bottom_y + (
            handle_top_y - handle_bottom_y
        ) * index / handle_slices
        y1 = handle_bottom_y + (
            handle_top_y - handle_bottom_y
        ) * (index + 1) / handle_slices
        y_mid = (y0 + y1) * 0.5
        width0 = handle_width(y0)
        width1 = handle_width(y1)
        vertical = (y_mid - handle_bottom_y) / (
            handle_top_y - handle_bottom_y
        )
        left_edge = azulene.drawing.Polygon(
            [[-width0,y0],[-width1,y1]]
        )
        right_edge = azulene.drawing.Polygon(
            [[width0,y0],[width1,y1]]
        )
        left_edge.color = [color[0], *azulene.math.blend_color(
            handle_dark_rgb,
            handle_light_rgb,
            (1.0 - vertical) * 0.5,
        )]
        right_edge.color = [color[0], *azulene.math.blend_color(
            handle_dark_rgb,
            handle_light_rgb,
            1.0 - vertical * 0.5,
        )]
        strip_origin = azulene.drawing.point(-handle_width(y_mid),y_mid)
        main_canvas.set_origin(strip_origin)
        main_canvas.interpolation_mode = "w"
        main_canvas.fill_color(left_edge,right_edge,"1","alpha")

    # 护手的四条边分别按自身颜色向外渐隐，避免软边内侧出现色阶。
    guard_rgb = azulene.math.blend_color(left_rgb,edge_rgb,0.5)
    crossguard_top_outer = azulene.drawing.Polygon([[-7.7,7.2],[7.7,7.2]])
    crossguard_bottom_outer = azulene.drawing.Polygon([[-7.7,4.8],[7.7,4.8]])
    crossguard_left = azulene.drawing.Polygon([[-7,6.5],[-7,5.5]])
    crossguard_left_outer = azulene.drawing.Polygon([[-7.7,7.2],[-7.7,4.8]])
    crossguard_right = azulene.drawing.Polygon([[7,6.5],[7,5.5]])
    crossguard_right_outer = azulene.drawing.Polygon([[7.7,7.2],[7.7,4.8]])
    crossguard_top_outer.color = [0, *left_rgb]
    crossguard_bottom_outer.color = [0, *edge_rgb]
    crossguard_left.color = [color[0], *guard_rgb]
    crossguard_right.color = [color[0], *guard_rgb]
    crossguard_left_outer.color = [0, *guard_rgb]
    crossguard_right_outer.color = [0, *guard_rgb]
    main_canvas.set_origin(azulene.drawing.point(0,6))
    main_canvas.interpolation_mode = "w"
    main_canvas.fill_color(
        crossguard_left,
        crossguard_left_outer,
        "1.5add",
        "alpha",
    )
    main_canvas.fill_color(
        crossguard_right,
        crossguard_right_outer,
        "1.5add",
        "alpha",
    )
    main_canvas.interpolation_mode = "h"
    main_canvas.fill_color(
        crossguard_up,
        crossguard_top_outer,
        "1.5add",
        "alpha",
    )
    main_canvas.fill_color(
        crossguard_down,
        crossguard_bottom_outer,
        "1.5add",
        "alpha",
    )
    main_canvas.set_origin(azulene.drawing.point(0,6.5))
    main_canvas.interpolation_mode = "h"
    main_canvas.fill_color(crossguard_up,crossguard_down,"1add", "alpha")
    main_canvas.rot = 90
    main_canvas.save("bullet/" + name + "/" + name + str(number) + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"knife",k)
