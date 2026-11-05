"""会话与工作区管理模块。

负责多会话生命周期管理、工作区切换绑定、历史会话切换及系统看板展示。
"""

import os
import uuid
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..core.config import config
from ..core.database import (
    get_user_state,
    update_user_state,
    create_or_update_conversation,
    list_conversations,
    get_conversation,
)
from ..engine.discovery import scan_and_sync_local_conversations
from ..presentation.keyboards import get_conversations_keyboard, get_cancel_task_keyboard, get_power_keyboard
from .base import require_auth, active_drivers


async def handle_cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /new 指令：创建新会话并绑定工作区。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文，可携带可选的工作区路径参数。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    workspace = config.DEFAULT_WORKSPACE

    # 支持 /new <workspace_path>
    if context.args:
        custom_path = " ".join(context.args).strip()
        abs_path = os.path.abspath(os.path.expanduser(custom_path))
        if os.path.exists(abs_path):
            workspace = abs_path
        else:
            await update.message.reply_text(f"⚠️ 指定路径不存在: `{abs_path}`，使用默认目录。")

    new_conv_id = str(uuid.uuid4())
    create_or_update_conversation(new_conv_id, user_id, workspace, title="新任务会话")
    update_user_state(user_id, active_conversation_id=new_conv_id)

    await update.message.reply_text(
        f"✨ **已创建全新会话！**\n\n"
        f"🆔 会话 ID: `{new_conv_id}`\n"
        f"📁 工作区目录: `{workspace}`\n\n"
        f"现在发送你的指令，Agent 将在全新的上下文中工作！",
        parse_mode="Markdown"
    )


async def handle_cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /list 指令：列出最近历史对话并提供切换按钮。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id

    # 自动扫描并同步本机已有的历史会话
    scan_and_sync_local_conversations(user_id)

    convs = list_conversations(user_id, limit=10)
    state = get_user_state(user_id)
    active_id = state["active_conversation_id"]

    if not convs:
        await update.message.reply_text("📂 目前还没有历史会话，输入 `/new` 开始第一个对话！")
        return

    text = "📂 **历史会话列表 (点击下方按钮一键切换)**:\n\n"
    for idx, c in enumerate(convs, 1):
        cid = c["conversation_id"]
        title = c["title"] or "未命名会话"
        is_active = (cid == active_id)
        mark = "👉 " if is_active else "• "
        active_tag = " `[当前活跃]`" if is_active else ""
        text += f"{mark}**{idx}. 💬 {title}**{active_tag}\n   📁 工作区: `{c['workspace_path']}`\n\n"

    try:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_conversations_keyboard(convs, active_id)
        )
    except Exception:
        plain_text = "📂 历史会话列表 (点击下方按钮一键切换):\n\n"
        for idx, c in enumerate(convs, 1):
            title = c["title"] or "未命名会话"
            is_active = (c["conversation_id"] == active_id)
            mark = "👉 " if is_active else "• "
            active_tag = " [当前活跃]" if is_active else ""
            plain_text += f"{mark}{idx}. 💬 {title}{active_tag}\n   📁 工作区: {c['workspace_path']}\n\n"
        await update.message.reply_text(
            plain_text,
            reply_markup=get_conversations_keyboard(convs, active_id)
        )


async def handle_cmd_cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /cd 指令：查看或切换当前会话绑定的工作区。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文，包含目标路径参数。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    active_id = state["active_conversation_id"]

    if not context.args:
        conv = get_conversation(active_id) if active_id else None
        current_ws = conv["workspace_path"] if conv else config.DEFAULT_WORKSPACE
        await update.message.reply_text(
            f"📁 **当前工作区路径**:\n`{current_ws}`\n\n如需切换，请输入: `/cd <新路径>`"
        )
        return

    new_path = " ".join(context.args).strip()
    abs_path = os.path.abspath(os.path.expanduser(new_path))
    if not os.path.exists(abs_path):
        await update.message.reply_text(f"❌ 路径不存在: `{abs_path}`")
        return

    if active_id:
        create_or_update_conversation(active_id, user_id, abs_path)
    await update.message.reply_text(f"✅ **工作区已切换为**:\n`{abs_path}`")


async def handle_cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /status 指令：打印系统全景状态看板。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    active_id = state["active_conversation_id"]
    conv = get_conversation(active_id) if active_id else None
    ws = conv["workspace_path"] if conv else config.DEFAULT_WORKSPACE
    is_running = (user_id in active_drivers)

    text = (
        "📊 **tele-agy 系统运行状态看板**\n"
        "────────────────────────────\n"
        f"⚡ **总电源状态**: `{'🟢 ON' if state['power_state'] == 'on' else '🔴 OFF'}`\n"
        f"🏃 **当前任务**: `{'⏳ 正在执行中' if is_running else '💤 空闲待命'}`\n"
        f"📁 **当前工作区**: `{ws}`\n"
        f"🆔 **活跃会话 ID**: `{active_id or '未绑定'}`\n"
        f"⚙️ **执行模式**: `{state['mode']}`\n"
        f"🤖 **当前模型**: `{state['model']}` (Effort: `{state['effort']}`)\n"
        f"🛡️ **安全策略**: `{state['policy']}`\n"
    )
    reply_markup = get_cancel_task_keyboard() if is_running else get_power_keyboard(state["power_state"] == "on")
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_conv_switch_callback(query: CallbackQuery, conv_id: str) -> None:
    """处理会话切换按钮回调。

    Args:
        query: Telegram CallbackQuery 对象。
        conv_id: 目标会话的 UUID。
    """
    user_id = query.from_user.id
    conv = get_conversation(conv_id)
    if conv:
        update_user_state(user_id, active_conversation_id=conv_id)
        title = conv["title"] or conv_id[:8]
        await query.edit_message_text(
            f"🔀 **已切换到会话**: `{title}`\n"
            f"📁 关联工作区: `{conv['workspace_path']}`\n\n"
            f"后续发送的消息将直接在该上下文中继续！"
        )
