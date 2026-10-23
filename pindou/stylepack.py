"""风格包：把"某种画风"翻译成可执行的拼豆规则。

一个风格包 = 颜色 + 线宽 + 纹理 + 画幅配比 + 点缀策略 + 难度系数。
换风格只改 JSON，不改代码；参考图分析（analyze.py）可以自动生成一个新的风格包。

字段（都可省略，缺省值见 DEFAULTS）
  id/name/desc/tags
  palette      角色 → 理想颜色（十六进制），角色：white light mid dark line accent accent2 bg
  color_set    用哪套色卡解析：mard72（默认，便宜好买）/ mard291（细节多）
  bg           paper（贴纸式白边）| fill（满底铺色）
  bg_color     满底时的底色
  line_width   主轮廓线宽（格）
  fill         主体填充用哪个角色
  detail       纹理细节用哪个角色
  fill_texture 主体填充纹理：solid/stipple/hatch/cross/dots/scales/seigaiha/waves/checker/halftone/confetti/contour/weave/gradient
  face_texture 脸部/内部纹理（可省略）
  formats      画幅配比 S/M/V
  templates    允许的构图模板
  subjects     默认题材
  accent_policy  点缀策略：focus=每款点缀个数上限, max_area=面积占比上限
  difficulty   难度系数
"""
import copy
import json
import math
import os
from collections.abc import Mapping
from numbers import Integral, Real

HERE = os.path.dirname(os.path.abspath(__file__))
STYLE_DIR = os.path.join(os.path.dirname(HERE), 'styles')

DEFAULTS = {
    'id': 'custom', 'name': '自定义风格', 'desc': '', 'tags': [],
    'color_set': 'mard72', 'bg': 'paper', 'bg_color': None,
    'line_width': 1.3, 'detail_width': 1.0,
    'fill': 'mid', 'detail': 'line', 'shade1': 'dark', 'shade2': 'line',
    'hi': 'light', 'ground': None, 'face_texture': None, 'wing_texture': None,
    'fill_texture': 'solid',
    'formats': {'S': 0.4, 'M': 0.3, 'V': 0.3},
    'templates': ['badge', 'frame', 'arch', 'fullbleed', 'medallion', 'poster', 'wreath', 'radial', 'corner', 'banner'],
    'subjects': ['flower', 'moon', 'bird', 'cat', 'mountain'],
    'accent_policy': {'focus': 1, 'max_area': 0.05},
    'difficulty': {'bead_div': 1100, 'single_div': 220, 'color_coef': 0.35, 'board_coef': 0.25, 'star_div': 1.35},
    'splatter': 0, 'stipple_density': 0.55, 'fill_ratio': 0.86,
    'rays': True, 'ticks': True,
}

FORMATS = {'S': (52, 52, 1.0), 'V': (52, 104, 1.0), 'M': (52, 52, 1.5)}
FORMAT_INFO = {'S': '小方 52×52（1 块板）', 'V': '竖幅 52×104（2 块板）', 'M': '大方 78×78（4 块板）'}


def _load_all():
    out = {}
    if not os.path.isdir(STYLE_DIR):
        return out
    for fn in sorted(os.listdir(STYLE_DIR)):
        if not fn.endswith('.json') or fn.startswith('_'):
            continue
        with open(os.path.join(STYLE_DIR, fn), encoding='utf-8-sig') as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError(f'风格文件 {fn} 的根节点必须是对象')
        d.setdefault('id', os.path.splitext(fn)[0])
        if not isinstance(d['id'], str) or not d['id'].strip():
            raise ValueError(f'风格文件 {fn} 的 id 必须是非空文本')
        if any(sid.casefold() == d['id'].casefold() for sid in out):
            raise ValueError(f'风格 id 重复：{d["id"]}（文件 {fn}）')
        out[d['id']] = d
    return out


def list_styles():
    return _load_all()


