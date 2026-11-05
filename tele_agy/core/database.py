"""数据库仓储层模块。

使用 SQLite 存储用户会话偏好、活跃会话 ID、工作区路径以及历史会话元数据。
"""

import sqlite3
import datetime
from typing import Optional, List, Dict, Any
from .config import config


def get_connection() -> sqlite3.Connection:
    """获取 SQLite 数据库连接。

    Returns:
        sqlite3.Connection: 已配置 Row 工厂的 SQLite 连接实例。
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化数据库表结构。

    创建 user_state 表和 conversations 表（若不存在）。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 用户状态表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_state (
        user_id INTEGER PRIMARY KEY,
        active_conversation_id TEXT,
        mode TEXT DEFAULT 'auto',
        model TEXT DEFAULT 'auto',
        effort TEXT DEFAULT 'medium',
        policy TEXT DEFAULT 'auto',
        power_state TEXT DEFAULT 'on',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 历史会话表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        conversation_id TEXT PRIMARY KEY,
        user_id INTEGER,
        title TEXT,
        workspace_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()


def get_user_state(user_id: int) -> Dict[str, Any]:
    """查询指定用户的运行偏好与状态，若不存在则创建默认记录。

    Args:
        user_id: Telegram 用户的数字 ID。

    Returns:
        Dict[str, Any]: 包含 mode, model, effort, policy, power_state 等字段的字典。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_state WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO user_state (user_id, mode, model, effort, policy, power_state) VALUES (?, 'auto', 'auto', 'medium', 'auto', 'on')",
            (user_id,)
        )
        conn.commit()
        cursor.execute("SELECT * FROM user_state WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    res = dict(row)
    conn.close()
    return res


def update_user_state(user_id: int, **kwargs: Any) -> None:
    """更新用户的运行配置字段。

    Args:
        user_id: Telegram 用户的数字 ID。
        **kwargs: 待更新的键值对（例如 mode='plan', power_state='off' 等）。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM user_state WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO user_state (user_id) VALUES (?)", (user_id,))

    fields: List[str] = []
    values: List[Any] = []
    for k, v in kwargs.items():
        fields.append(f"{k} = ?")
        values.append(v)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(user_id)

    query = f"UPDATE user_state SET {', '.join(fields)} WHERE user_id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()


def create_or_update_conversation(
    conversation_id: str,
    user_id: int,
    workspace_path: str,
    title: str = ""
) -> None:
    """创建新会话或更新现有会话的工作区及标题。

    Args:
        conversation_id: 会话的唯一 UUID。
        user_id: 所属 Telegram 用户 ID。
        workspace_path: 该会话绑定的工作区绝对路径。
        title: 会话描述标题（可选）。
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cursor.execute("SELECT conversation_id, title FROM conversations WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    if row:
        new_title = title if title else row["title"]
        cursor.execute(
            "UPDATE conversations SET title = ?, workspace_path = ?, updated_at = ? WHERE conversation_id = ?",
            (new_title, workspace_path, now, conversation_id)
        )
    else:
        actual_title = title if title else f"Conversation {conversation_id[:8]}"
        cursor.execute(
            "INSERT INTO conversations (conversation_id, user_id, title, workspace_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, user_id, actual_title, workspace_path, now, now)
        )
    conn.commit()
    conn.close()


def list_conversations(user_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """按更新时间降序获取用户的历史会话列表（支持分页）。

    Args:
        user_id: 所属 Telegram 用户 ID。
        limit: 最大返回数量（默认 10）。
        offset: 偏移量（默认 0）。

    Returns:
        List[Dict[str, Any]]: 会话记录字典列表。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )
    rows = cursor.fetchall()
    res = [dict(r) for r in rows]
    conn.close()
    return res


def count_conversations(user_id: int) -> int:
    """统计用户的历史会话总数。

    Args:
        user_id: 所属 Telegram 用户 ID。

    Returns:
        int: 会话总数。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]
    conn.close()
    return int(total)


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """根据会话 ID 获取会话详情。

    Args:
        conversation_id: 会话的唯一 UUID。

    Returns:
        Optional[Dict[str, Any]]: 存在则返回会话记录字典，不存在返回 None。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,))
    row = cursor.fetchone()
    res = dict(row) if row else None
    conn.close()
    return res
