"""把整个技能打包成一份自包含的交接包 MD（源码逐字节内嵌 + sha256 校验）。

用法：
    python scripts/pack_handoff.py [输出路径]

产物结构（和最初的墨纹交接包同构）：
    正文：说明 / 红线 / 流程 / 架构 / 规则 / 优化清单 / 验收
    附录 A：还原脚本（把附录 B 的源码逐字节写回，并校验 sha256）
    附录 B：全部源码（每个文件带 <!-- file: 路径 sha256=… eol=… --> 标记）

接手方只要跑附录 A 的脚本，就能得到一份一模一样的技能目录。
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 收录顺序 = 正文里第一次提到的顺序；文档本身（流程与优化全记录.md）不收录，避免自我引用
FILES = [
    'SKILL.md', 'README.md', 'requirements.txt',
    'pindou/__init__.py', 'pindou/palette.py', 'pindou/geom.py', 'pindou/canvas.py',
    'pindou/brushes.py', 'pindou/motifs.py', 'pindou/comp.py', 'pindou/stylepack.py',
    'pindou/recipes.py', 'pindou/beadify.py', 'pindou/analyze.py',
    'pindou/originality.py', 'pindou/chartkit.py', 'pindou/build.py', 'pindou/cli.py',
    'scripts/pindou.py', 'scripts/audit_motifs.py', 'scripts/pack_handoff.py',
    'assets/mard72.json', 'assets/colorSystemMapping.json',
    'references/风格包规范.md', 'references/原创红线与验收.md', 'references/风格简报模板.md',
]

# 风格包目录整体收录（加一个风格包，重新打包就自动带上）
STYLE_DIR = os.path.join(ROOT, 'styles')
FILES += sorted(f'styles/{f}' for f in os.listdir(STYLE_DIR)
                if f.endswith('.json') and not f.startswith('_'))

# v3补齐新增模块、测试、执行记录和可移植的还原脚本；不收录demo和私有资料。
for directory, suffixes in [('pindou', {'.py'}), ('scripts', {'.py'}), ('tests', {'.py'}),
                            ('docs', {'.md', '.json'}), ('references', {'.md'})]:
    FILES += [p.relative_to(ROOT).as_posix() for p in sorted((Path(ROOT) / directory).rglob('*'))
              if p.is_file() and p.suffix in suffixes]
FILES += ['AGENTS.md', '.gitignore', '.gitattributes', 'source_integrity.json']
FILES = list(dict.fromkeys(FILES))

ROLE = {
    'SKILL.md': '技能入口：给 Agent 的操作手册（流程/边界/题材表）',
    'README.md': '使用文档：架构、扩展、FAQ',
    'requirements.txt': '依赖（numpy / pillow / scipy）',
    'pindou/__init__.py': '包说明',
    'pindou/palette.py': '色卡：MARD 291 色 / 72 色套装；理想色 → 真实色号 + ΔE',
    'pindou/geom.py': '纯 numpy 几何：样条、偏移、锥形轮廓、对称轮廓、花瓣叶片',
    'pindou/canvas.py': '绘图引擎：显示列表 → 超采样 → 加权表决成拼豆网格 + 高清原画',
    'pindou/brushes.py': '14 种填充纹理 + 墨溅/光芒/螺旋/编结笔刷',
    'pindou/motifs.py': '75 个参数化造型（走兽/飞羽/虫蛇/海洋/花草/天象/器物/符号/风景/人物/萌物）',
    'pindou/comp.py': '16 个构图模板（含竖幅纵向排版与场景分层）',
    'pindou/stylepack.py': '风格包：加载/默认值/自动匹配/从参考图 DNA 合成',
    'pindou/recipes.py': '配方合成器：题材不重复、构图轮转、画幅配比、主体自动放大',
    'pindou/beadify.py': '拼豆化：闭运算、填洞、白边托底、碎块删除/桥接、统计与难度',
    'pindou/analyze.py': '参考图量化：主色、明暗、边缘、线宽、对称、糊格率、照片识别',
    'pindou/originality.py': '原创性核查：NCC + dHash（含镜像），对照参考图与款间查重',
    'pindou/chartkit.py': '出图：色号图/原画/效果图/总览/目录/zip，全部带 PNG 元数据',
    'pindou/build.py': '一键构建全流程',
    'pindou/cli.py': '命令行实现（8 个命令）',
    'scripts/pindou.py': 'CLI 包装（唯一需要执行的入口）',
    'scripts/audit_motifs.py': '造型对照表（人工挑刺用）',
    'scripts/pack_handoff.py': '本文件的生成器（改完代码重新打包）',
    'assets/mard72.json': '72 色套装色号表',
    'assets/colorSystemMapping.json': '291 色全卡（含漫漫/COCO/盼盼/咪小窝对照）',
    'references/风格包规范.md': '风格包字段逐条说明 + 怎么加新风格',
    'references/原创红线与验收.md': '红线、原创性算法、交付验收清单、存证建议',
    'references/风格简报模板.md': '第 1 步看图写简报的模板',
}

RESTORE = '''"""从交接包 md 还原源码：python3 restore_from_md.py <交接包.md> <目标目录>
找到每个 "<!-- file: 路径 sha256=… eol=… -->" 标记后面的代码块，逐字节写回，并校验 sha256。"""
import hashlib, os, re, sys

MARK = re.compile(r'^<!-- file: (\\S+) sha256=([0-9a-f]{64}) eol=([01]) -->$')


def restore(md_path, dest):
    with open(md_path, encoding='utf-8') as f:     # 文本模式会把 CRLF 统一成 LF，Windows 下载的文件也能还原
        lines = f.read().split('\\n')
    done, i = [], 0
    while i < len(lines):
        m = MARK.match(lines[i])
        if not m:
            i += 1
            continue
        path, sha, eol = m.groups()
        if os.path.isabs(path) or '..' in path.split('/'):
            raise SystemExit(f'非法路径：{path}')
        fence = re.match(r'^(`{3,})', lines[i + 1]).group(1)
        j = i + 2
        while lines[j] != fence:
            j += 1
        data = ('\\n'.join(lines[i + 2:j]) + ('\\n' if eol == '1' else '')).encode('utf-8')
        if hashlib.sha256(data).hexdigest() != sha:
            raise SystemExit(f'校验失败：{path}（内容和打包时不一致）')
        out = os.path.join(dest, path)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'wb') as f:
            f.write(data)
        done.append(path)
        i = j + 1
    if not done:
        raise SystemExit('没有找到文件标记：请确认用的是完整的交接包')
    return done


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    files = restore(sys.argv[1], sys.argv[2])
    print(f'已还原 {len(files)} 个文件到 {os.path.abspath(sys.argv[2])}，sha256 全部一致')
'''

PROSE = r'''# 拼豆原创工坊 · 全量交接包（v2）

> 这份文件由 `scripts/pack_handoff.py` 自动生成：前半部分是流程说明，附录 B 是全部源码（@@n_files@@ 个文件、@@n_lines@@ 行），
> 附录 A 的脚本能把源码逐字节还原成技能目录。源码指纹 `@@fingerprint@@`。
>
> 它合并了两份材料：①最初《墨纹原创流程交接包》的方法论（单一风格、100 款、cairo 实现）；
> ②在此基础上的泛化重构（任意风格、纯 numpy+Pillow、14 个风格包、75 个造型）。
> 原始代码未收录（依赖 cairo + opencv，已被本版取代），但原始**全部规则数值、阈值校准方法、踩坑清单**都在第 2–5 章保留。

---

## 0. 给接手 Agent 的说明（先读）

**阅读方式**：第 0–12 章是说明，请完整读完；附录 B 很长，**不要整段读进上下文**。
先用附录 A 的脚本把源码还原成目录，再按需打开具体文件。

**工作规则**（必须遵守）：
- 每完成一处改动就创建一个 git commit，方便追踪和回滚。
- 每次改动后都要跑 `python scripts/pindou.py selftest`，全部通过再交付。
- 改了引擎或规则，同步更新第 11 节的优化清单（本包的约定）。

**还原 + 冒烟测试**：

```bash
pip install numpy pillow scipy
python restore_from_md.py 本文件.md pindou-original
cd pindou-original && python scripts/pindou.py selftest     # 约 5 秒，通过就能接真图
python scripts/pindou.py motifs                            # 看造型库
python scripts/pindou.py build --style kawaii_pastel --n 4 --out /tmp/try --no-zip
```

**你接到的任务通常是这四种**：
- **A. 直接出图**：用户给了参考图 → 按第 3 节三步走。
- **B. 加题材**：现有 75 个造型不够 → 第 3.3 节 + 第 8 节末尾的写法。
- **C. 加风格**：现有 14 个风格包不够 → 第 3.2 节 + `references/风格包规范.md`。
- **D. 修问题**：图糊了/空了/重复了 → 第 6 章规则表 + 第 11 节优化清单。

拿不准题材、数量、风格方向时先问用户。参考图、他人作品和 IP 角色，任何时候都不能进交付物。

---

## 1. 这套东西是什么

**任意风格的参考图 → 一整套能卖、能举证原创的拼豆图纸。**

参考图只用来"量风格"（配色比例、线宽、纹理密度、构图比例），**画面全部由代码从零画出来**：
样条曲线、几何形、程序化纹样。所以换任何风格都能做，而且不侵权。

```
参考图 ──► 风格 DNA（配色/线宽/纹理/构图比例/糊格率）
                │
                ▼
          风格包 JSON ──┐
                         ├─► 配方合成（风格×题材×构图×种子）──► 调色板网格 ──► 拼豆化 ──► 出图
   造型库 75 个 ─────────┤
   构图模板 16 个 ───────┤
   纹理 14 种 ───────────┘
```

**换风格只改 JSON，换题材只加一个函数，换构图只加一个函数。** 这是"任意风格"的根本原因。

一句话记住区别：
- **风格** = 真的任意（统计出来的参数）
- **题材** = 有词汇表（75 个造型，库外的要新写，约 20 行）

---

## 2. 原创红线（比任何技术步骤都优先）

出发点：**风格本身不受著作权保护，受保护的是具体的画面表达。**

1. **参考图只用来统计风格**（黑白灰比例、构图比例、线宽、墨溅频率、缩成拼豆后的糊格率），
   不描图、不取样像素、不做图生图、不拼贴。代码里没有任何"读参考图"的路径，只有 `analyze.py` 读图算数字。
2. **每款画面都由代码从零绘制**：样条、几何、程序化纹样，控制点都是手写坐标。
3. **参考图保持私有**：不进 git、不进 zip、不外发。`--refs` 只用于原创性核查。
4. **不碰 IP**：动漫/影视/游戏角色、商标、名人肖像、他人签名水印一律不用。
   参考图里有 IP 时，只统计风格，不做同题材。**"同风格原创角色"可以，"复刻那个角色"不行。**
5. **肖像要授权**：做真人头像只能做原创形象，不还原五官比例、发型细节、服装图案。
6. **传统公共母题可以用**（骷髅、罗盘、莲花、青海波、曼陀罗……），但别照搬某位作者的具体排布。
7. **每套都过原创性核查**（第 7 章）。超过阈值就重画，**不许为了通过去调阈值**。
8. **留证**：固定种子（可逐格复现）、网格源文件、PNG 内嵌作者/版权/时间、原创性报告、git 提交。
   卖得好的款建议到中国版权保护中心做美术作品登记。
9. 以上是工程防线，不构成法律意见；具体纠纷请咨询专业人士。

---

## 3. 三步走

### 第 1 步：看参考图，写风格简报（30 秒）

**必须自己打开参考图看**（能看图就看图）。代码只会量数字，判断不了"这是水彩还是赛璐璐"。

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
  "点缀色": "#FEFF8B",
  "是照片吗": false
}
```

模板见 `references/风格简报模板.md`。

### 第 2 步：量化参考图，定风格包

```bash
python scripts/pindou.py analyze <参考图目录> --out out/风格分析.json
```

看四个字段：`推荐纹理`、`画幅配比`、`配色角色`、`photo_like`。然后二选一：

- **有现成风格包能对上** → 直接用（`python scripts/pindou.py styles` 看 14 个）
- **对不上** → 自动合成：`python scripts/pindou.py auto <图目录> --n 12 --out out/x --name "风格名" --subjects ...`
  或者复制一个风格包 JSON 手改（字段见 `references/风格包规范.md`），**不用改代码**。

`--subjects` 必须由你按简报填（把图里的东西映射到造型库，对照表见第 9 章）。

### 第 3 步：出全套 + 自查 + 交付

```bash
python scripts/pindou.py build --style <id|json> --n 24 --out out/系列名 \
    --series "系列名" --prefix XX --seed 1 --subjects cat,star,heart --refs <参考图目录>
```

产出：每款 `色号图/原画/效果图/网格源文件`，加 `总览_N.png`、`目录.csv`、`catalog.json`、
`原创性报告.md`、`说明.txt`、`系列名_全套.zip`。

**交付前必须打开总览图看一遍**，按这五条挑刺：

| 症状 | 怎么改 |
|---|---|
| 糊成一片 / 中间灰多 | 换更粗的纹理（halftone→dots→scales→solid），或加大 `line_width` |
| 断线 / 细节消失 | `line_width` 调到 1.4–1.8；去掉过密纹理 |
| 飘着的小碎点 | 会被删：把 `splatter` 调小或去掉 |
| 画面太空 | 换构图（`--templates`），或提高 `fill_ratio` |
| 几款长得像 | 换 `--seed`，或让 `--subjects` 更分散、`--templates` 更杂 |

---

## 4. 架构：四层组合

### 4.1 角色化配色（替代最初的固定 7 档）

| 角色 | 作用 | 必需 |
|---|---|---|
| `line` | 描边、轮廓、深色细节 | **是** |
| `white` | 高光、眼白、留白、贴纸白边 | 建议 |
| `light` / `mid` / `dark` | 主体亮面/中间调/暗面 | 建议 |
| `accent` / `accent2` | 点睛色（每款只用一处） | 可选 |
| `bg` | 满底铺色时的底色 | `bg=fill` 时必需 |

理想色 → CIEDE2000 在 MARD 色卡里找最近的真实色号 → 输出 ΔE。
同色号被两角色抢占时自动换次优；角色缺失按语义链回退（`accent→line→dark`），所以 2 色风格包也能跑。

### 4.2 风格包（14 个内置）

`ink_tattoo` 墨纹 · `kawaii_pastel` 马卡龙萌系 · `pop_art` 波普 · `pixel_retro` 像素复古 ·
`mandala_gold` 曼陀罗金 · `ukiyoe` 和风 · `lowpoly` 低多边 · `neon_cyber` 赛博霓虹 ·
`botanical` 植物线描 · `stained_glass` 彩窗 · `chinese_ink` 国风水墨 ·
`nordic_tribal` 北欧部落 · `sunset_warm` 落日渐变 · `anime_cel` 日系赛璐璐

### 4.3 造型库（75 个，11 类）

| 类别 | 造型 |
|---|---|
| beast 走兽 | 猫 猫脸 狐狸 狼 熊 熊脸 兔 兔脸 鹿 龙 小恐龙 |
| bird 飞羽 | 小鸟 猫头鹰 |
| bug 虫蛇 | 蝴蝶 飞蛾 蜜蜂 蛇 |
| sea 海洋 | 小鱼 锦鲤 鲸 章鱼 水母 海龟 蟹 |
| flora 花草 | 花 玫瑰 莲花 蘑菇 叶 蕨 仙人掌 树 花环 |
| sky 天象 | 月 太阳 星球 星星 彗星 星座 日蚀 |
| object 器物 | 蜡烛 钥匙 瓶子 沙漏 灯笼 船锚 匕首 书 咖啡 相机 磁带 时钟 药瓶 |
| symbol 符号 | 眼睛 心 骷髅 罗盘 曼陀罗 山 浪 阴阳 螺旋 三角结 |
| scene 风景 | 丘陵 树林 水面 小屋 小船 灯塔 |
| person 人物 | 半身像 Q版小人 |
| cute 萌物 | 小幽灵 云 彩虹 星星仔 |

### 4.4 构图模板（16 个）

`badge` 徽章 · `frame` 几何框 · `arch` 拱框 · `fullbleed` 满幅 · `medallion` 圆章 ·
`poster` 海报 · `banner` 绶带 · `wreath` 花环 · `radial` 放射 · `window` 彩窗 ·
`tile` 纹样铺贴 · `sticker` 贴纸 · `card` 卡片 · `corner` 角饰 · `horizon` 地平线 ·
`scene` 场景（风景/照片专用，四层：天空→远山两层→主体→地面+前景）

### 4.5 纹理（14 种）

`solid` `stipple` `hatch` `cross` `dots` `scales` `seigaiha` `waves` `checker` `halftone`
`confetti` `contour` `weave` `gradient`

风格包可给 `texture_pool`，每款随机挑一种。口诀：**线越细，纹理越要粗**。

---

## 5. 引擎实现

```
显示列表（poly/stroke/tapered/circle/ring/rect/compound/clip/pixels）
   ├─► 网格路径：8 倍超采样 → PIL 多边形逐形状栅格化 → 每格加权多数表决落一颗豆
   └─► 原画路径：32 px/格 渲染 → 2 倍 BOX 降采样 → 抗锯齿原画
```

- **加权表决**：`line` 1.55、`accent` 1.60、`white` 1.50、`paper` 0.80。半格墨也算墨，一颗红豆不会被灰吞。
- **偏移轮廓描边**：粗线不逐段画，算"中心线两侧各偏移 w/2 的闭合多边形"再填充（避免 1px 接缝）。
- **单颗线落格**：宽度 < 1.35 格的线用单颗线落格并去 L 形拐角 → 不断、不双线。
- **单颗豆**：半径 < 0.8 格的圆点直接落成 1 颗。
- 单款约 1.5–2.5 秒（含三张 PNG）。

---

## 6. 拼豆工艺规则（硬约束，沿用最初校准的数值）

| 规则 | 数值 / 做法 |
|---|---|
| 画幅 | S 52×52（1 板）· V 52×104（2 板）· M 78×78（4 板）；设计坐标一律 52 格宽 |
| 栅格化 | 8 倍超采样 + 加权多数表决 |
| 线宽 | 主轮廓 ≥ 1.2 格，细节线 ≥ 1 格；< 1.35 格自动单颗线 |
| 纹样周期 | 重复纹样 ≥ 3 格；青海波圈距 ≥ 2 格 |
| 灰阶 | 最多 2–3 阶色块，或 4×4 Bayer 抖动；不做写实渐变 |
| 墨溅 | 墨点 ≥ 1 格且贴近主体 |
| 外轮廓 | 1 格白豆托底；1 格闭运算 + 填 ≤ 16 格小洞 |
| 碎块 | < 30 格删掉；离主体 ≤ 5 格用四邻桥接并进来 |
| 整件 | 四邻连通成一整片，熨好不掉零件 |
| 点睛色 | 每款只用在 1 个焦点，面积要小 |
| 铺满 | 主体包围盒够大（长边 ≥ 0.6、短边 ≥ 0.45 画布） |
| 孤立单颗 | ≤ 豆子总数 25% |
| 难度 | `score = 颗数/1100 + 孤立单颗/220 + max(0,色数−2)×0.35 + (板数−1)×0.25`；星级 `clip(round(1+score/1.35), 2, 5)` |

**兜底**：整理后豆子少于原来的 55%（主体被当碎块删了），自动放宽桥接距离到 16 格重跑。

---

## 7. 原创性核查

1. 成品网格 → 墨量图（按色号亮度）→ 裁包围盒 → 拉伸 32×32
2. **NCC**：零均值单位向量余弦相似度（含镜像取大）
3. **dHash**：9×8 差分哈希 64 位，取汉明距离最小值（含镜像）
4. 参考图先转成"照搬版"（直接缩到 52 格再量化），两边同尺度比

| 判定 | 阈值 |
|---|---|
| 与任何参考图 NCC | < 0.75 |
| 与任何参考图 dHash | ≥ 10（**仅当 NCC ≥ 0.60 时参与判定**） |
| 款与款之间 NCC | < 0.92 |

判定逻辑：`太像 = NCC ≥ 0.75 或 (dHash < 10 且 NCC ≥ 0.60)`。
理由：拼豆图很稀疏，两件不同作品也可能同档哈希；而"照搬"的 NCC 一定 ≥ 0.85（校准数据：
同一图缩到 44/64 格再与 52 格比，NCC 0.854–0.991）。

数值通过后仍要人工复核 `nearest_ref` 最高的几款，和参考图并排看。

---

## 8. 能力边界（必须对用户说清）

| | 能力 | 说明 |
|---|---|---|
| **风格** | ✅ 任意 | 配色/线宽/纹理/明暗/构图比例都从参考图统计，风格包是纯数据 |
| **题材** | ⚠️ 75 个造型 | 库外题材要新写造型（约 20 行） |

| 素材 | 能不能做 | 怎么做 |
|---|---|---|
| 动物/植物/天体/器物/符号 | ✅ 能 | 造型库直接对应 |
| **风景照片** | ✅ 能 | `scene` 构图 + `hill/forest/lake/house/boat/lighthouse` |
| **人物照片** | ⚠️ 只能原创头像 | `bust`/`chibi`，不还原相貌（肖像权） |
| **漫画角色** | ⚠️ 只能同风格原创角色 | 用该画风画新角色，不复刻具体角色（IP） |

**它出的是"同风格的新作品"，不是"把这张照片原样转成图纸"**——后者属于"照图转图"，不是本技能。

**加新造型的写法**（20 行左右）：

```python
@motif('jelly_donut', 'cute', '果冻甜甜圈')
def _jelly_donut(cv, cx, cy, s, st, rng):
    ring = geom.arc(cx, cy, 0.8 * s, 0, 2 * math.pi, 0.35)
    cv.compound([ring, geom.arc(cx, cy, 0.34 * s, 0, 2 * math.pi, 0.35)], st.get('fill', 'mid'))
    cv.stroke(ring, 1.4, st.get('line', 'line'))
    for k in range(6):
        a = 2 * math.pi * k / 6
        cv.circle(cx + 0.57 * s * math.cos(a), cy + 0.57 * s * math.sin(a), 0.07 * s, st.get('accent', 'accent'))
    return (cx - 0.8 * s, cy - 0.8 * s, cx + 0.8 * s, cy + 0.8 * s)
```

要点：局部坐标 [-1,1]；用 `T(pts,cx,cy,s)` 缩放，**坐标里别再乘 s**（会双重缩放）；
主体用 `body()` 铺纹理+描边；返回包围盒。写完跑 `audit` 看一眼。

---

## 9. 题材 → 造型对照表

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
| 风景：丘陵 / 树林 / 水面 / 小屋 / 小船 / 灯塔 | `hill` `forest` `lake` `house` `boat` `lighthouse` |
| 人物：半身头像 / Q版小人 | `bust` `chibi` |

全量清单：`python scripts/pindou.py motifs`。

---

## 10. 命令速查

```bash
python scripts/pindou.py styles                 # 14 个风格包
python scripts/pindou.py motifs                 # 75 造型 / 16 构图 / 14 纹理
python scripts/pindou.py analyze <图目录> [--out dna.json] [--save-style 名字]
python scripts/pindou.py auto <图目录> --n 12 --out out/x --name "风格名" --subjects a,b,c
python scripts/pindou.py build --style <id|json> --n 24 --out out/x [--subjects a,b] [--templates a,b] [--seed 1] [--prefix XX] [--refs 图目录] [--cs 28] [--no-zip]
python scripts/pindou.py check out/x --refs <图目录>
python scripts/pindou.py audit --style ink_tattoo --out audit.png
python scripts/pindou.py selftest
```

---

## 11. 优化清单（v1 → v2，共 25 条）

| # | 问题 | 原因 | 改法 | 验证 |
|---|---|---|---|---|
| O1 | 换机器跑不起来 | 依赖 pycairo + OpenCV | 纯 numpy+Pillow+scipy 重写渲染与形态学 | 本机（无 cairo/opencv）跑通 |
| O2 | 粗线边缘有 1px 白缝 | PIL 逐段画线，段间漏缝 | 改偏移轮廓多边形一次成形 | 放大 4 倍检查 |
| O3 | 原画边缘有毛刺 | LANCZOS 在高对比边缘振铃 | 改 BOX 降采样 | 圆环边缘干净 |
| O4 | 原画外一圈白噪点 | 白豆托底被画成小圆点 | 亮度 > 238 的点不画 | 纸底干净 |
| O5 | 只能做黑白红 | 色阶写死 7 档 | 角色化配色（9 角色，可缺省可回退） | 14 个风格包 |
| O6 | 图纸色号买不到 | 直接写十六进制 | 理想色→CIEDE2000 匹配真实色号 + ΔE | 色号全在 291 卡内 |
| O7 | 两种灰其实是同一颗豆 | 两角色匹配到同一色号 | 抢占时取次优 | 色数不再虚高 |
| O8 | 换题材要写新配方 | 每款一个手写函数 | 参数化造型库 0→75，装饰器自动注册 | 造型对照表 |
| O9 | 构图只有几种 | 配方自带构图 | 构图模板库 0→16 | 16 个模板 |
| O10 | 同风格下每款长得像 | 纹理固定 | 14 纹理 + `texture_pool` 随机 | 同套内有变化 |
| O11 | 有些款主体特别小 | 造型尺寸与画布不匹配 | 按造型包围盒自动放大一次（环形限 1.18 倍） | 占位率提升 |
| O12 | 主体飘着、熨完掉件 | 主体没贴住边框/地面 | 模板改为贴住；竖幅加竖向装饰 | 112 款全部一整片 |
| O13 | 偶尔整款变空 | 碎块清理把主体删了 | 豆子 < 55% 时放宽桥接重跑 | 0 空款 |
| O14 | 边缘密度恒为 0.12 | 阈值取 88 分位，比例天然固定 | 改"相对对比度固定阈值"（0.3×P99.5） | 不同图有区分度 |
| O15 | 彩色图配色糊成灰 | 只按亮度分配角色 | 双模式：黑白走亮度阶梯，彩色按色相挑 | 风景系列 4 个真色 |
| O16 | 照片被做成白底图标 | 背景判定只看占比 | `photo_like` → 满底 + 渐变 + 地面用 mid | 风景系列像照片 |
| O17 | 风景变成一枚徽章 | 没有分层构图 | 新增 `scene`（四层构图） | 10 款风景系列 |
| O18 | 不能做人物/角色 | 没有人物造型 | 新增 `chibi`/`bust` + `anime_cel` | 8 款角色系列 |
| O19 | 同题材同构图出重复款 | 构图只按顺序轮，不查重 | 同 (题材,构图) 全局唯一 | 款间 NCC 0.913→0.79 |
| O20 | 原创性报告误判未通过 | dHash 单指标在稀疏图误报 | 改组合判定（NCC 优先） | 12 款系列通过 |
| O21 | 不能直接用 analyze 结果 | build 只认风格包 | 自动识别风格 DNA 并转换 | 一条命令串起来 |
| O22 | 缺角色时崩溃 | `palette.index` 直接抛异常 | 语义链回退 | 2 色风格包能跑 |
| O23 | 中文字体找不到 | 路径写死 | 自动查找三平台字体 | 三平台通用 |
| O24 | 没有统一入口 | 一堆脚本 | 8 命令 CLI | 全流程可跑 |
| O25 | 难度星级不准 | 系数按原 100 款校准 | 系数沿用，风格包可覆盖 | 分布合理 |

---

## 12. 已知限制与下一步

**限制**：①题材是封闭词汇表；②人物不做相貌还原；③竖幅里扁平题材（鲸/海龟/莲花）容易显空；
④复杂场景（多层建筑、人群、车辆）做不到；⑤效果图是模拟，不是真实熨烫照片。

**下一步（按价值排序）**：①按销量反馈补造型（生肖、星座、地标、宠物品种）；
②加场景道具（桥、栅栏、路、招牌）；③加文字/数字（生日、首字母，礼品刚需）；
④风格包扩到国潮/昭和/Y2K/莫兰迪/素描；⑤出 A4 PDF 图纸（分页 + 分区编号）。

---

## 13. 交付前验收清单

- [ ] 总览图人工过了一遍：没有糊、断、飘、空、重复
- [ ] 每款都是四邻连通的一整片，熨完不掉零件
- [ ] 每款色数 ≤ 8，色号都在 MARD 卡里
- [ ] `原创性报告.md` 结论"通过"，最像的几款已人工复核
- [ ] 参考图没进 zip、没进 git
- [ ] 网格源文件（`网格/*.txt`）齐全，能逐格复现
- [ ] 目录.csv / catalog.json 的数字和网格对得上
- [ ] PNG 都带 Title/Author/Copyright/CreationTime
- [ ] 交付物：总览、色号图、原画、效果图、网格、目录、原创性报告、zip

---

## 14. 踩坑（原始 11 条 + v2 新增 7 条）

**原始（墨纹）**
1. 缩图不等于拼豆：直接缩到 52 格，糊格率中位数 62%，必须按规律重画
2. 细线和密纹会消失或糊掉：线宽 < 1 格就断，纹样周期 < 3 格就糊
3. 飘在外面的碎点会掉：离主体远了要么删掉要么拉出很长的桥
4. 画面太空不好看
5. 重复款：同一题材很容易画成"换个姿势的同一张"
6. 调色板压缩会并色：小面积红会被并成暗红，必须锁关键色
7. 改共用引擎会改老作品
8. 种子要固定：只用传入的 rng
9. 难度要按分布校准
10. 参考图里可能有 IP 或 AI 图
11. 字体路径要能配

**v2 新增**
12. **双重缩放**：`T(pts,cx,cy,s)` 之后坐标里又乘 `s`，花朵造型一度把整张画布糊满。
    约定：局部坐标一律 [-1,1]，缩放只在 `T()` 里做一次。
13. **主体飘着被删**：模板摆位不贴边框，`finalize` 就当碎块清掉。模板必须保证主体贴住边框/地面。
14. **竖幅空白**：52×104 用圆形构图会上下大片空，必须改椭圆 + 下方竖向装饰。
15. **dHash 误报**：稀疏图哈希碰撞率高，单看 dHash 会冤枉好作品，要和 NCC 一起判。
16. **同题材同构图 = 重复款**：排方案必须做组合查重。
17. **白豆托底别画进原画**：纸底上看不见，只会变成一圈噪点。
18. **加造型先跑 audit**：全部造型排一张表，糊/断/空一眼挑出来。

---

## 附录 A：还原脚本

把下面这段存成 `restore_from_md.py`，然后运行：

```bash
python3 restore_from_md.py <这份 md> pindou-original
```

它会找出附录 B 里每个文件的标记和代码块，逐字节写回，并校验 sha256；只要有一个对不上就报错停止。

<!-- restore-script -->
'''

TABLE_HEAD = '''
## 附录 B：全部源码

顺序 = 正文里第一次用到的顺序。`sha256` 前 12 位列在下表，完整值在每段前面的标记里。

| # | 文件 | 行数 | 作用 | sha256 |
|---|---|---|---|---|
'''

README_HINT = '''
> 本文档由 `scripts/pack_handoff.py` 生成。改了技能里的代码或文档，重新跑一次即可刷新本包：
> `python scripts/pack_handoff.py 输出.md`
'''


def fence_for(text, base=3):
    """选一个不会和内容冲突的围栏长度。"""
    n = base
    while True:
        f = '`' * n
        if not any(line.startswith(f) and set(line) == {'`'} for line in text.split('\n')):
            return f
        n += 1


def read(p):
    with open(os.path.join(ROOT, p), 'rb') as f:
        raw = f.read()
    return raw.replace(b'\r\n', b'\n')     # 统一换行：md 是文本，还原出来必须是 LF，否则 sha 对不上


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '拼豆原创工坊_交接包_v3.md')
    parts, table, lines_total = [], [], 0
    h = hashlib.sha256()
    for i, rel in enumerate(FILES, 1):
        raw = read(rel)
        h.update(raw)
        sha = hashlib.sha256(raw).hexdigest()
        eol = '1' if raw.endswith(b'\n') else '0'
        text = raw.decode('utf-8')
        body = text[:-1] if eol == '1' else text
        n = body.count('\n') + 1
        lines_total += n
        fence = fence_for(body)
        table.append(f'| {i} | `{rel}` | {n} | {ROLE.get(rel, "")} | `{sha[:12]}` |')
        parts.append(f'<!-- file: {rel} sha256={sha} eol={eol} -->\n{fence}\n{body}\n{fence}\n')

    fingerprint = h.hexdigest()[:16]
    head = (PROSE.replace('@@n_files@@', str(len(FILES)))
                 .replace('@@n_lines@@', str(lines_total))
                 .replace('@@fingerprint@@', fingerprint))
    head = head.replace('全量交接包（v2）', '全量交接包（v3）')
    notice = ('> v3更新：本次100项新增优化、验证证据、兼容变化和人工验收步骤见附录中的 '
              '`docs/optimization_100.md`、`docs/verification.md`。正文历史规则仅作背景；冲突时以v3说明和实际代码为准。\n\n')
    head = notice + head
    restore_source = read('scripts/restore_handoff.py').decode('utf-8')
    doc = head + '```python\n' + restore_source + '```\n' + TABLE_HEAD + '\n'.join(table) + README_HINT + '\n---\n\n' + '\n'.join(parts)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(doc)
    print(f'已生成 {out}')
    print(f'  {len(FILES)} 个文件 / {lines_total} 行 / 源码指纹 {fingerprint}')
    print(f'  体积 {os.path.getsize(out) / 1024:.0f} KB')


if __name__ == '__main__':
    main()
