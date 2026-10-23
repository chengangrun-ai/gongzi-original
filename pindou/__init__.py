"""pindou-original：任意风格 → 原创拼豆图纸。

模块
- palette  色卡（MARD 291 色 / 72 色套装）与角色化配色
- geom     纯 numpy 几何（样条、偏移、锥形轮廓、对称轮廓……）
- canvas   矢量显示列表 → 拼豆索引网格 + 高清原画
- brushes  纹样笔刷与填充纹理（风格无关）
- motifs   参数化题材造型库
- comp     构图模板（徽章、几何框、拱框、满幅、花环……）
- stylepack 风格包：颜色、线宽、纹理、画幅配比、难度系数
- recipes  配方合成器：风格 × 题材 × 构图 × 种子 → 一款作品
- beadify  拼豆化：白边托底、整片连通、碎块桥接、统计与难度
- analyze  参考图 → 风格 DNA（只统计规律，不取像素）
- originality 原创性核查（NCC + dHash）
- chartkit 出图：色号图、原画、效果图、总览、目录、zip
"""
__version__ = '1.0.0'
