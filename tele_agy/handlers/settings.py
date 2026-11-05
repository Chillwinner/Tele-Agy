"""运行模式、模型与安全策略调节模块。

负责 Plan/Build 模式切换、模型与思考深度选择、以及全自动/沙箱/审批策略的配置。
"""

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..core.database import get_user_state, update_user_state
from ..presentation.keyboards import get_mode_keyboard, get_model_keyboard, get_policy_keyboard
from .base import require_auth


async def handle_cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /mode 指令：展示当前执行模式并提供单选切换。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    cur = state["mode"]

    text = (
        f"⚙️ **执行模式切换**\n\n"
        f"当前模式: **`{cur}`**\n\n"
        f"• **Plan (规划模式)**: 仅深度分析代码，产出方案与排期，不改动文件。\n"
        f"• **Build (构建模式)**: 完整执行代码修改、跑测试、自主解决问题。"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_mode_keyboard(cur)
    )


async def handle_cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /model 指令：展示模型和思考深度选择键盘。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    cur_m = state["model"]
    cur_e = state["effort"]

    text = (
        f"🧠 **模型与思考深度选择**\n\n"
        f"当前模型: `{cur_m}` | 当前 Effort: `{cur_e}`"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_model_keyboard(cur_m, cur_e)
    )


async def handle_cmd_policy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /policy 指令：展示安全与审批策略切换键盘。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    cur = state["policy"]

    text = (
        f"🛡️ **安全与工具审批策略**\n\n"
        f"当前策略: **`{cur}`**\n\n"
        f"• **全自动 (Auto)**: 自动放行工具调用与写文件，适合免打扰自主运行。\n"
        f"• **沙箱 (Sandbox)**: 限制宿主机访问与敏感调用。\n"
        f"• **严格审批 (Review)**: 敏感命令会在手机上弹窗审批确认。"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_policy_keyboard(cur)
    )


async def handle_mode_callback(query: CallbackQuery, mode: str) -> None:
    """处理模式切换按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
        mode: 目标模式 ('plan' 或 'auto')。
    """
    user_id = query.from_user.id
    update_user_state(user_id, mode=mode)
    await query.edit_message_text(f"✅ **执行模式已切换为**: `{mode}`")


async def handle_model_callback(query: CallbackQuery, model: str) -> None:
    """处理模型选择按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
        model: 目标模型名称 ('auto', 'flash', 'pro')。
    """
    user_id = query.from_user.id
    update_user_state(user_id, model=model)
    await query.edit_message_text(f"✅ **模型已切换为**: `{model}`")


async def handle_effort_callback(query: CallbackQuery, effort: str) -> None:
    """处理思考深度按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
        effort: 目标深度 ('low', 'medium', 'high', 'max')。
    """
    user_id = query.from_user.id
    update_user_state(user_id, effort=effort)
    await query.edit_message_text(f"✅ **思考深度已切换为**: `{effort}`")


async def handle_policy_callback(query: CallbackQuery, policy: str) -> None:
    """处理安全策略按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
        policy: 目标策略 ('auto', 'sandbox', 'review')。
    """
    user_id = query.from_user.id
    update_user_state(user_id, policy=policy)
    await query.edit_message_text(f"✅ **安全策略已切换为**: `{policy}`")
