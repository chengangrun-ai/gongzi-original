---
name: 公子图纸原创
description: 任意风格的参考图 → 一整套「原创」拼豆图纸（色号图/原画/效果图/总览/目录/原创性报告/zip）。用户发来图片说"照这个风格做一套""这个风格能做成拼豆吗""给我原创一批图纸""不要描图、要原创"，或提到拼豆、豆子、图纸、色号、原创系列、风格包时使用。支持纹身/水墨/和风/萌系/波普/像素/霓虹/彩窗/植物/低多边/日系赛璐璐等风格，也支持风景照片与人物头像（做原创角色，不复刻具体角色）。区别于"照图转图纸"：本技能只从参考图里学风格规律（配色/线宽/纹理/构图），画面全部由代码从零绘制，附带原创性核查。
agent_created: true
---

# 公子图纸原创 · Gongzi Original

> v3使用约定：100项改进见 `docs/optimization_100.md`，验证与人工验收见 `docs/verification.md`。已有系列目录会拒绝覆盖，重做请用新目录；参考图不得放入交付目录。`check` 后以最新报告、manifest和交付包为准。无参考图必须说明未做参考图核查；单款无法做款间比较，不能说“款间通过”。`pass_` 只是本次可执行数值检查的结果，不是作品权利状态的保证。自动检查不代替人工查看总览和手工试拼。

**从参考图提炼风格参数，用程序绘制新拼豆图纸，并保留生成记录。**

参考图只用来"量风格"（配色比例、线宽、纹理密度、构图比例），**画面全部由代码从零画出来**：
样条曲线、几何形、程序化纹样。可用风格参数生成新画面；题材和视觉效果仍受造型库、拼豆尺寸限制，数值核查后仍需人工复核。

## 先说清楚边界：风格 ≠ 题材

这套系统由两部分组成，能力上限不一样，**别混为一谈**：

| | 能力 | 说明 |
|---|---|---|
| **风格** | ✅ 真的任意 | 配色、线宽、纹理、明暗、构图比例全部由参考图统计得出，风格包是纯数据，换风格只改 JSON。黑白稿、水彩、照片、霓虹、像素、彩窗……都能量、都能出 |
| **题材** | ⚠️ 有词汇表 | 画面由 85 个参数化造型拼出来。库里有的（动物/植物/天体/器物/符号/风景/人物）没问题；库里没有的（某款车、某栋楼、某个具体角色）要么用近似造型，要么新写一个造型 |

所以老实说：
- **"风格任意"** = 是。任何图扔进来都能提炼出风格并出图纸。
- **"题材任意"** = 不是。85 个造型之外的题材需要扩展造型库（每个约 20 行代码）。

具体到三类常见素材：

| 素材 | 能不能做 | 怎么做 |
|---|---|---|
| **风景照片**（海、山、森林、城市天际线） | ✅ 能 | `scene` 构图分层（天空→远山→主体→地面/水面）+ `hill/forest/lake/house/boat/lighthouse` 等造型。照片会自动判成"满底铺色 + 渐变纹理" |
| **人物照片** | ⚠️ 能做"头像" | `bust`（半身像）/`chibi`（Q版小人）能出**原创**头像，但**不是还原这个人**。要还原真人相貌（肖像）不属于本技能，也涉及肖像权 |
| **漫画/动漫角色** | ⚠️ 只能做原创角色 | 用同风格的配色和线条画**全新角色**（`chibi`/`bust` + 该风格的风格包）。**不复刻任何已有角色**——那是 IP，红线第一条 |

## 何时使用

- 用户扔来一批图：「照这个风格给我做一套拼豆」「这种画风能做吗」
- 用户要「原创」而不是「转图」：「不要描图」「要能卖、能举证」
- 用户已有系列要扩充：「再加 20 款」「换个题材」
- 用户提到：拼豆、豆子、图纸、色号、原创系列、风格包、MARD、漫漫

> 如果用户只是想把**某一张图**原样转成图纸（要还原那只猫、那张照片），用 `pindou-gongzi`（照图转图），不是本技能。

## 三步走

### 第 1 步：看参考图，写风格简报（30 秒）

**你必须自己打开参考图看**（Read 工具能看图），然后写下这份简报。
这一步机器替代不了：代码只会量数字，不会判断"这是水彩还是赛璐璐"。

