"""内联按键回调统一路由器模块。

负责接收所有 CallbackQuery 事件，根据前缀与操作标识解耦分发至具体业务模块。
"""

from telegram import Update
from telegram.ext import ContextTypes

from .base import is_authorized
from .power import handle_power_callback, handle_cmd_power
from .settings import (
    handle_mode_callback,
    handle_model_callback,
    handle_effort_callback,
    handle_policy_callback,
    handle_cmd_mode,
    handle_cmd_model,
    handle_cmd_policy,
)
from .session import (
    handle_conv_switch_callback,
    handle_conv_page_callback,
    handle_cmd_list,
    handle_cmd_status,
    handle_cmd_new,
)
from .chat import handle_task_cancel_callback, handle_ask_answer_callback


async def handle_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """中央回调路由器。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_authorized(user_id):
        return

    data = query.data or ""

    # 1. 电源操作
    if data in ["power_on", "power_off"]:
        await handle_power_callback(query, data)
    elif data == "show_power":
        await handle_cmd_power(update, context)

    # 2. 紧急打断
    elif data == "task_cancel":
        await handle_task_cancel_callback(query)

    # 3. 运行模式
    elif data.startswith("mode:"):
        await handle_mode_callback(query, data.split(":", 1)[1])
    elif data == "show_mode":
        await handle_cmd_mode(update, context)

    # 4. 模型选择
    elif data.startswith("model:"):
        await handle_model_callback(query, data.split(":", 1)[1])
    elif data.startswith("effort:"):
        await handle_effort_callback(query, data.split(":", 1)[1])
    elif data == "show_model":
        await handle_cmd_model(update, context)

    # 5. 安全策略
    elif data.startswith("policy:"):
        await handle_policy_callback(query, data.split(":", 1)[1])
    elif data == "show_policy":
        await handle_cmd_policy(update, context)

    # 6. 会话管理与分页
    elif data.startswith("conv_switch:"):
        await handle_conv_switch_callback(query, data.split(":", 1)[1])
    elif data.startswith("conv_page:"):
        await handle_conv_page_callback(query, data.split(":", 1)[1])
    elif data == "list_convs":
        await handle_cmd_list(update, context)
    elif data == "new_conv":
        await handle_cmd_new(update, context)

    # 7. 问答决策回答
    elif data.startswith("ask_ans:"):
        await handle_ask_answer_callback(query, data.split(":", 1)[1])

    # 8. 状态面板
    elif data == "show_status":
        await handle_cmd_status(update, context)

    # 9. 无操作占位按钮（如页码显示）
    elif data == "noop":
        pass
