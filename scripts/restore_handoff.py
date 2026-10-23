"""还原自包含交接包：python scripts/restore_handoff.py 交接包.md 新目录。

先验证所有文件的路径、围栏、重复项和SHA256，再写入；不覆盖现有文件。
"""
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys

MARK = re.compile(r'^<!-- file: (\S+) sha256=([0-9a-f]{64}) eol=([01]) -->$')


def restore(md_path, dest):
    lines = Path(md_path).read_text(encoding='utf-8-sig').splitlines()
    root = Path(dest).resolve()
    pending, names = [], set()
    i = 0
    while i < len(lines):
        m = MARK.fullmatch(lines[i])
        if not m:
            i += 1
            continue
        name, sha, eol = m.groups()
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError(f'非法路径：{name}')
        target = (root / name).resolve()
        identity = str(target).casefold()
        if not target.is_relative_to(root) or identity in names:
            raise ValueError(f'非法或重复路径：{name}')
        if target.exists():
            raise FileExistsError(f'不覆盖现有文件：{target}')
        names.add(identity)
        if i + 1 >= len(lines) or not re.fullmatch(r'`{3,}', lines[i + 1]):
            raise ValueError(f'缺少代码围栏：{name}')
        fence = lines[i + 1]
        j = i + 2
        while j < len(lines) and lines[j] != fence:
            j += 1
        if j == len(lines):
            raise ValueError(f'代码围栏未闭合：{name}')
        data = ('\n'.join(lines[i + 2:j]) + ('\n' if eol == '1' else '')).encode('utf-8')
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError(f'校验失败：{name}')
        pending.append((name, target, data))
        i = j + 1
    if not pending:
        raise ValueError('没有找到源码文件标记，请使用完整交接包')
    # 所有成员都是普通文件；其中任意成员都不能同时充当另一个成员的目录。
    # 必须整批预查，不能写完前面的安全文件才发现后面的路径冲突。
    for name, target, _ in pending:
        for parent in target.parents:
            if str(parent).casefold() in names:
                raise ValueError(f'文件与父目录冲突：{name}')
            if parent.exists() and not parent.is_dir():
                raise FileExistsError(f'父路径不是目录：{parent}')
    for _, target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)
    return [name for name, _, _ in pending]


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    result = restore(sys.argv[1], sys.argv[2])
    print(f'已还原 {len(result)} 个文件，SHA256全部一致')