```json
{
  "风格名": "复古日系少女漫",
  "一句话描述": "奶油底、粉紫主色、细线、网点阴影、圆形徽章构图",
  "主色": ["#FFE2CE 奶油底", "#FFB7E7 粉", "#B6B1BA 灰"],
  "线": {"颜色": "#753832 深棕", "粗细": "细（1–1.5 格）"},
  "纹理感": "网点 / 平涂",
  "背景": "满底铺色（不留白边）",
  "构图": "圆形徽章为主，少量竖幅",
  "题材": ["猫脸", "星星", "爱心", "小幽灵", "彩虹"],
  "点缀色": "#FEFF8B 一点点黄",
  "是照片吗": false
}
```

### 第 2 步：量化参考图，定风格包

```bash

# 只统计规律，不取像素；输出饱和度/对比/边缘密度/线宽/糊格率/推荐纹理与配色
python scripts/pindou.py analyze <参考图目录> --out out/风格分析.json
```

看 `推荐纹理`、`画幅配比`、`配色角色`、`photo_like` 四个字段，然后二选一：

- **有现成风格包能对上** → 直接用它（`python scripts/pindou.py styles` 看 14 个内置风格）
- **对不上** → 自动合成一个（推荐，一步到位）：
  ```bash
  python scripts/pindou.py auto <参考图目录> --n 12 --out out/新系列 \
      --name "复古日系少女漫" --subjects cat_face,star,heart,ghost,rainbow
  ```
  或者把第 1 步的简报手写成风格包：复制 `styles/kawaii_pastel.json` 改配色和参数，
  字段说明见 `references/风格包规范.md`。改 JSON 就行，**不用改代码**。

> `--subjects` 必须由你根据简报填：把用户图里的题材映射到造型库（见下方对照表）。
> 全量清单：`python scripts/pindou.py motifs`。

### 第 3 步：出全套 + 自查 + 交付

```bash
python scripts/pindou.py build --style <风格id或json路径> --n 24 --out out/系列名 \
    --series "系列名" --prefix XX --seed 1 --subjects cat,star,heart --refs <参考图目录>
```

产出（每款 3 张图 + 1 个源文件）：

```
out/系列名/
├── 色号图/XX001_猫_色号图.png    照着拼（每格写色号，10 格红线、5 格虚线、行列坐标）
├── 原画/XX001_猫_原画.png        展示/封面（矢量抗锯齿）
├── 效果图/XX001_猫_效果图.png    熨完的样子（带高光/豆孔/投影）
├── 网格/XX001.txt               作品原件（3 行文件头 + 每行一排豆），必须留档
├── 总览_1.png                   25 款一张，人工过一遍
├── 目录.csv / catalog.json      台账（Excel 直接打开）
├── 原创性报告.md/.json          和参考图、款与款的相似度
├── 说明.txt
└── 系列名_全套.zip
```

**交付前必须打开总览图看一遍**（用 Read 看图），按这五条挑刺，不合格就改参数重跑：

| 症状 | 怎么改 |
|---|---|
| 糊成一片 / 中间灰多 | 换更粗的纹理（`fill_texture`: halftone→dots→scales→solid），或加大 `line_width` |
| 断线 / 细节消失 | `line_width` 调到 1.4–1.8；去掉过密纹理 |
| 飘着的小碎点 | 这是会被删的：把 `splatter` 调小或去掉 |
| 画面太空 | 换构图（`--templates`），或提高 `fill_ratio` |
| 几款长得像 | 换 `--seed`，或让 `--subjects` 更分散、`--templates` 更杂 |

## 三类素材的具体打法

### A. 风景 / 照片

```bash
python scripts/pindou.py auto <风景图目录> --n 12 --out out/风景 \
    --name "海边小镇" --subjects tree,boat,lighthouse,house,forest,mountain \
    --templates scene,horizon
```

- 照片会自动判成 `photo_like`：满底铺色 + 渐变纹理（照片边缘柔和，用点刺会脏）
- **一定要用 `scene` 构图**：它分四层（天空 → 远山两层 → 主体 → 地面/水面 + 前景剪影），
  这才是风景的样子；用 `badge`/`medallion` 会变成"图标"而不是"景"
- 配色是**按色相挑**的（不是一路灰）：天空、远山、水面各取一个真正不同的颜色

### B. 人物照片 / 头像

```bash
python scripts/pindou.py auto <人像图目录> --n 8 --out out/头像 \
    --name "人像系列" --subjects bust,chibi --templates badge,frame,card,corner
```

- `bust` = 半身像（肩+颈+头+发），`chibi` = Q版全身，发型由种子随机变化
- **只做原创形象**：不要照着照片还原五官比例、发型细节、服装图案。用户要"像本人"的，
  明确说这是原创形象、不是肖像还原
- 真要做"某个人"，属于肖像，先确认授权

### C. 漫画 / 动漫角色

```bash
python scripts/pindou.py build --style anime_cel --n 10 --out out/角色 \
    --subjects chibi,bust,cat_face --templates badge,frame,card,corner,banner
```

