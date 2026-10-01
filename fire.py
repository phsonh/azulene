from pathlib import Path

from PIL import Image

import azulene


colors = {
    1:  (255, 255, 0, 0),
    2:  (255, 128, 0, 0),
    3:  (255, 255, 255, 0),
    4:  (255, 128, 128, 0),
    5:  (255, 0, 255, 0),
    6:  (255, 0, 128, 0),
    7:  (255, 0, 255, 255),
    8:  (255, 0, 128, 128),
    9:  (255, 0, 0, 255),
    10: (255, 0, 0, 128),
    11: (255, 255, 0, 255),
    12: (255, 128, 0, 128),
    13: (255, 255, 255, 255),
    14: (255, 192, 192, 192),
    15: (255, 128, 128, 128),
    16: (255, 0, 0, 0),
}


# 白芯采用逻辑画布绘制，由Canvas内部高分辨率栅格化为64×96。
simulation_width = 64
simulation_height = 96
output_frame_width = simulation_height   # 旋转后每帧为96×64，火焰头朝右
output_frame_height = simulation_width
frame_count = 12      # 参考脚本的默认动画帧数
random_seed = 2947156886  # 固定随机种子；16色共用同一组火舌形态


flame = azulene.drawing.Flame(
    size=(simulation_width, simulation_height),  # 旋转前的64×96流场
    frames=frame_count,       # 一个循环包含的帧数，支持任意正整数
    seed=random_seed,         # 噪声种子；相同种子和参数会得到完全相同的动画
    variation=0.8,           # 帧间变化量：1为原变化量，0为静止
    thickness=8.5,           # 白芯周围的火焰厚度，范围1~20
    head_motion=0.5,         # 火焰前半部的轮廓变化幅度，范围0~3
    rear_fullness=1.5,       # 后半部饱满度，越大尾焰根部越宽，范围0.8~1.7
    turbulence=1.5,          # 总体涡流强度，越大轮廓和内部流动越明显，范围0~4
    tail_motion=1.2,         # 尾部摆动及轮廓变化强度，范围0~4
    tail_chaos=1.5,          # 尾部翻卷、分叉和局部明暗变化，范围0~3
    tail_flow=2.2,           # 火焰向后飘逸的程度，建议1.0~2.2，范围0.5~3
    side_tail_ratio=0.7,     # 两侧尾焰相对中央尾焰的长度比例，范围0.2~1
    shadow_strength=0.5,     # 不规则暗斑的对比强度，范围0~1
    tail_length=30.0,        # 尾焰长度；超出有效区域的部分会自然透明渐隐
    tail_width=8.0,          # 尾焰根部半宽，范围1~24
    tail_strength=0.5,       # 尾焰的热量与亮度，范围0~1
    tail_separation=0.15,    # 火舌之间的透明冷缝强度，0表示基本连成一片
    wind_strength=6.0,       # 从头部吹向尾部的风速，范围0~6
    front_compression=0.32,  # 前缘受风压缩的比例，范围0~0.5
    cooling=0.020,           # 每个模拟子步的冷却速度，越大消散越快，范围0~1
)


def make_white_core(radius):
    """生成实心白芯，并在原半径以外用1像素完成透明渐变。"""

    canvas = azulene.drawing.Canvas(32, 48)
    core = azulene.drawing.Circle(radius)
    # 逻辑半径增加0.5，经2倍导出后向外扩展1像素。
    fade = azulene.drawing.Circle(radius + 0.5)
    core.color = (255, 255, 255, 255)
    fade.color = (0, 255, 255, 255)

    # 64×96流场的热源位于第23.5行，即画布中心上方24像素。
    origin = azulene.drawing.point(0, 12)
    origin.color = (255, 255, 255, 255)
    canvas.put(core, 0, 12)
    canvas.put(fade, 0, 12)
    canvas.set_origin(origin)
    canvas.fill_color(origin, core, "lerp", "replace")
    canvas.fill_color(core, fade, "lerp", "replace")

    return canvas.render(2)


white_cores = {
    6: make_white_core(6),  # 当前奇数帧白芯半径
    7: make_white_core(6.25),  # 当前偶数帧白芯半径
}


def draw(color, name, number):
    frames = flame.render(color)
    sheet = Image.new(
        "RGBA",
        (output_frame_width * frame_count, output_frame_height),
        (0, 0, 0, 0),
    )
    for frame_index, frame in enumerate(frames, start=1):
        # 奇数帧半径6，偶数帧半径7；白芯始终最后覆盖。
        core_radius = 6 if frame_index % 2 == 1 else 7
        composed = frame.copy()
        composed.alpha_composite(white_cores[core_radius])
        # 原始流场的火焰头朝上；顺时针旋转90度后统一朝右。
        composed = composed.transpose(Image.Transpose.ROTATE_270)
        sheet.alpha_composite(
            composed,
            ((frame_index - 1) * output_frame_width, 0),
        )

    path = Path("bullet") / name / f"{name}{number}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    print(str(path) + "渲染完成")


for key, value in colors.items():
    draw(value, "fire", str(key))
