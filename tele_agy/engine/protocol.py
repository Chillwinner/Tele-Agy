"""Antigravity NDJSON 协议与事件解析模块。

负责将底层 agy 进程通过 stdout 抛出的原始数据流解析为强类型的语义事件。
"""

import json
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class EventType(str, Enum):
    """事件类型枚举。"""
    INIT = "init"
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TEXT = "text"
    ASK_QUESTION = "ask_question"
    RESULT = "result"
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
    tool_args: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None


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

    event_name = data.get("event") or data.get("type")

    # 1. 初始化事件
    if event_name == "init":
        return StreamEvent(type=EventType.INIT, raw=data)

    # 2. step_update 状态更新（包含打字增量、思考增量与工具状态）
    if event_name == "step_update":
        su = data.get("step_update", {})
        # 正文文本增量
        if "text_delta" in su and su["text_delta"]:
            return StreamEvent(type=EventType.TEXT, content=su["text_delta"], raw=data)
        # 思考增量
        if "thinking_delta" in su and su["thinking_delta"]:
            return StreamEvent(type=EventType.THOUGHT, content=su["thinking_delta"], raw=data)
        if "thought_delta" in su and su["thought_delta"]:
            return StreamEvent(type=EventType.THOUGHT, content=su["thought_delta"], raw=data)
        # 工具调用
        if "tool_call" in su or su.get("step_type") == "tool_call":
            tc = su.get("tool_call") or su
            t_name = tc.get("name") or tc.get("tool_name") or "unknown"
            t_args = tc.get("args") or tc.get("tool_args") or {}
            if t_name == "ask_question":
                return StreamEvent(type=EventType.ASK_QUESTION, tool_name=t_name, tool_args=t_args, raw=data)
            return StreamEvent(type=EventType.TOOL_CALL, tool_name=t_name, tool_args=t_args, raw=data)

    # 3. 最终汇总结果事件
    if event_name == "result":
        res = data.get("result", {})
        resp_text = res.get("response", "")
        return StreamEvent(type=EventType.RESULT, content=resp_text, raw=data)

    # 4. 兼容老版本/通用结构
    if "thought" in data:
        return StreamEvent(type=EventType.THOUGHT, content=str(data["thought"]), raw=data)
    if "tool_call" in data:
        tc = data["tool_call"]
        t_name = tc.get("name", "unknown")
        t_args = tc.get("args", {})
        if t_name == "ask_question":
            return StreamEvent(type=EventType.ASK_QUESTION, tool_name=t_name, tool_args=t_args, raw=data)
        return StreamEvent(type=EventType.TOOL_CALL, tool_name=t_name, tool_args=t_args, raw=data)
    if "delta" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["delta"]), raw=data)
    if "content" in data:
        return StreamEvent(type=EventType.TEXT, content=str(data["content"]), raw=data)
    if "error" in data:
        return StreamEvent(type=EventType.ERROR, content=str(data["error"]), raw=data)

    return StreamEvent(type=EventType.UNKNOWN, raw=data)
