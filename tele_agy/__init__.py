"""tele-agy: 针对无桌面 Linux 服务器的 Antigravity Telegram 远程控制网关。"""

from .core.config import config
from .core.database import init_db
from .app import app

__version__ = "0.1.0"
__all__ = ["config", "init_db", "app"]
