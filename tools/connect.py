from PIL import Image
import os
import re
from collections import defaultdict

# 当前脚本所在目录
folder = os.path.dirname(os.path.abspath(__file__))

# 匹配：任意前缀 + 数字 + .png
pattern = re.compile(r"^(.*?)(\d+)\.png$", re.IGNORECASE)

groups = defaultdict(list)

for filename in os.listdir(folder):
    match = pattern.match(filename)
    if not match:
        continue

    prefix = match.group(1)
    number = int(match.group(2))

    groups[prefix].append((number, filename))

if not groups:
    raise RuntimeError("当前目录没有找到类似 xxx1.png、xxx2.png 的图片")

for prefix, files in groups.items():

    # 至少两张才认为需要拼接
    if len(files) < 2:
        continue

    # 按数字排序，而不是字符串排序
    # 避免出现 1, 10, 11, 2...
    files.sort(key=lambda x: x[0])

    print(f"\n发现图片组：{prefix}")
    print("顺序：", [name for _, name in files])

    images = []

    for _, filename in files:
        path = os.path.join(folder, filename)

        with Image.open(path) as img:
            images.append(img.convert("RGBA"))

    # 输出宽度取最大宽度
    out_width = max(img.width for img in images)

    # 输出高度为所有图片高度之和
    out_height = sum(img.height for img in images)

    # 透明背景
    result = Image.new(
        "RGBA",
        (out_width, out_height),
        (0, 0, 0, 0)
    )

    y = 0

    for img in images:
        # 每张图片水平居中
        x = (out_width - img.width) // 2

        result.alpha_composite(img, (x, y))

        y += img.height

    output_name = f"{prefix}.png"
    output_path = os.path.join(folder, output_name)

    result.save(output_path)

    print(f"已生成：{output_name}")