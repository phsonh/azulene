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


# 尺寸由 32x32 参考图量取，在32x32逻辑画布上绘制，
# 最终按2倍导出为64x64；脚本不读取或内嵌参考图片。
tail_half_width = 4.5
tail_top_y = 15.0
tail_notch_y = 13.5
tail_bottom_y = 10.0
shaft_half_width = 1.5
shaft_top_y = 7.0
head_top_y = -6.0
head_taper_y = -9.0
head_tip_y = -14.0
outline_width = 0.625
rear_outline_width = 0.625
edge_blur_radius = 1.5

# 只有箭头头部之后的箭杆、尾羽衰减；箭头头部保持不透明。
tail_alpha = 32


def scaled_positions(positions):
    return list(positions)


arrow_positions = scaled_positions(
    [
        (-tail_half_width, tail_top_y),
        (0.0, tail_notch_y),
        (tail_half_width, tail_top_y),
        (tail_half_width, tail_bottom_y),
        (shaft_half_width, shaft_top_y),
        (shaft_half_width, head_top_y),
        (tail_half_width, head_top_y),
        (tail_half_width, head_taper_y),
        (0.0, head_tip_y),
        (-tail_half_width, head_taper_y),
        (-tail_half_width, head_top_y),
        (-shaft_half_width, head_top_y),
        (-shaft_half_width, shaft_top_y),
        (-tail_half_width, tail_bottom_y),
    ]
)

# 向内部缩进得到渐变区域；内外轮廓之间固定使用目标颜色。
# 箭杆两侧和 V 形箭尾使用稍宽的后部描边，使透明度衰减后仍清晰可见。
inner_tail_half_width = tail_half_width - rear_outline_width
inner_shaft_half_width = shaft_half_width - rear_outline_width
inner_head_half_width = tail_half_width - outline_width
inner_head_tip_y = (
    head_taper_y
    + outline_width
    - (head_taper_y - head_tip_y)
    * inner_head_half_width
    / tail_half_width
)
inner_arrow_positions = scaled_positions(
    [
        (-inner_tail_half_width, tail_top_y - rear_outline_width),
        (0.0, tail_notch_y - rear_outline_width),
        (inner_tail_half_width, tail_top_y - rear_outline_width),
        (inner_tail_half_width, tail_bottom_y),
        (inner_shaft_half_width, shaft_top_y),
        (inner_shaft_half_width, head_top_y),
        (inner_head_half_width, head_top_y - outline_width),
        (inner_head_half_width, head_taper_y + outline_width),
        (0.0, inner_head_tip_y),
        (-inner_head_half_width, head_taper_y + outline_width),
        (-inner_head_half_width, head_top_y - outline_width),
        (-inner_shaft_half_width, head_top_y),
        (-inner_shaft_half_width, shaft_top_y),
        (-inner_tail_half_width, tail_bottom_y),
    ]
)


def draw(color, name, number):
    main_canvas = azulene.drawing.Canvas(32, 32, "w")

    arrow = azulene.drawing.Polygon(arrow_positions)
    inner_arrow = azulene.drawing.Polygon(inner_arrow_positions)
    arrow.color = color
    inner_arrow.color = color

    center = azulene.drawing.point(0, 0)
    center.color = (255, 255, 255, 255)
    main_canvas.set_origin(center)

    # 内部横向从白色中心向目标颜色过渡；外圈固定为 color 描边。
    main_canvas.fill_color(center, inner_arrow, "2add", "alpha")
    main_canvas.fill_color(inner_arrow, arrow, "3add", "alpha")

    # 用整支箭的真实外边界计算连续色场，但只在头部和箭尾应用。
    # 连接处不是外边界，因此不会横跨中轴形成封口。
    head_region = azulene.drawing.Polygon(
        scaled_positions(
            [
                (-tail_half_width, head_top_y),
                (tail_half_width, head_top_y),
                (tail_half_width, head_taper_y),
                (0.0, head_tip_y),
                (-tail_half_width, head_taper_y),
            ]
        )
    )
    tail_region = azulene.drawing.Polygon(
        scaled_positions(
            [
                (-tail_half_width, tail_top_y),
                (0.0, tail_notch_y),
                (tail_half_width, tail_top_y),
                (tail_half_width, tail_bottom_y),
                (shaft_half_width, shaft_top_y),
                (-shaft_half_width, shaft_top_y),
                (-tail_half_width, tail_bottom_y),
            ]
        )
    )
    main_canvas.shade_edge(
        arrow,
        color,
        edge_blur_radius,
        "2add",
        head_region,
    )
    main_canvas.shade_edge(
        arrow,
        color,
        edge_blur_radius,
        "2add",
        tail_region,
    )

    # 用纯白 alpha 蒙版乘到箭杆和尾羽上。起点位于箭头肩部，
    # 所以 y <= head_top_y 的整个箭头头部不会参与透明度衰减。
    fade_start = azulene.drawing.Polygon(
        scaled_positions(
            [(-tail_half_width, head_top_y), (tail_half_width, head_top_y)]
        )
    )
    fade_end = azulene.drawing.Polygon(
        scaled_positions(
            [(-tail_half_width, shaft_top_y), (tail_half_width, shaft_top_y)]
        )
    )
    fade_start.color = (255, 255, 255, 255)
    fade_end.color = (tail_alpha, 255, 255, 255)

    fade_origin = azulene.drawing.point(0, head_top_y)
    main_canvas.set_origin(fade_origin)
    main_canvas.interpolation_mode = "h"
    main_canvas.fill_color(fade_start, fade_end, "3sub", "mul")

    # 尾羽已经超过衰减区间，保持最低透明度，不再继续变淡。
    tail_end = azulene.drawing.Polygon(
        scaled_positions(
            [(-tail_half_width, tail_top_y), (tail_half_width, tail_top_y)]
        )
    )
    tail_end.color = (tail_alpha, 255, 255, 255)
    tail_origin = azulene.drawing.point(0, shaft_top_y)
    main_canvas.set_origin(tail_origin)
    main_canvas.fill_color(fade_end, tail_end, "lerp", "mul")

    path = "bullet/" + name + "/" + name + str(number) + ".png"
    main_canvas.rot = 90
    main_canvas.save(path, 2)
    print(path + "渲染完成")


for key, value in colors.items():
    draw(value, "arrow", key)