def get(name):
    """按 id 取风格包；也支持直接给 json 文件路径（风格包或 analyze 产出的风格 DNA 都行）。"""
    if name and os.path.isfile(name):
        with open(name, encoding='utf-8-sig') as f:
            d = json.load(f)
        if not isinstance(d, dict):
            raise ValueError('风格文件的根节点必须是对象')
        if 'palette_roles' in d and 'palette' not in d:      # 是风格 DNA，自动转成风格包
            return from_dna(d, name=d.get('name'))
        d.setdefault('id', os.path.splitext(os.path.basename(name))[0])
        return normalize(d)
    all_ = _load_all()
    if name in all_:
        return normalize(all_[name])
    low = {k.lower(): k for k in all_}
    if name and name.lower() in low:
        return normalize(all_[low[name.lower()]])
    raise SystemExit(f'没有风格包「{name}」。可用：{", ".join(sorted(all_))}（或用 --style 指向 json 文件）')


def _number(value, field, minimum=0, maximum=None, positive=False, integer=False):
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or (integer and not isinstance(value, Integral))
            or value < minimum or (positive and value <= minimum)
            or (maximum is not None and value > maximum)):
        raise ValueError(f'风格字段 {field} 的数值无效：{value!r}')
    return int(value) if integer else float(value)


def normalize(d):
    """验证配置并返回完全独立的副本；不会修改用户输入或默认风格。"""
    from . import brushes, palette

    if not isinstance(d, Mapping):
        raise ValueError('风格包必须是对象')
    out = copy.deepcopy(DEFAULTS)
    out.update(copy.deepcopy(dict(d)))
    if out.get('bg') not in ('paper', 'fill'):
        raise ValueError('风格字段 bg 只能是 paper 或 fill')
    supplied_palette = out.get('palette', {})
    if not isinstance(supplied_palette, Mapping):
        raise ValueError('风格字段 palette 必须是角色到十六进制颜色的对象')
    pal = dict(supplied_palette)
    unknown = set(pal) - set(palette.ROLE_ORDER)
    if unknown:
        raise ValueError(f'palette 含未知角色：{sorted(unknown, key=str)}')
    for role, color in pal.items():
        try:
            values = palette._hex2rgb(color)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'palette.{role} 的颜色无效：{color!r}') from exc
        pal[role] = '#%02X%02X%02X' % values
    if out.get('bg_color') is not None:
        out['bg_color'] = '#%02X%02X%02X' % palette._hex2rgb(out['bg_color'])
    if out.get('bg') == 'fill':
        if out.get('bg_color'):
            pal.setdefault('bg', out['bg_color'])
        if 'bg' not in pal:
            raise ValueError(f'风格包 {out["id"]}：bg=fill 时必须给 bg_color 或 palette.bg')
    out['palette'] = pal
    # 缺少的颜色角色只退到实际存在的角色，不能再生成另一个缺失角色。
    for k in ('fill', 'detail', 'shade1', 'shade2', 'hi', 'ground', 'bg_role', 'sky_role', 'hill_far', 'hill_near'):
        v = out.get(k)
        if v is None:
            continue
        if not isinstance(v, str) or v not in palette.ROLE_ORDER + ['paper']:
            raise ValueError(f'风格字段 {k} 引用了未知颜色角色：{v!r}')
        if pal and v != 'paper' and v not in pal:
            out[k] = next((alt for alt in palette.FALLBACK.get(v, []) if alt in pal), next(iter(pal)))
    if out.get('face_texture') is None:
        out['face_texture'] = out.get('fill_texture', 'solid')
    if out.get('wing_texture') is None:
        out['wing_texture'] = out.get('face_texture')
    for key in ('fill_texture', 'face_texture', 'wing_texture'):
        if not isinstance(out[key], str) or out[key] not in brushes.TEXTURES:
            raise ValueError(f'风格字段 {key} 的纹理不存在：{out[key]!r}')
    if 'texture_pool' in out:
        pool = out['texture_pool']
        if not isinstance(pool, (list, tuple)) or not pool:
            raise ValueError('texture_pool 必须是非空纹理列表')
        for texture in pool:
            if not isinstance(texture, str) or texture not in brushes.TEXTURES:
                raise ValueError(f'texture_pool 的纹理不存在：{texture!r}')
        out['texture_pool'] = list(dict.fromkeys(pool))
    mix = out['formats']
    if not isinstance(mix, Mapping) or not mix or set(mix) - set(FORMATS):
        raise ValueError('formats 必须包含 S/M/V 的有效画幅配比')
    out['formats'] = {key: _number(value, f'formats.{key}') for key, value in mix.items()}
    if not any(out['formats'].values()):
        raise ValueError('formats 至少需要一个正的画幅权重')
    for key in ('line_width', 'detail_width'):
        out[key] = _number(out[key], key, positive=True)
    for key in ('stipple_density', 'fill_ratio', 'accent_rate', 'sat_target', 'contrast_target', 'edge_target', 'ink_target'):
        if key in out:
            out[key] = _number(out[key], key, maximum=1)
    for key in ('splatter', 'border', 'close', 'min_island', 'hole', 'bridge_max'):
        if key in out:
            out[key] = _number(out[key], key, integer=True)
    for key in ('difficulty', 'accent_policy', 'weights'):
        if key not in out:
            continue
        if not isinstance(out[key], Mapping):
            raise ValueError(f'风格字段 {key} 必须是对象')
        if key in DEFAULTS:
            out[key] = dict(copy.deepcopy(DEFAULTS[key]), **dict(out[key]))
    for key, value in out['difficulty'].items():
        _number(value, f'difficulty.{key}', positive=key in ('bead_div', 'single_div', 'star_div'))
    for key, value in out.get('weights', {}).items():
        _number(value, f'weights.{key}', positive=True)
    _number(out['accent_policy']['focus'], 'accent_policy.focus', integer=True)
    _number(out['accent_policy']['max_area'], 'accent_policy.max_area', maximum=1)
    return out


