"""色卡：MARD 291 色 / 72 色套装，角色化配色（纸、白、浅、中、深、线、点缀）。

设计原则
- 风格包只写"想要的理想颜色"（十六进制），由本模块解析成**真实在售色号**，
  所以图纸上的每个色号都能买到，且能给出 ΔE 误差。
- 色号统一用 MARD 体系（H02 白、H03 浅灰、H04 中灰、H05 深灰、H07 黑、F05 红……），
  同时保留 漫漫/COCO 对照，方便用户按自己的色卡备豆。
"""
import copy
import json
import math
import os
import re
from collections.abc import Mapping
from numbers import Real

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), 'assets')

PAPER = 0                      # 索引 0 永远表示"不放豆"


def _norm(code):
    """'H5' / 'H05' / 'h05' → 'H05'（三位标准写法）。"""
    m = re.match(r'^([A-Za-z]+)0*(\d+)$', str(code).strip())
    if not m:
        return str(code).strip().upper()
    return f'{m.group(1).upper()}{int(m.group(2)):02d}'


def _short(code):
    """'H05' → 'H5'（格子里写字用的短码）。"""
    m = re.match(r'^([A-Z]+)0*(\d+)$', code)
    return f'{m.group(1)}{m.group(2)}' if m else code


def _hex2rgb(hx):
    if not isinstance(hx, str):
        raise ValueError(f'颜色必须是十六进制文本：{hx!r}')
    hx = hx.strip()
    if not re.fullmatch(r'#?(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})', hx):
        raise ValueError(f'无效十六进制颜色：{hx!r}（支持 #RGB 或 #RRGGBB）')
    hx = hx.removeprefix('#')
    if len(hx) == 3:
        hx = ''.join(ch * 2 for ch in hx)
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------- 色卡载入
_CARD = None


def _card():
    """内部只读缓存；公开接口返回副本，避免调用方污染后续作品。"""
    global _CARD
    if _CARD is not None:
        return _CARD
    with open(os.path.join(ASSETS, 'colorSystemMapping.json'), encoding='utf-8') as f:
        raw = json.load(f)
    out = {}
    for hx, v in raw.items():
        code = _norm(v.get('MARD', ''))
        if not re.match(r'^[A-Z]+\d+$', code):
            continue
        out[code] = dict(code=code, short=_short(code), hex=hx.upper(), rgb=_hex2rgb(hx),
                         coco=_norm(v.get('COCO', '')) if v.get('COCO') else '',
                         manman=_norm(v.get('漫漫', '')) if v.get('漫漫') else '',
                         panpan=str(v.get('盼盼', '')), mixiaowo=str(v.get('咪小窝', '')))
    _CARD = out
    return out


def card():
    """返回独立的色卡快照 {code: dict(code, short, hex, rgb, ...)}。"""
    return {code: dict(item) for code, item in _card().items()}


def sets():
    """可用色卡：mard72（72 色套装，便宜好买）/ mard291（全色卡，细节多）。"""
    with open(os.path.join(ASSETS, 'mard72.json'), encoding='utf-8') as f:
        basic = [_norm(c) for c in json.load(f)]
    c = _card()
    basic = [b for b in dict.fromkeys(basic) if b in c]
    return {'mard72': basic, 'mard291': sorted(c)}


def resolve_set(name):
    s = sets()
    if name in s:
        return s[name]
    if name in ('all', 'full', 'mard', None, ''):
        return s['mard291']
    raise SystemExit(f'未知色卡：{name}（可选 {", ".join(s)}）')


