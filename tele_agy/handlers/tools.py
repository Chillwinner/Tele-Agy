"""MCP 插件与 Skill 技能扩展查询模块。

负责调用 agy 子命令查看生效的 MCP 服务列表，以及读取当前工作区的 Skill 定义。
"""

import os
import subprocess
from telegram import Update
from telegram.ext import ContextTypes

from ..core.config import config
from ..core.database import get_user_state, get_conversation
from .base import require_auth


async def handle_cmd_mcp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /mcp 指令：查询当前配置的 MCP 服务器列表。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    try:
        proc = subprocess.run(
            [config.AGY_BIN_PATH, "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = proc.stdout.strip() or proc.stderr.strip() or "暂无 MCP 服务配置。"
    except Exception as e:
        output = f"获取 MCP 列表失败: {e}"

    await update.message.reply_text(
        f"🔌 **MCP 插件服务器列表**:\n```\n{output}\n```",
        parse_mode="Markdown"
    )


async def handle_cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理 /skills 指令：列出当前工作区中定义的技能列表。

    Args:
        update: Telegram Update 对象。
        context: 回调上下文。
    """
    if not await require_auth(update):
        return

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    conv = get_conversation(state["active_conversation_id"]) if state["active_conversation_id"] else None
    ws = conv["workspace_path"] if conv else config.DEFAULT_WORKSPACE

    skills_dir = os.path.join(ws, ".agents", "skills")
    if os.path.exists(skills_dir):
        skills = os.listdir(skills_dir)
        skills_text = "\n".join(f"• `{s}`" for s in skills if not s.startswith("."))
    else:
        skills_text = "当前工作区尚未定义 `.agents/skills`。"

    await update.message.reply_text(
        f"🛠️ **当前工作区 Skill 技能列表**:\n{skills_text}",
        parse_mode="Markdown"
    )
