"""核心对话调度与任务流式生命周期模块。

负责接收用户发送的指令、初始化会话驱动器与防抖渲染器、调度任务并在完成时更新状态。
"""

import asyncio
import uuid
from typing import Dict, Any
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes

from ..core.config import config
from ..core.database import (
    get_user_state,
    update_user_state,
    create_or_update_conversation,
    get_conversation,
)
from ..engine.driver import AgyDriver
from ..presentation.renderer import ThrottledRenderer
from ..presentation.keyboards import get_power_keyboard, get_question_keyboard
from .base import require_auth, active_drivers


async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的常规聊天需求，触发 Agent 执行。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)

    # 1. 检查电源状态
    if state["power_state"] == "off":
        await update.message.reply_text(
            "⏸️ **Agent 当前处于关闭休眠状态**。\n"
            "输入 `/on` 或点击下方按钮开启运行：",
            reply_markup=get_power_keyboard(is_on=False)
        )
        return

    # 2. 检查是否有并发任务正在执行
    if user_id in active_drivers:
        await update.message.reply_text(
            "⚠️ **当前已有任务正在执行中**，请等待完成或输入 `/stop` 紧急打断。"
        )
        return

    user_text = update.message.text
    if not user_text:
        return

    # 3. 获取或自动创建活跃会话
    active_id = state["active_conversation_id"]
    conv = get_conversation(active_id) if active_id else None
    workspace = conv["workspace_path"] if conv else config.DEFAULT_WORKSPACE

    # 4. 初始化 Telegram 初始消息与流式防抖渲染器
    init_msg = await update.message.reply_text("⏳ **准备执行中...**")
    renderer = ThrottledRenderer(context.bot, update.effective_chat.id, init_msg)
    renderer.start()

    # 5. 构建 agy 驱动器实例
    driver = AgyDriver(
        workspace_path=workspace,
        mode=state["mode"],
        model=state["model"],
        effort=state["effort"],
        policy=state["policy"],
        conversation_id=active_id
    )
    active_drivers[user_id] = driver

    # 6. 定义事件回调
    def on_init(cid: str) -> None:
        if cid:
            create_or_update_conversation(
                cid,
                user_id,
                workspace,
                title=user_text[:28]
            )
            update_user_state(user_id, active_conversation_id=cid)

    def on_thought(text: str) -> None:
        renderer.append_thought(text)

    def on_tool(name: str, args: Dict[str, Any]) -> None:
        renderer.add_tool_call(f"{name}")

    def on_text(delta: str) -> None:
        renderer.append_answer(delta)

    def on_ask(args: Dict[str, Any]) -> None:
        questions = args.get("questions", [])
        if questions:
            q = questions[0]
            q_text = q.get("question", "请选择操作:")
            options = q.get("options", [])
            asyncio.create_task(
                update.message.reply_text(
                    f"❓ **Agent 请示**:\n{q_text}",
                    reply_markup=get_question_keyboard(options)
                )
            )

    # 7. 执行驱动
    try:
        await driver.run(
            prompt=user_text,
            on_thought=on_thought,
            on_tool_call=on_tool,
            on_text=on_text,
            on_ask_question=on_ask,
            on_init=on_init
        )
    except Exception as e:
        renderer.set_error(str(e))
    finally:
        await renderer.stop()
        if user_id in active_drivers:
            del active_drivers[user_id]


async def handle_cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /stop 指令：中断当前正在执行的任务。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    if user_id in active_drivers:
        await active_drivers[user_id].cancel()
        del active_drivers[user_id]
        await update.message.reply_text("🛑 **已成功中断当前任务！**")
    else:
        await update.message.reply_text("ℹ️ 当前没有正在运行的任务。")


async def handle_task_cancel_callback(query: CallbackQuery) -> None:
    """处理停止任务按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
    """
    user_id = query.from_user.id
    if user_id in active_drivers:
        await active_drivers[user_id].cancel()
        del active_drivers[user_id]
        await query.message.reply_text("🛑 **任务已紧急中断！**")
    else:
        await query.answer("没有正在执行的任务", show_alert=True)


async def handle_ask_answer_callback(query: CallbackQuery, answer: str) -> None:
    """处理 Agent 提问选项按钮点击回调。

    Args:
        query: Telegram CallbackQuery 对象。
        answer: 用户选中的答案文本。
    """
    user_id = query.from_user.id
    if user_id in active_drivers:
        active_drivers[user_id].send_tool_result({"answer": answer})
        await query.edit_message_text(f"✅ **已选择并提交答案**: `{answer}`")
    else:
        await query.edit_message_text(f"已选择 `{answer}` (任务可能已结束)")