# ---------------------------------------------------------------- 色差
def srgb2lab(rgb):
    try:
        a = np.asarray(rgb, np.float32)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('RGB 必须是三个 0–255 数值一组') from exc
    if a.ndim == 0 or a.shape[-1] != 3 or not np.isfinite(a).all() or (a < 0).any() or (a > 255).any():
        raise ValueError('RGB 必须是三个有限的 0–255 数值一组')
    a = a.reshape(-1, 3) / 255.0
    a = np.where(a > 0.04045, ((a + 0.055) / 1.055) ** 2.4, a / 12.92)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]], np.float32)
    xyz = a @ m.T / np.array([0.95047, 1.0, 1.08883], np.float32)
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[:, 1] - 16
    return np.stack([L, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def de2000(L1, L2):
    """CIEDE2000，L1:(N,3) L2:(M,3) → (N,M)。"""
    L1 = L1[:, None, :]
    l1, a1, b1 = L1[..., 0], L1[..., 1], L1[..., 2]
    l2, a2, b2 = L2[:, 0], L2[:, 1], L2[:, 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = l2 - l1, C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dhp = np.where(C1p * C2p == 0, 0, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbp, Cbp = (l1 + l2) / 2, (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(np.abs(h1p - h2p) > 180, (hs + 360) / 2, hs / 2)
    hbp = np.where(C1p * C2p == 0, hs, hbp)
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dth = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def nearest(hex_or_rgb, allowed=None):
    """在允许的色号集合里找最接近的一个，返回 (code, ΔE)。"""
    c = _card()
    if allowed is None:
        allowed = list(c)
    else:
        allowed = [allowed] if isinstance(allowed, str) else list(allowed)
        allowed = list(dict.fromkeys(_norm(code) for code in allowed))
        if not allowed:
            raise ValueError('允许的色号集合为空，不能改用全色卡')
        unknown = [code for code in allowed if code not in c]
        if unknown:
            raise ValueError(f'色卡中没有这些色号：{", ".join(unknown)}')
    rgb = _hex2rgb(hex_or_rgb) if isinstance(hex_or_rgb, str) else tuple(hex_or_rgb)
    lab = srgb2lab([rgb])
    cand = np.array([c[k]['rgb'] for k in allowed], np.float32)
    d = de2000(lab, srgb2lab(cand))[0]
    i = int(np.argmin(d))
    return allowed[i], float(d[i])


def rgb(code):
    return _card()[_norm(code)]['rgb']


def short(code):
    return _card()[_norm(code)]['short']


# ---------------------------------------------------------------- 角色化配色
ROLE_ORDER = ['white', 'light', 'mid', 'dark', 'line', 'accent', 'accent2', 'bg']
# 多数表决权重：线、点缀优先保住；纸最弱（半格以上有墨就算墨）
DEFAULT_WEIGHT = {'paper': 0.80, 'white': 1.50, 'light': 1.00, 'mid': 1.05,
                  'dark': 1.15, 'line': 1.55, 'accent': 1.60, 'accent2': 1.50, 'bg': 1.20}


FALLBACK = {'accent': ['line', 'dark', 'mid'], 'accent2': ['accent', 'line', 'dark'],
            'bg': ['white', 'light', 'mid'], 'white': ['light', 'bg', 'mid'],
            'light': ['white', 'mid', 'bg'], 'mid': ['light', 'dark', 'white'],
            'dark': ['mid', 'line', 'light'], 'line': ['dark', 'mid']}


class Palette:
    """角色 → 索引 的映射。索引 0 = 纸（不放豆），其余索引对应一个真实色号。"""

    def __init__(self, roles, weights=None):
        if not isinstance(roles, Mapping) or not roles:
            raise ValueError('配色必须包含至少一个颜色角色')
        extra = [r for r in roles if r not in ROLE_ORDER]
        if any(not isinstance(r, str) or not re.fullmatch(r'color_\d{3,}', r) for r in extra):
            raise ValueError(f'配色中存在未知角色：{extra}')
        self.roles = ['paper'] + [r for r in ROLE_ORDER if r in roles] + sorted(extra)
        self.codes = {r: _norm(roles[r]) for r in roles}
        unknown = [code for code in self.codes.values() if code not in _card()]
        if unknown:
            raise ValueError(f'色卡中没有这些色号：{", ".join(unknown)}')
        self.idx = {r: i for i, r in enumerate(self.roles)}
        self._rgb = {r: rgb(code) for r, code in self.codes.items()}
        if weights is not None and not isinstance(weights, Mapping):
            raise ValueError('配色权重必须是对象')
        resolved_weights = dict(DEFAULT_WEIGHT)
        resolved_weights.update(weights or {})
        for role, value in resolved_weights.items():
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'配色权重 {role} 必须是正的有限数值')
        self.weight = np.array([resolved_weights.get(r, 1.0) for r in self.roles], np.float32)
        self.missing = []

    # --- 查询
    def __len__(self):
        return len(self.roles)

    def index(self, role):
        if isinstance(role, (bool, np.bool_)):
            raise ValueError('配色索引必须是整数，不能是布尔值')
        if isinstance(role, (int, np.integer)):
            index = int(role)
            if not 0 <= index < len(self.roles):
                raise ValueError(f'配色索引越界：{index}')
            return index
        if not isinstance(role, str):
            raise ValueError('配色查询必须使用颜色角色或有效整数索引')
        if role in self.idx:
            return self.idx[role]
        # 配色里没有这个角色：按语义链退到最接近的可用角色（只有两三个色的风格也能跑）
        for alt in FALLBACK.get(role, []):
            if alt in self.idx:
                self.missing.append((role, alt))
                return self.idx[alt]
        for alt in self.roles[1:]:
            self.missing.append((role, alt))
            return self.idx[alt]
        raise KeyError(f'配色是空的')

    def has(self, role):
        return role in self.idx

    def index_of_code(self, code):
        code = _norm(code)
        for r in self.roles[1:]:
            if self.codes[r] == code:
                return self.idx[r]
        return PAPER

    def code(self, role):
        index = self.index(role)
        return '—' if index == PAPER else self.codes[self.roles[index]]

    def rgb(self, role):
        i = self.index(role)
        return (246, 244, 239) if i == PAPER else self._rgb[self.roles[i]]

    def tone_rgb(self, i):
        return self.rgb(i)

    def used(self):
        return [r for r in self.roles[1:]]

    # --- 从风格包构建
    @classmethod
    def from_style(cls, style, color_set='mard72'):
        allowed = resolve_set(style.get('color_set', color_set))
        want = dict(style.get('palette', {}))
        unknown = set(want) - set(ROLE_ORDER)
        if unknown:
            raise ValueError(f'palette 含未知角色：{sorted(unknown, key=str)}')
        if style.get('bg') == 'fill' and style.get('bg_color'):
            want.setdefault('bg', style['bg_color'])
        roles, report = {}, []
        for r in ROLE_ORDER:
            hx = want.get(r)
            if not hx:
                continue
            code, d = nearest(hx, allowed)
            roles[r] = code
            report.append(dict(role=r, want=hx, code=code, short=_short(code), dE=round(d, 2)))
        if 'line' not in roles:
            raise SystemExit('风格包至少要有一个 line（描边）颜色')
        # 同一色号被两个角色抢用时，后一个自动换次优，避免"两种灰其实是同一颗豆"
        seen = set()
        for r in ROLE_ORDER:
            if r not in roles:
                continue
            if roles[r] in seen:
                cand = [c for c in allowed if c not in seen]
                if not cand:
                    raise ValueError('所选色卡颜色不足，不能为各角色分配不同色号')
                code, d = nearest(want[r], cand)
                roles[r] = code
                for item in report:
                    if item['role'] == r:
                        item.update(code=code, short=_short(code), dE=round(d, 2))
            seen.add(roles[r])
        pal = cls(roles, style.get('weights'))
        pal.report = report
        return pal

    def to_dict(self):
        return dict(roles={r: dict(code=self.codes[r], short=_short(self.codes[r]), hex=_card()[self.codes[r]]['hex'])
                           for r in self.roles[1:]},
                    report=copy.deepcopy(getattr(self, 'report', [])))

    @classmethod
    def from_codes(cls, codes):
        """从一组色号还原配色（按亮度分配角色）——读回网格文件时用。"""
        cs = list(dict.fromkeys(_norm(c) for c in codes))
        unknown = [code for code in cs if code not in _card()]
        if unknown:
            raise ValueError(f'色卡中没有这些色号：{", ".join(unknown)}')
        cs.sort(key=lambda c: (-_lum(rgb(c)), c))
        names = ROLE_ORDER + [f'color_{i + 1:03d}' for i in range(len(ROLE_ORDER), len(cs))]
        roles = {n: c for n, c in zip(names, cs)}
        return cls(roles)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
