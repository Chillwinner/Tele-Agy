"""Antigravity NDJSON 协议与事件解析模块。

负责将底层 agy 进程通过 stdout 抛出的原始数据流解析为强类型的语义事件。
"""

import json
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class EventType(str, Enum):
    """事件类型枚举。"""
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TEXT = "text"
    ASK_QUESTION = "ask_question"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class StreamEvent:
    """标准流事件数据结构。

    Attributes:
        type: 事件类型。
        content: 文本或错误内容。
        tool_name: 工具名称（仅限 TOOL_CALL 或 ASK_QUESTION）。
        tool_args: 工具调用参数。
        raw: 原始数据字典。
    """
    type: EventType
    content: str = ""
    tool_name: str = ""
    tool_args: Dict[str, Any] = None
    raw: Dict[str, Any] = None


def parse_stream_line(line_str: str) -> StreamEvent:
    """解析单行标准输出数据为 StreamEvent。

    Args:
        line_str: 从 agy 进程标准输出读取的单行文本。

    Returns:
        StreamEvent: 解析后的结构化事件对象。
    """
    line_clean = line_str.strip()
    if not line_clean:
        return StreamEvent(type=EventType.UNKNOWN)

    try:
        data = json.loads(line_clean)
    except json.JSONDecodeError:
        # 非 JSON 格式普通文本
        return StreamEvent(type=EventType.TEXT, content=line_clean + "\n")

    raw_type = data.get("type") or data.get("event")

    # 1. 思考过程
    if "thought" in data:
        return StreamEvent(type=EventType.THOUGHT, content=str(data["thought"]), raw=data)
    if raw_type == "thought":
        thought_text = data.get("text", "") or data.get("content", "")
        return StreamEvent(type=EventType.THOUGHT, content=str(thought_text), raw=data)

    # 2. 工具调用与提问中断
    if "tool_call" in data or raw_type == "tool_call":
        tc = data.get("tool_call") or data
        t_name = tc.get("name", "unknown")
        t_args = tc.get("args", {})
        if t_name == "ask_question":
            return StreamEvent(
                type=EventType.ASK_QUESTION,
                tool_name=t_name,
                tool_args=t_args,
                raw=data
            )
        return StreamEvent(
            type=EventType.TOOL_CALL,
            tool_name=t_name,
            tool_args=t_args,
            raw=data
        )

    # 3. 正文增量
    if "delta" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["delta"]), raw=data)
    if "content" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["content"]), raw=data)
    if "text" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["text"]), raw=data)
    if "output" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["output"]), raw=data)

    # 4. 错误
    if "error" in data:
        return StreamEvent(type=EventType.ERROR, content=str(data["error"]), raw=data)

    return StreamEvent(type=EventType.UNKNOWN, raw=data)
