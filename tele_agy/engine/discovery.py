"""Antigravity CLI 本地历史会话自动发现模块。

负责从 Antigravity CLI 的 conversation_summaries.db 及 conversations 存储中，
提取真实的会话标题 (title/preview)、精准的工作区路径 (workspace_path) 与最后修改时间，
精准筛选出支持 agy CLI 续接的有效会话，无缝同步到 tele-agy 数据库中。
"""

import os
import re
import json
import sqlite3
import urllib.parse
from typing import List, Dict, Any, Optional
from ..core.config import config
from ..core.database import create_or_update_conversation, get_conversation


def parse_file_uri_to_path(uri: str) -> str:
    """将 file:/// 协议的 URI 转换为系统绝对路径。

    Args:
        uri: 例如 "file:///Volumes/Data/project"。

    Returns:
        str: 转换后的系统路径。
    """
    if not uri:
        return ""
    if uri.startswith("file://"):
        parsed = urllib.parse.urlparse(uri)
        return urllib.parse.unquote(parsed.path)
    return uri


def clean_title(title_raw: str, preview_raw: str) -> str:
    """清理并提取最具可读性的会话标题。

    Args:
        title_raw: 原生 title 字段。
        preview_raw: 原生 preview 字段。

    Returns:
        str: 简洁有意义的标题文本。
    """
    t = (title_raw or preview_raw or "").strip()
    if not t:
        return "未命名会话"

    t = re.sub(r'<[^>]+>', '', t).strip()
    t = re.sub(r'^[#*>\s\-`]+', '', t).strip()
    first_line = t.split("\n")[0].strip()
    return first_line[:32] if first_line else "未命名会话"


def scan_and_sync_local_conversations(user_id: int) -> int:
    """扫描并同步本机所有支持 CLI 续接的历史会话。

    Args:
        user_id: 当前用户的 Telegram 数字 ID。

    Returns:
        int: 同步的总会话数量。
    """
    cli_base = os.path.expanduser("~/.gemini/antigravity-cli")
    conv_dir = os.path.join(cli_base, "conversations")
    db_path = os.path.join(cli_base, "conversation_summaries.db")

    if not os.path.exists(conv_dir) or not os.path.exists(db_path):
        return 0

    # 1. 获取所有真实具有本地轨迹数据库的合法 CLI 会话 ID
    valid_cids = {f[:-3] for f in os.listdir(conv_dir) if f.endswith(".db")}
    if not valid_cids:
        return 0

    count = 0
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 检查 conversation_summaries 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_summaries'")
        if not cursor.fetchone():
            conn.close()
            return 0

        rows = cursor.execute("""
            SELECT conversation_id, title, preview, workspace_uris, last_modified_time 
            FROM conversation_summaries 
            ORDER BY last_modified_time DESC
        """).fetchall()

        for row in rows:
            conv_id = row["conversation_id"]
            if conv_id not in valid_cids:
                continue

            title = clean_title(row["title"], row["preview"])
            ws_path = config.DEFAULT_WORKSPACE
            ws_uris_raw = row["workspace_uris"]
            if ws_uris_raw:
                try:
                    uris = json.loads(ws_uris_raw)
                    if isinstance(uris, list) and uris:
                        extracted = parse_file_uri_to_path(uris[0])
                        if extracted:
                            ws_path = extracted
                except Exception:
                    pass

            create_or_update_conversation(
                conversation_id=conv_id,
                user_id=user_id,
                workspace_path=ws_path,
                title=title
            )
            count += 1

        conn.close()
    except Exception:
        pass

    return count
