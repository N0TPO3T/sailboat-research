"""Keep target-installed matplotlib namespace ahead of Ubuntu's old .pth entry."""
import sys
from pathlib import Path
_local = str(Path(__file__).parent / 'mpl_toolkits')
if 'mpl_toolkits' in sys.modules and Path(_local).is_dir():
    _module = sys.modules['mpl_toolkits']
    _module.__path__ = [_local] + [p for p in _module.__path__ if p != _local]
