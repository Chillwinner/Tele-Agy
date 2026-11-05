"""Telegram Bot 路由注册与组装模块。

负责将解耦后的各业务处理器注入 Telegram Application 实例。
"""

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from .handlers.start import handle_cmd_start
from .handlers.power import handle_cmd_power, handle_cmd_on, handle_cmd_off
from .handlers.session import handle_cmd_new, handle_cmd_list, handle_cmd_cd, handle_cmd_status
from .handlers.settings import handle_cmd_mode, handle_cmd_model, handle_cmd_policy
from .handlers.tools import handle_cmd_mcp, handle_cmd_skills
from .handlers.chat import handle_chat_message, handle_cmd_stop
from .handlers.callbacks import handle_callback_router


def setup_bot_handlers(application: Application) -> None:
    """向 Telegram Application 注册所有命令、消息与回调路由。

    Args:
        application: 已初始化的 Telegram Application 实例。
    """
    # 基础与导航
    application.add_handler(CommandHandler("start", handle_cmd_start))
    application.add_handler(CommandHandler("help", handle_cmd_start))

    # 电源总开关
    application.add_handler(CommandHandler("power", handle_cmd_power))
    application.add_handler(CommandHandler("on", handle_cmd_on))
    application.add_handler(CommandHandler("off", handle_cmd_off))

    # 模式、模型与安全策略
    application.add_handler(CommandHandler("mode", handle_cmd_mode))
    application.add_handler(CommandHandler("model", handle_cmd_model))
    application.add_handler(CommandHandler("policy", handle_cmd_policy))

    # 会话与工作区管理
    application.add_handler(CommandHandler("new", handle_cmd_new))
    application.add_handler(CommandHandler("list", handle_cmd_list))
    application.add_handler(CommandHandler("cd", handle_cmd_cd))
    application.add_handler(CommandHandler("status", handle_cmd_status))

    # 扩展能力查询
    application.add_handler(CommandHandler("mcp", handle_cmd_mcp))
    application.add_handler(CommandHandler("skills", handle_cmd_skills))

    # 任务控制与核心对话
    application.add_handler(CommandHandler("stop", handle_cmd_stop))
    application.add_handler(CallbackQueryHandler(handle_callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message))