- 用该作品的**画风**（配色、线条粗细、上色方式），画**全新的角色**
- **绝不复刻已有角色**：发型+瞳色+服装+标志物凑在一起就是 IP 了。参考图里有角色时，
  只统计风格，题材换成中性角色
- 用户坚持要"画那个角色"，直接说明这是 IP 红线，改用「原创角色 + 同风格」

## 常用命令

```bash
python scripts/pindou.py styles                 # 15 个风格包
python scripts/pindou.py motifs                 # 85 个造型 / 18 个构图 / 15 种纹理
python scripts/pindou.py analyze <图目录>        # 风格量化
python scripts/pindou.py auto <图目录> --n 12 --out out/x --subjects ...   # 一步到位
python scripts/pindou.py build --style kawaii_pastel --n 24 --out out/x    # 用现成风格
python scripts/pindou.py build --style out/x/风格分析.json ...              # 也能直接吃 analyze 的结果
python scripts/pindou.py check out/x --refs <图目录>                       # 重跑原创性核查
python scripts/pindou.py audit --style ink_tattoo --out audit.png          # 造型对照表
python scripts/pindou.py selftest               # 自检（装完先跑这个）
```

`build` 常用参数：`--n` 数量、`--subjects` 题材、`--templates` 构图、`--seed` 种子（换一批就换它）、
`--prefix` 编号前缀、`--series` 系列名、`--refs` 参考图目录（只用于原创性核查）、`--cs` 色号图每格像素。

## 题材 → 造型对照表（最常用）

| 用户图里是 | 用哪个造型 |
|---|---|
| 猫 / 猫脸 / 狐狸 / 狼 / 熊 / 兔 / 鹿 / 龙 / 恐龙 | `cat` `cat_face` `fox` `wolf` `bear` `rabbit` `deer` `dragon` `dino` |
| 鸟 / 猫头鹰 / 蝴蝶 / 飞蛾 / 蜜蜂 / 蛇 | `bird` `owl` `butterfly` `moth` `bee` `snake` |
| 鱼 / 锦鲤 / 鲸 / 章鱼 / 水母 / 海龟 / 蟹 | `fish` `koi` `whale` `octopus` `jellyfish` `turtle` `crab` |
| 花 / 玫瑰 / 莲花 / 蘑菇 / 叶 / 蕨 / 仙人掌 / 树 / 花环 | `flower` `rose` `lotus` `mushroom` `leaf` `fern` `cactus` `tree` `wreath` |
| 月亮 / 太阳 / 星球 / 星星 / 彗星 / 星座 / 日蚀 | `moon` `sun` `planet` `star` `comet` `constellation` `eclipse` |
| 眼睛 / 心 / 骷髅 / 罗盘 / 曼陀罗 / 山 / 浪 / 阴阳 / 螺旋 / 三角结 | `eye` `heart` `skull` `compass` `mandala` `mountain` `wave_icon` `yinyang` `spiral` `triquetra` |
| 蜡烛 / 钥匙 / 瓶子 / 沙漏 / 灯笼 / 船锚 / 匕首 / 书 / 咖啡 / 相机 / 磁带 / 时钟 / 药瓶 | `candle` `key` `bottle` `hourglass` `lantern` `anchor` `dagger` `book` `coffee` `camera` `cassette` `clock` `potion` |
| 幽灵 / 云 / 彩虹 / 星星仔 / 熊脸 / 兔脸 | `ghost` `cloud` `rainbow` `star_buddy` `bear_face` `bunny_face` |
| **风景：丘陵 / 树林 / 水面 / 小屋 / 小船 / 灯塔 / 拱桥 / 栅栏 / 小路 / 鸟居** | `hill` `forest` `lake` `house` `boat` `lighthouse` `bridge` `fence` `path` `gate` |
| **和风/国风：竹 / 樱 / 双鲤 / 月相** | `bamboo` `sakura` `koi_pair` `moon_phase` |
| **萌宠：狗 / 熊猫** | `dog` `panda` |
| **人物：半身头像 / Q版小人** | `bust` `chibi` |

**没有对应造型怎么办**：先看能不能用近似造型 + 换纹理/构图糊过去（大多数情况够用）；
真要新造型，就照着 `pindou/motifs.py` 里任意一个函数写一个新的（20 行左右，参数化样条），
加 `@motif('名字','类别','中文名')` 装饰器就自动进库。写完跑 `audit` 看一眼。

## 出图质量闭环（v4 新增）

一款成品会按"能不能卖"打分，不达标就自动重画：

