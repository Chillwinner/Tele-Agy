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

    采用带并发支持的独立路由编排（block=False），实现类似 BMC/IPMI 的独立带外管理架构，
    确保后台长任务或 agy 进程执行时，控制面指令（/list, /status, /stop, 按钮等）绝对不会被排队卡死。

    Args:
        application: 已初始化的 Telegram Application 实例。
    """
    # 基础与导航（独立带外通道）
    application.add_handler(CommandHandler("start", handle_cmd_start, block=False))
    application.add_handler(CommandHandler("help", handle_cmd_start, block=False))

    # 电源总开关（硬切断带外通道）
    application.add_handler(CommandHandler("power", handle_cmd_power, block=False))
    application.add_handler(CommandHandler("on", handle_cmd_on, block=False))
    application.add_handler(CommandHandler("off", handle_cmd_off, block=False))

    # 模式、模型与安全策略配置
    application.add_handler(CommandHandler("mode", handle_cmd_mode, block=False))
    application.add_handler(CommandHandler("model", handle_cmd_model, block=False))
    application.add_handler(CommandHandler("policy", handle_cmd_policy, block=False))

    # 会话与工作区管理（高优先级独立路由，绝对不被工作负载卡死）
    application.add_handler(CommandHandler("new", handle_cmd_new, block=False))
    application.add_handler(CommandHandler("list", handle_cmd_list, block=False))
    application.add_handler(CommandHandler("cd", handle_cmd_cd, block=False))
    application.add_handler(CommandHandler("status", handle_cmd_status, block=False))

    # 扩展能力查询
    application.add_handler(CommandHandler("mcp", handle_cmd_mcp, block=False))
    application.add_handler(CommandHandler("skills", handle_cmd_skills, block=False))

    # 紧急打断指令（最高优先级独立响应）
    application.add_handler(CommandHandler("stop", handle_cmd_stop, block=False))
    application.add_handler(CallbackQueryHandler(handle_callback_router, block=False))

    # 业务工作负载对话消息
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message, block=False))
