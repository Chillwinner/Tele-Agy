"""电源总开关控制模块。

负责全局总开关的查看、开启、彻底休眠与强杀正在执行的任务。
"""

from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..core.database import get_user_state, update_user_state
from ..presentation.keyboards import get_power_keyboard
from .base import require_auth, active_drivers


async def handle_cmd_power(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /power 指令：展示当前电源状态与切换按钮。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    is_on = (state["power_state"] == "on")

    text = (
        f"⚡ **全局总电源开关**\n\n"
        f"当前运行状态: **{'🟢 运行中 (READY)' if is_on else '🔴 已休眠 (OFF)'}**\n\n"
        f"{'开启状态下：接收指令并正常执行任务。' if is_on else '关闭状态下：后台进程已强杀，拦截一切指令，零资源占用。'}"
    )
    await update.effective_message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_power_keyboard(is_on)
    )


async def handle_cmd_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /on 指令：一键唤醒并开启 Agent。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    update_user_state(user_id, power_state="on")
    await update.message.reply_text("🟢 **Agent 已开启唤醒**，处于就绪状态，可以随时发送任务！")


async def handle_cmd_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /off 指令：一键彻底关闭 Agent 并强杀后台活跃进程。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    update_user_state(user_id, power_state="off")

    # 终止正在执行的任务
    if user_id in active_drivers:
        await active_drivers[user_id].cancel()
        del active_drivers[user_id]

    await update.message.reply_text("🔴 **Agent 已彻底关闭休眠**，后台进程已终止，停止接收新任务。")


async def handle_power_callback(query: CallbackQuery, action: str) -> None:
    """处理电源切换按钮回调事件。

    Args:
        query: Telegram CallbackQuery 对象。
        action: 'power_on' 或 'power_off'。
    """
    user_id = query.from_user.id
    if action == "power_on":
        update_user_state(user_id, power_state="on")
        await query.edit_message_text("🟢 **Agent 已开启！** 可以正常接收并执行任务。")
    elif action == "power_off":
        update_user_state(user_id, power_state="off")
        if user_id in active_drivers:
            await active_drivers[user_id].cancel()
            del active_drivers[user_id]
        await query.edit_message_text("🔴 **Agent 已关闭休眠！** 后台任务已强杀。")
