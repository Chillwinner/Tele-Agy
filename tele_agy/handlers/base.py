"""鉴权与全局任务共享状态模块。

提供白名单校验拦截器以及跨模块任务实例的注册与取消管理。
"""

from typing import Dict
from telegram import Update
from ..core.config import config
from ..engine.driver import AgyDriver

# 记录当前每个 Telegram User ID 正在执行的 AgyDriver 实例
active_drivers: Dict[int, AgyDriver] = {}


def is_authorized(user_id: int) -> bool:
    """检查指定 Telegram User ID 是否在白名单中。

    Args:
        user_id: Telegram 用户的数字 ID。

    Returns:
        bool: True 为授权用户，False 为拒绝访问。
    """
    if not config.ALLOWED_USER_IDS:
        # 若未配置白名单，默认允许首个配置环境
        return True
    return user_id in config.ALLOWED_USER_IDS


async def require_auth(update: Update) -> bool:
    """校验消息或事件触发者是否有权访问。

    Args:
        update: Telegram Update 上下文对象。

    Returns:
        bool: True 为放行，False 为拦截并给出提示。
    """
    user = update.effective_user
    if not user or not is_authorized(user.id):
        if update.message:
            await update.message.reply_text("⛔ **未授权访问**\n您的 Telegram ID 不在白名单列表中。")
        return False
    return True
