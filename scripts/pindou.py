"""命令行包装：python scripts/pindou.py ...
（真正的实现在 pindou/cli.py，这里只负责把项目根目录加进 sys.path）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pindou.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
