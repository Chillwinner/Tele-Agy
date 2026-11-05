"""首页导航与欢迎指令模块。

负责展示系统概览看板与核心功能入口按键。
"""

from telegram import Update
from telegram.ext import ContextTypes

from ..core.database import get_user_state
from ..presentation.keyboards import get_start_keyboard
from .base import require_auth


async def handle_cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /start 和 /help 指令：展示欢迎面板与功能导航按键。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    power_icon = "🟢 运行中" if state["power_state"] == "on" else "🔴 已关闭"

    welcome_text = (
        "🤖 **欢迎使用 tele-agy 远程控制网关！**\n\n"
        f"👤 **你的 Telegram ID**: `{user_id}`\n"
        f"⚡ **系统状态**: {power_icon}\n"
        f"⚙️ **当前模式**: `{state['mode']}`\n"
        f"🧠 **当前模型**: `{state['model']}` (Effort: `{state['effort']}`)\n"
        f"🛡️ **安全策略**: `{state['policy']}`\n"
        f"🆔 **当前对话**: `{state['active_conversation_id'] or '未绑定 (将自动创建)'}`\n\n"
        "💡 **快捷操作指南**:\n"
        "• `/power` - 开启 / 关闭 Agent 进程\n"
        "• `/mode` - 切换 Plan / Build 模式\n"
        "• `/model` - 切换模型与思考深度\n"
        "• `/policy` - 切换全自动 / 沙箱 / 审批策略\n"
        "• `/new [路径]` - 新建会话并指定工作区\n"
        "• `/list` - 查看并切换历史对话\n"
        "• `/status` - 查看完整运行面板\n"
        "• `/stop` - 紧急停止当前任务\n\n"
        "直接在聊天框发送你的需求，Agent 将立即执行！"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_start_keyboard()
    )
