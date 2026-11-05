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


def conversation_exists_on_disk(conv_id: Optional[str]) -> bool:
    """检查指定的会话 ID 是否具有 CLI 支持的真实轨迹数据库文件。

    Args:
        conv_id: 会话 UUID。

    Returns:
        bool: 存在有效轨迹文件返回 True，否则返回 False。
    """
    if not conv_id:
        return False
    db_path = os.path.expanduser(f"~/.gemini/antigravity-cli/conversations/{conv_id}.db")
    return os.path.isfile(db_path)


class AgyDriver:
    """agy 进程驱动类。

    Attributes:
        workspace_path: 执行该任务所在的工作区目录路径。
        mode: 运行模式 (auto / plan / accept-edits)。
        model: 模型选择 (auto / gemini-3.8-flash-medium / claude-sonnet-4-6 等)。
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

        # 模式设置：仅在明确需要 plan 或 accept-edits 时传参
        if self.mode == "plan":
            cmd.extend(["--mode", "plan"])
        elif self.mode == "accept-edits":
            cmd.extend(["--mode", "accept-edits"])

        # 模型选择（auto 则不传让 agy 走默认）
        if self.model and self.model != "auto":
            cmd.extend(["--model", self.model])

        # 思考深度：仅在非 flash 且非空时传参
        if self.model and "flash" not in self.model.lower() and self.effort and self.effort != "none":
            cmd.extend(["--effort", self.effort])

        # 安全审批策略
        if self.policy == "auto":
            cmd.append("--dangerously-skip-permissions")
        elif self.policy == "sandbox":
            cmd.append("--sandbox")

        # 绑定会话 ID：仅当该 ID 在磁盘真实存在时才传参，避免未初始化会话报错
        if self.conversation_id and conversation_exists_on_disk(self.conversation_id):
            cmd.extend(["--conversation", self.conversation_id])

        return cmd

    async def run(
        self,
        prompt: str,
        on_thought: Callable[[str], None],
        on_tool_call: Callable[[str, Dict[str, Any]], None],
        on_text: Callable[[str], None],
        on_ask_question: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_init: Optional[Callable[[str], None]] = None,
    ) -> int:
        """启动 agy 子进程并流式处理输出事件。

        Args:
            prompt: 发送给 Agent 的用户指令文本。
            on_thought: 思考片段产生时的回调函数。
            on_tool_call: 工具调用发起时的回调函数。
            on_text: 回答正文增量产生时的回调函数。
            on_ask_question: 遇到问答决策中断时的回调函数。
            on_init: 会话初始化并返回真实 conversation_id 时的回调函数。

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

        # 正确按照 stream-json 协议规范构造输入事件
        input_payload = json.dumps({
            "event": "user",
            "message": {
                "content": prompt
            }
        }) + "\n"

        if self.process.stdin:
            self.process.stdin.write(input_payload.encode("utf-8"))
            await self.process.stdin.drain()

        # 监听标准输出流
        received_text_deltas = False
        finished_event = asyncio.Event()

        async def read_stdout() -> None:
            nonlocal received_text_deltas
            if not self.process or not self.process.stdout:
                return

            while not finished_event.is_set():
                line = await self.process.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue

                event: StreamEvent = parse_stream_line(line_str)
                if event.type == EventType.INIT:
                    if on_init and event.raw and event.raw.get("conversation_id"):
                        on_init(event.raw["conversation_id"])
                elif event.type == EventType.THOUGHT:
                    on_thought(event.content)
                elif event.type == EventType.TOOL_CALL:
                    on_tool_call(event.tool_name, event.tool_args or {})
                elif event.type == EventType.ASK_QUESTION:
                    if on_ask_question:
                        on_ask_question(event.tool_args or {})
                    else:
                        on_tool_call(event.tool_name, event.tool_args or {})
                elif event.type == EventType.TEXT:
                    received_text_deltas = True
                    on_text(event.content)
                elif event.type == EventType.RESULT:
                    if not received_text_deltas and event.content:
                        on_text(event.content)
                    # 本轮交互已产生最终 result，标识本轮结束
                    finished_event.set()
                    break
                elif event.type == EventType.ERROR:
                    on_text(f"\n[错误] {event.content}\n")
                    finished_event.set()
                    break

        # 监听标准错误流
        captured_stderr: List[str] = []

        async def read_stderr() -> None:
            if not self.process or not self.process.stderr:
                return
            while not finished_event.is_set():
                err_line = await self.process.stderr.readline()
                if not err_line:
                    break
                err_str = err_line.decode("utf-8", errors="replace").strip()
                if not err_str:
                    continue
                captured_stderr.append(err_str)
                if "error:" in err_str.lower() or "fatal:" in err_str.lower():
                    on_text(f"\n❌ **执行错误**: `{err_str}`\n")
                elif "warning:" not in err_str.lower():
                    on_thought(f"[stderr] {err_str}\n")

        stdout_task = asyncio.create_task(read_stdout())
        stderr_task = asyncio.create_task(read_stderr())

        # 等待 stdout 读到 result/error 事件或进程自然退出
        await finished_event.wait()

        # 结束当前子进程（因为每轮请求按需启动独立 agy 实例，或者断开以释放资源）
        try:
            if self.process.stdin and not self.process.stdin.is_closing():
                self.process.stdin.close()
        except Exception:
            pass

        stdout_task.cancel()
        stderr_task.cancel()

        # 等待子进程退出，若 3 秒内未退出则 kill
        try:
            ret_code = await asyncio.wait_for(self.process.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            self.process.kill()
            ret_code = await self.process.wait()

        if ret_code != 0 and captured_stderr and not received_text_deltas:
            err_msg = "\n".join(captured_stderr[-3:])
            on_text(f"\n⚠️ **任务异常退出 (退出码 {ret_code})**:\n```\n{err_msg}\n```\n")
        return ret_code

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
                for _ in range(10):
                    if self.process.returncode is not None:
                        return
                    await asyncio.sleep(0.2)
                if self.process.returncode is None:
                    self.process.kill()
            except ProcessLookupError:
                pass
