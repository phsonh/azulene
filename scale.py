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
    LOWER_WHITE_OFFSET = 0.75   # 下方白色覆盖层的下移量，最终图片约为 3 像素

    # 最外层 color 外壳参数
    OUTER_COLOR_SCALE_X = 1          # 横向尺寸基准
    OUTER_COLOR_SCALE_Y = 1          # 纵向尺寸；与 OFFSET_Y 一起控制上下端位置
    OUTER_COLOR_OFFSET_Y = 0.0         # 整层上下偏移；正数上移，负数下移
    OUTER_COLOR_HALF_WIDTH = 8.0       # 轮廓函数的两端位置：y=±8
    OUTER_COLOR_PEAK_HEIGHT = 4      # y=0 处的最大横向倍率，实际使用值会除以 4
    OUTER_COLOR_POWER = 3.5            # 中段到两端的变化速度；越小越早开始收窄
    OUTER_COLOR_SIDE_TIGHTNESS = 4.0   # 两侧收紧程度；越大越窄、越陡
    OUTER_COLOR_TIP_ROUNDNESS = 0.0    # 端部饱满程度；0 表示不额外加圆
    OUTER_COLOR_TIP_FOCUS = 0.0        # 端部加圆效果向尖端集中的程度
    OUTER_COLOR_END_VALUE = 0.1        # y=±HALF_WIDTH 时保留的最小横向倍率

    # 中间 white 边界参数
    INNER_WHITE_SCALE_X = 0.9          # 横向尺寸；越小，左右环带越厚
    INNER_WHITE_SCALE_Y = 0.9          # 纵向尺寸；越小，上下环带越厚
    INNER_WHITE_OFFSET_Y = -0.75         # 整层上下偏移；正数上移，负数下移
    INNER_WHITE_HALF_WIDTH = 8.0       # 收口曲率范围；不要用它控制上下尺寸
    INNER_WHITE_PEAK_HEIGHT = 4.3      # y=0 处的最大横向倍率，实际使用值会除以 4
    INNER_WHITE_POWER = 3.5            # 中段到两端的变化速度；越小越早开始收窄
    INNER_WHITE_SIDE_TIGHTNESS = 4.0   # 两侧收紧程度；越大越窄、越陡
    INNER_WHITE_TIP_ROUNDNESS = 0.0    # 端部饱满程度；0 表示不额外加圆
    INNER_WHITE_TIP_FOCUS = 0.0        # 端部加圆效果向尖端集中的程度
    INNER_WHITE_END_VALUE = 0.05        # y=±HALF_WIDTH 时保留的最小横向倍率

    # 最内层 color 边界参数
    INNER_COLOR_SCALE_X = 0.75         # 横向尺寸；越小，内侧环带越厚
    INNER_COLOR_SCALE_Y = 0.75         # 纵向尺寸；越小，内侧环带越厚
    INNER_COLOR_OFFSET_Y = -0.75         # 整层上下偏移；正数上移，负数下移
    INNER_COLOR_FADE_INSET = 0.75      # 向内经过多少逻辑单位后，alpha 降为 0
    INNER_COLOR_HALF_WIDTH = 8.0       # 轮廓函数的两端位置：y=±8
    INNER_COLOR_PEAK_HEIGHT = 4.3      # y=0 处的最大横向倍率，实际使用值会除以 4
    INNER_COLOR_POWER = 3.5            # 中段到两端的变化速度；越小越早开始收窄
    INNER_COLOR_SIDE_TIGHTNESS = 4.0   # 两侧收紧程度；越大越窄、越陡
    INNER_COLOR_TIP_ROUNDNESS = 0.0    # 端部饱满程度；0 表示不额外加圆
    INNER_COLOR_TIP_FOCUS = 0.0        # 端部加圆效果向尖端集中的程度
    INNER_COLOR_END_VALUE = 0.1        # y=±HALF_WIDTH 时保留的最小横向倍率

    # 从 rice.py 复制的完整 rice 形状参数
    RICE_CENTER_X = 0.0                 # rice 中心横坐标
    RICE_CENTER_Y = -3.0                # rice 中心纵坐标
    RICE_COLOR_TOP_Y = 2.0              # 外层 color 的实际最上端
    RICE_COLOR_BOTTOM_Y = -8.0          # 外层 color 的实际最下端
    RICE_WHITE_INSET_SCALE = 0.3        # 白色边界等比内缩，让 color 更向内延伸

    RICE_WHITE_HALF_WIDTH = 7.0
    RICE_WHITE_PEAK_HEIGHT = 5.5
    RICE_WHITE_POWER = 3.5
    RICE_WHITE_SIDE_TIGHTNESS = 6.0
    RICE_WHITE_TIP_ROUNDNESS = 0.0
    RICE_WHITE_TIP_FOCUS = 0.0
    RICE_WHITE_END_VALUE = 0.1

    RICE_COLOR_HALF_WIDTH = 8.0
    RICE_COLOR_PEAK_HEIGHT = 4.3
    RICE_COLOR_POWER = 3.5
    RICE_COLOR_SIDE_TIGHTNESS = 4.0
    RICE_COLOR_TIP_ROUNDNESS = 0.0
    RICE_COLOR_TIP_FOCUS = 0.0
    RICE_COLOR_END_VALUE = 0.1

    def pottery_scale(
        y,
        half_width,
        peak_height,
        power,
        side_tightness,
        tip_roundness,
        tip_focus,
        end_value,
    ):
        t = (abs(y) / half_width) ** power
        tip = 1.0 + tip_roundness * t ** tip_focus
        shape = math.sqrt(
            max(0.0, 1.0 - t) * tip / (1.0 + side_tightness * t)
        )
        return end_value + (peak_height / 4.0 - end_value) * shape

    def outer_color_scale(y):
        return pottery_scale(
            y,
            OUTER_COLOR_HALF_WIDTH,
            OUTER_COLOR_PEAK_HEIGHT,
            OUTER_COLOR_POWER,
            OUTER_COLOR_SIDE_TIGHTNESS,
            OUTER_COLOR_TIP_ROUNDNESS,
            OUTER_COLOR_TIP_FOCUS,
            OUTER_COLOR_END_VALUE,
        )

    def inner_white_scale(y):
        return pottery_scale(
            y,
            INNER_WHITE_HALF_WIDTH,
            INNER_WHITE_PEAK_HEIGHT,
            INNER_WHITE_POWER,
            INNER_WHITE_SIDE_TIGHTNESS,
            INNER_WHITE_TIP_ROUNDNESS,
            INNER_WHITE_TIP_FOCUS,
            INNER_WHITE_END_VALUE,
        )

    def inner_color_scale(y):
        return pottery_scale(
            y,
            INNER_COLOR_HALF_WIDTH,
            INNER_COLOR_PEAK_HEIGHT,
            INNER_COLOR_POWER,
            INNER_COLOR_SIDE_TIGHTNESS,
            INNER_COLOR_TIP_ROUNDNESS,
            INNER_COLOR_TIP_FOCUS,
            INNER_COLOR_END_VALUE,
        )

    def rice_white_scale(y):
        return pottery_scale(
            y,
            RICE_WHITE_HALF_WIDTH,
            RICE_WHITE_PEAK_HEIGHT,
            RICE_WHITE_POWER,
            RICE_WHITE_SIDE_TIGHTNESS,
            RICE_WHITE_TIP_ROUNDNESS,
            RICE_WHITE_TIP_FOCUS,
            RICE_WHITE_END_VALUE,
        )

    def rice_color_scale(y):
        return pottery_scale(
            y,
            RICE_COLOR_HALF_WIDTH,
            RICE_COLOR_PEAK_HEIGHT,
            RICE_COLOR_POWER,
            RICE_COLOR_SIDE_TIGHTNESS,
            RICE_COLOR_TIP_ROUNDNESS,
            RICE_COLOR_TIP_FOCUS,
            RICE_COLOR_END_VALUE,
        )

    color_poses = [[3.5,7],[-3.5,7],[-3.5,-7],[3.5,-7]]
    source_canvas = azulene.drawing.Canvas(16,16)
    color_base = azulene.drawing.Polygon(color_poses)

    white_c = azulene.drawing.Pottery(
        color_base,
        profile=inner_white_scale,
        y_range=(-8, 8),
        samples=128,
    )
    white_c.scale_x = INNER_WHITE_SCALE_X
    white_c.scale_y = INNER_WHITE_SCALE_Y
    color_c = azulene.drawing.Pottery(
        color_base,
        profile=outer_color_scale,
        y_range=(-8, 8),
        samples=128,
    )
    lower_white_c = azulene.drawing.Pottery(
        color_base,
        profile=outer_color_scale,
        y_range=(-8, 8),
        samples=128,
    )
    inner_color_c = azulene.drawing.Pottery(
        color_base,
        profile=inner_color_scale,
        y_range=(-8, 8),
        samples=128,
    )
    inner_transparent_c = azulene.drawing.Pottery(
        color_base,
        profile=inner_color_scale,
        y_range=(-8, 8),
        samples=128,
    )
    color_c.scale_x = OUTER_COLOR_SCALE_X
    color_c.scale_y = OUTER_COLOR_SCALE_Y
    lower_white_c.scale_x = OUTER_COLOR_SCALE_X
    lower_white_c.scale_y = OUTER_COLOR_SCALE_Y
    inner_color_c.scale_x = INNER_COLOR_SCALE_X
    inner_color_c.scale_y = INNER_COLOR_SCALE_Y
    inner_center_half_width = 3.5 * inner_color_scale(0)
    inner_transparent_scale_x = (
        INNER_COLOR_SCALE_X
        - INNER_COLOR_FADE_INSET / inner_center_half_width
    )
    inner_transparent_scale_y = (
        INNER_COLOR_SCALE_Y
        - INNER_COLOR_FADE_INSET / 7.0
    )
    if inner_transparent_scale_x <= 0 or inner_transparent_scale_y <= 0:
        raise ValueError(
            "INNER_COLOR_FADE_INSET is too large for the inner color boundary"
        )
    inner_transparent_c.scale_x = inner_transparent_scale_x
    inner_transparent_c.scale_y = inner_transparent_scale_y

    color_c.color = color
    white_c.color = (255, 255, 255, 255)
    lower_white_c.color = (255, 255, 255, 255)
    inner_color_c.color = color
    inner_transparent_c.color = (0, *color[1:])

    # 缩放负责厚度，OFFSET_Y 只负责上下移动；二者都不会改变收口曲率。
    source_canvas.put(color_c,0,OUTER_COLOR_OFFSET_Y)
    source_canvas.put(white_c,0,INNER_WHITE_OFFSET_Y)
    source_canvas.put(inner_color_c,0,INNER_COLOR_OFFSET_Y)
    source_canvas.put(inner_transparent_c,0,INNER_COLOR_OFFSET_Y)

    # 只绘制白色内边界到 color 外壳之间的环带；白色边界以内保持透明。
    source_canvas.fill_color(white_c, color_c, "0.6add", "alpha")

    # 同形白层向下错开，覆盖环带下方的 color；之后重新按原外壳
    # 裁边并挖空中心，因此不会扩大轮廓，也不会重新填上白芯。
    source_canvas.put(
        lower_white_c,
        0,
        OUTER_COLOR_OFFSET_Y - LOWER_WHITE_OFFSET,
    )
    source_canvas.fill_color(lower_white_c,"alpha")
    source_canvas.cut(color_c,"out")
    source_canvas.cut(white_c,"in")

    # 最内层只提供 color 边界，并由此向外过渡到 white 边界；
    # 向内则在指定距离内把 alpha 线性降到 0，透明边界以内不填充。
    source_canvas.fill_color(inner_color_c,white_c,"2add","alpha")
    source_canvas.fill_color(
        inner_transparent_c,
        inner_color_c,
        "1",
        "alpha",
    )

    # 先在原始坐标系中严格保留 y >= 0 的上半部分。
    upper_half_clip = azulene.drawing.Polygon(
        [[-8,8],[8,8],[8,0],[-8,0]]
    )
    source_canvas.cut(upper_half_clip,"out")

    # 裁好的上半部分整体放大两倍，再整体向上平移 0.5 个逻辑单位。
    upper_half = azulene.drawing.Pottery(source_canvas)
    upper_half.scale_x = 2
    upper_half.scale_y = 2

    # rice 的外层有色几何原本位于 y=±7；画布 y=±8 处是透明留白。
    # 因此依据有色边界计算等比倍率，使上下有色端精确落在 2 和 -8。
    rice_uniform_scale = (
        RICE_COLOR_TOP_Y - RICE_COLOR_BOTTOM_Y
    ) / 14.0
    rice_white_base = azulene.drawing.Polygon(
        [[1.5,2],[-1.5,2],[-1.5,-2],[1.5,-2]]
    )
    rice_color_base = azulene.drawing.Polygon(
        [[3.5,7],[-3.5,7],[-3.5,-7],[3.5,-7]]
    )
    rice_white_c = azulene.drawing.Pottery(
        rice_white_base,
        profile=rice_white_scale,
        y_range=(-6, 6),
        samples=128,
    )
    rice_color_c = azulene.drawing.Pottery(
        rice_color_base,
        profile=rice_color_scale,
        y_range=(-8, 8),
        samples=128,
    )
    rice_white_c.scale_x = rice_uniform_scale * RICE_WHITE_INSET_SCALE
    rice_white_c.scale_y = rice_uniform_scale * RICE_WHITE_INSET_SCALE
    rice_color_c.scale_x = rice_uniform_scale
    rice_color_c.scale_y = rice_uniform_scale
    rice_white_c.color = (255, 255, 255, 255)
    rice_color_c.color = color
    rice_origin = azulene.drawing.point(RICE_CENTER_X, RICE_CENTER_Y)
    rice_origin.color = (255, 255, 255, 255)

    main_canvas = azulene.drawing.Canvas(16,16)
    # 先画 rice，再叠加带透明内沿的半环。
    main_canvas.put(rice_white_c,RICE_CENTER_X,RICE_CENTER_Y)
    main_canvas.put(rice_color_c,RICE_CENTER_X,RICE_CENTER_Y)
    main_canvas.set_origin(rice_origin)
    main_canvas.fill_color(rice_origin,rice_white_c,"lerp","alpha")
    main_canvas.fill_color(rice_white_c,rice_color_c,"2add","alpha")
    main_canvas.put(upper_half,0,-7.0)
    main_canvas.rot = -90
    main_canvas.save("bullet/" + name + "/" + name + number + ".png",2)
    #保存到文件，倍率1
for k,v in colors.items():
    draw(v,"scale",str(k))
