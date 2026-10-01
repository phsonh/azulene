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

def draw_star_big(color,name):
    r0 = 16*0.9#星星最大半径
    r00 = 10*0.9#星星最小半径
    star0_positions = []#星星的顶点坐标

    angle0,angle00 = 0,36#用于计算星星的极坐标角度
    i=1

    while i <= 5:
        star0_positions.append([r0*azulene.math.cos(angle0),r0*azulene.math.sin(angle0)])
        star0_positions.append([r00*azulene.math.cos(angle00),r00*azulene.math.sin(angle00)])
        i = i + 1
        angle0 += 72
        angle00 += 72

    star0 = azulene.drawing.Polygon(star0_positions)
    #新建一个多边形对象
    star0.color = (0,255,255,255)


    r1 = 16#星星最大半径
    r2 = 10#星星最小半径
    star_positions = []#星星的顶点坐标

    angle1,angle2 = 0,36#用于计算星星的极坐标角度
    i=1

    while i <= 5:
        star_positions.append([r1*azulene.math.cos(angle1),r1*azulene.math.sin(angle1)])
        star_positions.append([r2*azulene.math.cos(angle2),r2*azulene.math.sin(angle2)])
        #计算星星的顶点坐标存入star_positions
        i = i + 1
        angle1 += 72
        angle2 += 72

    star = azulene.drawing.Polygon(star_positions)
    #新建一个多边形对象
    star.color = (255,255,255,255)
    #设置多边形轮廓上的颜色值（顶点颜色）

    color_start_r = 6
    #color_max_r = 16
    color_max_r = 14
    #星星内部颜色设定，两个五边形过渡颜色。r=4内部纯白，r=4~12之间从白到蓝线性插值

    main_canvas = azulene.drawing.Canvas(32,32)
    #主画布，大小1024*1024，中心点为原点0，0
    angle3 = 0
    pentagon3_positions,pentagon4_positions = [],[]

    i = 1
    while i <= 5:
        pentagon3_positions.append([color_start_r*azulene.math.cos(angle3),color_start_r*azulene.math.sin(angle3)])
        pentagon4_positions.append([color_max_r*azulene.math.cos(angle3),color_max_r*azulene.math.sin(angle3)])
        i = i + 1
        angle3 += 72

    pentagon3 = azulene.drawing.Polygon(pentagon3_positions)
    pentagon4 = azulene.drawing.Polygon(pentagon4_positions)
    origin = azulene.drawing.point(0,0)
    pentagon3.color = (255,255,255,255)
    #pentagon4.color = (255,60,40,200)
    pentagon4.color = color
    origin.color = (255,255,255,255)
    #原点顶点颜色
    main_canvas.put(pentagon3,0,0)
    #把多边形摆到画布的0，0
    main_canvas.put(pentagon4,0,0)

    main_canvas.fill_color(origin,pentagon3,"lerp","alpha")
    #填充颜色
    main_canvas.fill_color(pentagon3,pentagon4,"1.5add","alpha")
    #填充颜色

    star_body = main_canvas.cut(star,"out") #切掉星星边界以外的部分，这个函数返回一个多边形对象
    main_canvas.put(star0,0,0)
    main_canvas.fill_color(star0,star_body,"lerp","alpha")
    main_canvas.save(name+".png",2)
    #保存到文件，倍率1


for k,v in colors.items():
    draw_star_big(v,"bullet/star_big/star_big"+str(k))