# ---------------------------------------------------------------- 自动匹配 / 自动生成
def match(dna):
    """按统计特征给参考图找最接近的风格包，返回 (id, 分数)。"""
    best = (None, 1e9)
    for sid, st in _load_all().items():
        s = 0.0
        st = normalize(st)
        s += abs(st.get('sat_target', 0.35) - dna.get('saturation', 0.35)) * 3
        s += abs(st.get('contrast_target', 0.6) - dna.get('contrast', 0.6)) * 2
        s += abs(st.get('edge_target', 0.25) - dna.get('edge_density', 0.25)) * 2
        s += abs(st.get('ink_target', 0.2) - dna.get('dark_ratio', 0.2)) * 1.5
        if best[1] > s:
            best = (sid, s)
    return best


def from_dna(dna, name=None, color_set=None):
    """用参考图的统计结果造一个风格包（参考图只贡献"规律"，不贡献任何像素）。"""
    if not isinstance(dna, Mapping):
        raise ValueError('风格 DNA 必须是对象')
    dna = copy.deepcopy(dict(dna))
    pal = dna.get('palette_roles') or {}
    if not isinstance(pal, Mapping):
        raise ValueError('palette_roles 必须是对象')
    pal = dict(pal)
    if not pal.get('line'):
        pal['line'] = '#1A1A1A'
    st = copy.deepcopy(DEFAULTS)
    st.update(id=(name or 'auto').strip().replace(' ', '_'), name=name or '参考图风格',
              desc='由参考图统计自动生成（只含规律，不含任何参考图像素）',
              tags=['自动生成'],
              palette=pal,
              color_set=color_set or ('mard291' if len(pal) > 5 else 'mard72'),
              bg='fill' if dna.get('bg_is_filled') else 'paper',
              bg_color=pal.get('bg') if dna.get('bg_is_filled') else None,
              line_width=round(float(np_clip(0.62 * dna.get('line_weight', 1.3) + 0.45, 1.2, 1.7)), 2),
              fill_texture=dna.get('texture', 'solid'),
              face_texture=dna.get('texture', 'solid'),
              fill=dna.get('fill_role', 'mid'),
              detail=dna.get('detail_role', 'line'),
              shade1='dark', shade2='line', ground=('mid' if dna.get('photo_like') else 'dark'),
              sky_role='light', hill_far='mid', hill_near='dark',
              formats=dna.get('formats') or DEFAULTS['formats'],
              subjects=dna.get('subjects') or DEFAULTS['subjects'],
              splatter=dna.get('splatter', 0))
    return normalize(st)


def np_clip(v, lo, hi):
    try:
        value = float(v)
        return max(lo, min(hi, value)) if math.isfinite(value) else lo
    except (TypeError, ValueError, OverflowError):
        return lo
