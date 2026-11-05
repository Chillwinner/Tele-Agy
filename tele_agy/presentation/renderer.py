"""Telegram 防抖与流式消息渲染器。

负责将 Agent 的思考过程、工具调用与最终回答组合排版，并以严格控频（1.2s 防抖）推送至 Telegram，彻底杜绝 429 Too Many Requests。
"""

import asyncio
import time
from typing import Optional, List
import telegram
from .keyboards import get_cancel_task_keyboard


class ThrottledRenderer:
    """消息防抖节流渲染器。

    Attributes:
        bot: Telegram Bot 客户端实例。
        chat_id: 目标聊天会话 ID。
        message_id: 正在编辑更新的消息 ID。
        thinking_buffer: 思考过程文本累加缓存。
        tool_calls: 工具执行步骤列表。
        answer_buffer: 回答正文累加缓存。
        phase: 当前阶段 (thinking / tools / answering / finished / error)。
        min_interval: 最小编辑刷新间隔（秒）。
    """

    def __init__(self, bot: telegram.Bot, chat_id: int, initial_message: telegram.Message) -> None:
        """初始化渲染器。

        Args:
            bot: Telegram Bot 实例。
            chat_id: 目标聊天 ID。
            initial_message: 初始创建的等待消息。
        """
        self.bot: telegram.Bot = bot
        self.chat_id: int = chat_id
        self.current_message: telegram.Message = initial_message
        self.message_id: int = initial_message.message_id

        self.thinking_buffer: str = ""
        self.tool_calls: List[str] = []
        self.answer_buffer: str = ""
        self.phase: str = "thinking"

        self.last_edit_time: float = 0.0
        self.min_interval: float = 1.2
        self.is_dirty: bool = False
        self._lock: asyncio.Lock = asyncio.Lock()
        self._stop_flusher: bool = False
        self._flush_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """启动后台定时节流刷新轮询任务。"""
        self._flush_task = asyncio.create_task(self._periodic_flush_loop())

    async def stop(self) -> None:
        """停止定时轮询并执行最后一次完整内容同步。"""
        self._stop_flusher = True
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._render_now(is_final=True)

    def append_thought(self, text: str) -> None:
        """追加思考推理文本片段。

        Args:
            text: 增量思考片段。
        """
        self.thinking_buffer += text
        if self.phase == "thinking":
            self.is_dirty = True

    def add_tool_call(self, tool_desc: str) -> None:
        """记录新的工具调用开始。

        Args:
            tool_desc: 工具描述（如 'read_file (src/main.py)'）。
        """
        self.tool_calls.append(tool_desc)
        self.phase = "tools"
        self.is_dirty = True

    def append_answer(self, text: str) -> None:
        """追加最终回答正文片段。

        Args:
            text: 增量正文片段。
        """
        self.answer_buffer += text
        self.phase = "answering"
        self.is_dirty = True

    def set_error(self, err_msg: str) -> None:
        """标记任务发生错误并更新渲染内容。

        Args:
            err_msg: 错误详情。
        """
        self.phase = "error"
        self.answer_buffer = f"❌ **发生错误**:\n```\n{err_msg}\n```"
        self.is_dirty = True

    def _compose_text(self, is_final: bool = False) -> str:
        """根据当前阶段组装 Markdown 格式化消息体。

        Args:
            is_final: 是否为最终完成渲染。

        Returns:
            str: 组装好的文本内容（控制在安全长度内）。
        """
        parts: List[str] = []

        if self.tool_calls:
            tools_block = "⚙️ **工具调用**:\n" + "\n".join(f"• `{t}`" for t in self.tool_calls[-4:])
            parts.append(tools_block)

        if self.phase == "thinking" and not is_final:
            lines = [l for l in self.thinking_buffer.strip().split("\n") if l.strip()]
            recent_thinking = "\n".join(lines[-4:]) if lines else "正在思考..."
            parts.append(f"💭 **思考中**:\n> {recent_thinking}")
        elif self.phase == "tools" and not is_final:
            parts.append("⏳ 正在处理中...")
        elif self.answer_buffer:
            parts.append(self.answer_buffer)
        elif not is_final:
            parts.append("⏳ 正在初始化...")

        content = "\n\n".join(parts)
        if len(content) > 3900:
            content = "...\n" + content[-3850:]
        return content or "⏳ 处理中..."

    async def _periodic_flush_loop(self) -> None:
        """后台轮询循环，每隔 300ms 检查缓冲区并在满足 1.2s 阈值时触发编辑。"""
        while not self._stop_flusher:
            await asyncio.sleep(0.3)
            now = time.time()
            if self.is_dirty and (now - self.last_edit_time >= self.min_interval):
                await self._render_now(is_final=False)

    async def _render_now(self, is_final: bool = False) -> None:
        """真正向 Telegram API 发送 editMessageText 请求。

        Args:
            is_final: 是否为终结帧。
        """
        async with self._lock:
            if not self.is_dirty and not is_final:
                return

            text = self._compose_text(is_final=is_final)
            reply_markup = None if is_final else get_cancel_task_keyboard()

            try:
                await self.bot.edit_message_text(
                    chat_id=self.chat_id,
                    message_id=self.message_id,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                self.last_edit_time = time.time()
                self.is_dirty = False
            except telegram.error.RetryAfter as e:
                # 触发限流时自动退避
                await asyncio.sleep(e.retry_after)
            except telegram.error.BadRequest as e:
                # 若 Markdown 语法冲突，尝试降级为纯文本
                if "Message is not modified" not in str(e):
                    try:
                        await self.bot.edit_message_text(
                            chat_id=self.chat_id,
                            message_id=self.message_id,
                            text=text,
                            reply_markup=reply_markup
                        )
                        self.last_edit_time = time.time()
                        self.is_dirty = False
                    except Exception:
                        pass
            except Exception:
                pass
