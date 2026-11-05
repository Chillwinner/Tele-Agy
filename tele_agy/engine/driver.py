"""Antigravity CLI (agy) 进程生命周期驱动器。

负责构建执行命令、调度后台异步子进程、流式双向管道交互以及支持任务紧急打断 (SIGINT/SIGKILL)。
"""

import asyncio
import json
import os
import signal
from typing import Optional, Callable, Dict, Any, List

from ..core.config import config
from .protocol import parse_stream_line, EventType, StreamEvent


class AgyDriver:
    """agy 进程驱动类。

    Attributes:
        workspace_path: 执行该任务所在的工作区目录路径。
        mode: 运行模式 (auto / plan / accept-edits)。
        model: 模型选择 (auto / flash / pro 等)。
        effort: 思考深度 (low / medium / high / max)。
        policy: 安全策略 (auto / sandbox / review)。
        conversation_id: 关联的持久化会话 UUID。
        process: 底层异步子进程实例。
    """

    def __init__(
        self,
        workspace_path: str,
        mode: str = "auto",
        model: str = "auto",
        effort: str = "medium",
        policy: str = "auto",
        conversation_id: Optional[str] = None
    ) -> None:
        """初始化驱动器配置。

        Args:
            workspace_path: 工作区绝对路径。
            mode: 运行模式。
            model: 模型名称。
            effort: 思考推理深度。
            policy: 安全与审批策略。
            conversation_id: 会话 ID。
        """
        self.workspace_path: str = workspace_path
        self.mode: str = mode
        self.model: str = model
        self.effort: str = effort
        self.policy: str = policy
        self.conversation_id: Optional[str] = conversation_id

        self.process: Optional[asyncio.subprocess.Process] = None
        self._is_cancelled: bool = False

    def build_command(self) -> List[str]:
        """构建调用 agy CLI 的完整命令行参数列表。

        Returns:
            List[str]: 格式化后的命令行参数列表。
        """
        cmd: List[str] = [config.AGY_BIN_PATH]

        # 启用流式 JSON 管道
        cmd.extend(["--input-format", "stream-json", "--output-format", "stream-json"])

        # 模式设置
        if self.mode in ["auto", "plan", "accept-edits"]:
            cmd.extend(["--mode", self.mode])

        # 思考深度
        if self.effort:
            cmd.extend(["--effort", self.effort])

        # 模型选择
        if self.model and self.model != "auto":
            cmd.extend(["--model", self.model])

        # 安全审批策略
        if self.policy == "auto":
            cmd.append("--dangerously-skip-permissions")
        elif self.policy == "sandbox":
            cmd.append("--sandbox")

        # 绑定会话 ID
        if self.conversation_id:
            cmd.extend(["--conversation", self.conversation_id])

        return cmd

    async def run(
        self,
        prompt: str,
        on_thought: Callable[[str], None],
        on_tool_call: Callable[[str, Dict[str, Any]], None],
        on_text: Callable[[str], None],
        on_ask_question: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> int:
        """启动 agy 子进程并流式处理输出事件。

        Args:
            prompt: 发送给 Agent 的用户指令文本。
            on_thought: 思考片段产生时的回调函数。
            on_tool_call: 工具调用发起时的回调函数。
            on_text: 回答正文增量产生时的回调函数。
            on_ask_question: 遇到问答决策中断时的回调函数。

        Returns:
            int: 进程退出码（0 表示正常退出）。
        """
        cmd = self.build_command()

        # 确保工作区目录存在
        if not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path, exist_ok=True)

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_path
            )
        except Exception as e:
            on_text(f"无法启动 agy 进程: {e}")
            return -1

        # 将 prompt 按 NDJSON 格式输入 stdin
        input_payload = json.dumps({"prompt": prompt}) + "\n"
        if self.process.stdin:
            self.process.stdin.write(input_payload.encode("utf-8"))
            await self.process.stdin.drain()

        # 监听标准输出流
        async def read_stdout() -> None:
            if not self.process or not self.process.stdout:
                return

            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue

                event: StreamEvent = parse_stream_line(line_str)
                if event.type == EventType.THOUGHT:
                    on_thought(event.content)
                elif event.type == EventType.TOOL_CALL:
                    on_tool_call(event.tool_name, event.tool_args or {})
                elif event.type == EventType.ASK_QUESTION:
                    if on_ask_question:
                        on_ask_question(event.tool_args or {})
                    else:
                        on_tool_call(event.tool_name, event.tool_args or {})
                elif event.type == EventType.TEXT:
                    on_text(event.content)
                elif event.type == EventType.ERROR:
                    on_text(f"\n[错误] {event.content}\n")

        # 监听标准错误流
        async def read_stderr() -> None:
            if not self.process or not self.process.stderr:
                return
            while True:
                err_line = await self.process.stderr.readline()
                if not err_line:
                    break
                err_str = err_line.decode("utf-8", errors="replace").strip()
                if err_str and "WARNING" not in err_str:
                    on_thought(f"[stderr] {err_str}\n")

        await asyncio.gather(read_stdout(), read_stderr(), return_exceptions=True)
        return await self.process.wait()

    def send_tool_result(self, result_payload: Dict[str, Any]) -> None:
        """向正在等待交互输入的子进程 stdin 写入工具执行结果或决策答案。

        Args:
            result_payload: 包含决策结果或工具输出的字典。
        """
        if self.process and self.process.stdin and not self.process.stdin.is_closing():
            data = json.dumps(result_payload) + "\n"
            self.process.stdin.write(data.encode("utf-8"))
            asyncio.create_task(self.process.stdin.drain())

    async def cancel(self) -> None:
        """优雅中断正在运行的子进程，超时未响应则强制终止。"""
        self._is_cancelled = True
        if self.process and self.process.returncode is None:
            try:
                self.process.send_signal(signal.SIGINT)
                # 轮询等待最多 2 秒进行优雅退出
                for _ in range(10):
                    if self.process.returncode is not None:
                        return
                    await asyncio.sleep(0.2)
                # 超时强制杀灭
                if self.process.returncode is None:
                    self.process.kill()
            except ProcessLookupError:
                pass