| 指标 | 判定 | 处理 |
|---|---|---|
| 主体面积占比 | < 0.22 判废 | 第 3 遍改满幅构图重画 |
| 色阶数 | < 3 色封顶 0.55 | 第 4 遍加内轮廓补一档 |
| 孤立单颗占比 | > 30% 封顶 0.50 | 第 2 遍强制平涂、关墨溅 |
| 难度星级 | 偏离 3–4 星扣分 | 只影响排序，不重画 |

最多画 4 遍取最高分；**只有"换纹理能修"的缺陷才重画**，所以不会白跑（168 款全量 6 秒）。
质量分写进 `catalog.json`，复盘时能直接筛"哪款偏弱"。

## 15 个内置风格

| id | 风格 | 适合 |
|---|---|---|
| `ink_tattoo` | 墨纹（黑白灰+一点红） | 纹身稿、图腾、走兽、暗黑 |
| `kawaii_pastel` | 马卡龙萌系 | 萌物、食物、小动物 |
| `pop_art` | 波普（正红黄蓝+网点） | 强对比、复古印刷 |
| `pixel_retro` | 像素复古 | 8-bit、游戏、深底 |
| `mandala_gold` | 曼陀罗金 | 对称、繁复、装饰 |
| `ukiyoe` | 和风 | 青海波、锦鲤、浪、山 |
| `lowpoly` | 低多边 | 几何折面、冷色 |
| `neon_cyber` | 赛博霓虹 | 黑底霓虹、未来感 |
| `botanical` | 植物线描 | 叶、花、蕨、清新 |
| `stained_glass` | 彩窗 | 铅条分区、饱和玻璃色 |
| `chinese_ink` | 国风水墨 | 宣纸、留白、朱砂 |
| `nordic_tribal` | 北欧部落 | 编结、黑白红、对称 |
| `sunset_warm` | 落日渐变 | 暖色渐变、复古海报 |
| `anime_cel` | 日系赛璐璐 | 原创角色、头像 |
| `deepsea_glow` | 深海幻光 | 深蓝底、橙金发光、摄影感 |

## 原创红线（比技术步骤优先）

1. **参考图只统计风格，不进交付物**：不描图、不取样像素、不做图生图、不拼贴。
   代码里没有任何"读参考图"的路径，只有 `analyze.py` 读图算数字。
2. **画面全部由代码从零画**：样条、几何、程序化纹样；控制点都是手写坐标。
3. **不碰 IP**：动漫/影视/游戏角色、商标、名人肖像、他人水印一律不用；
   参考图里有 IP 时，只统计风格，不做同题材。**"同风格原创角色"可以，"复刻那个角色"不行。**
4. **肖像要授权**：做真人头像只能做原创形象，不能还原相貌特征。
5. **传统公共母题可以用**（骷髅、罗盘、莲花、青海波、曼陀罗……），但别照搬某位作者的具体排布。
6. **每套都过原创性核查**：和参考图 NCC < 0.75、dHash ≥ 10（NCC 偏高时才参与判定），
   款与款 NCC < 0.92。**超了就重画，不许调阈值。**
7. **留证**：固定种子（可逐格复现）、网格源文件、PNG 内嵌作者/版权/时间、原创性报告、git 提交。

## 工艺底线（写进代码里的硬约束）

- 线宽 ≥ 1.2 格；细于 1.35 格的线自动按"像素完美单颗线"落格，不会断
- 重复纹样周期 ≥ 3 格，青海波圈距 ≥ 2 格，否则糊
- 灰阶最多 2–3 阶 + 4×4 抖动，不做写实渐变
- 整件必须四邻连通成一整片（熨完不掉零件）：碎块 < 30 格删掉，离主体 ≤ 5 格的桥接回来
- 外轮廓 1 格白豆托底（贴纸感）；主体要撑满画面
- 色号只在 MARD 72 色套装（默认）或 291 色全卡里选，都能买到

## 环境

```bash
pip install -r requirements.txt      # numpy pillow scipy
python scripts/pindou.py selftest    # 装完先自检，通过再接真图
```

只用 numpy + Pillow + scipy，**不需要 cairo / OpenCV**，Windows 直接能跑。
字体走 `PINDOU_FONT_DIR` 或系统字体（微软雅黑/黑体/Arial）。

## 目录

```
pindou-original/
├── SKILL.md
├── scripts/pindou.py          命令行入口
├── pindou/                    引擎（palette/geom/canvas/brushes/motifs/comp/stylepack/recipes/beadify/analyze/originality/chartkit/build/cli）
├── styles/*.json              14 个风格包（换风格只改这里）
├── assets/                    色卡（MARD 291 色 + 72 色套装）
└── references/                风格包规范、原创红线与验收、风格简报模板
```
