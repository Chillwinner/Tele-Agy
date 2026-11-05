"""Telegram 内联按钮组件库。

负责生成各类场景下的 InlineKeyboardMarkup（主页、电源、模式、模型、策略、会话切换、选项问答）。
"""

from typing import List, Dict, Any
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    """生成首页功能快捷导航键盘。

    Returns:
        InlineKeyboardMarkup: 快捷按键布局。
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ 电源总关", callback_data="show_power"),
            InlineKeyboardButton("📋 切换模式", callback_data="show_mode"),
        ],
        [
            InlineKeyboardButton("🤖 切换模型", callback_data="show_model"),
            InlineKeyboardButton("🛡️ 安全策略", callback_data="show_policy"),
        ],
        [
            InlineKeyboardButton("📂 历史会话", callback_data="list_convs"),
            InlineKeyboardButton("📊 状态面板", callback_data="show_status"),
        ]
    ])


def get_power_keyboard(is_on: bool) -> InlineKeyboardMarkup:
    """生成总电源开关操作键盘。

    Args:
        is_on: 当前是否处于运行中 (True 为运行中，False 为关闭休眠)。

    Returns:
        InlineKeyboardMarkup: 包含切换操作的键盘。
    """
    btn_text = "🛑 点击关闭 (Power OFF)" if is_on else "⚡ 点击开启 (Power ON)"
    btn_action = "power_off" if is_on else "power_on"
    return InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, callback_data=btn_action)]])


def get_mode_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """生成 Plan / Build 模式切换键盘。

    Args:
        current_mode: 当前模式标识 ('plan' 或 'auto')。

    Returns:
        InlineKeyboardMarkup: 模式单选键盘。
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'✅ ' if current_mode == 'plan' else ''}📋 Plan 模式", callback_data="mode:plan"),
            InlineKeyboardButton(f"{'✅ ' if current_mode == 'auto' else ''}🔨 Build 模式", callback_data="mode:auto"),
        ]
    ])


def get_model_keyboard(current_model: str, current_effort: str) -> InlineKeyboardMarkup:
    """生成模型与思考推理深度切换键盘。

    Args:
        current_model: 当前模型标识 ('auto', 'flash', 'pro')。
        current_effort: 当前深度标识 ('low', 'medium', 'high', 'max')。

    Returns:
        InlineKeyboardMarkup: 模型与 Effort 选择键盘。
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'✅ ' if current_model == 'auto' else ''}Auto 默认", callback_data="model:auto"),
            InlineKeyboardButton(f"{'✅ ' if current_model == 'flash' else ''}⚡ Flash", callback_data="model:flash"),
            InlineKeyboardButton(f"{'✅ ' if current_model == 'pro' else ''}🧠 Pro", callback_data="model:pro"),
        ],
        [
            InlineKeyboardButton(f"{'✅ ' if current_effort == 'low' else ''}Low", callback_data="effort:low"),
            InlineKeyboardButton(f"{'✅ ' if current_effort == 'medium' else ''}Med", callback_data="effort:medium"),
            InlineKeyboardButton(f"{'✅ ' if current_effort == 'high' else ''}High", callback_data="effort:high"),
            InlineKeyboardButton(f"{'✅ ' if current_effort == 'max' else ''}Max", callback_data="effort:max"),
        ]
    ])


def get_policy_keyboard(current_policy: str) -> InlineKeyboardMarkup:
    """生成安全审批策略切换键盘。

    Args:
        current_policy: 当前策略标识 ('auto', 'sandbox', 'review')。

    Returns:
        InlineKeyboardMarkup: 策略选择键盘。
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{'✅ ' if current_policy == 'auto' else ''}🚀 全自动", callback_data="policy:auto"),
            InlineKeyboardButton(f"{'✅ ' if current_policy == 'sandbox' else ''}🛡️ 沙箱", callback_data="policy:sandbox"),
            InlineKeyboardButton(f"{'✅ ' if current_policy == 'review' else ''}✋ 需审批", callback_data="policy:review"),
        ]
    ])


def get_conversations_keyboard(convs: List[Dict[str, Any]], active_id: str) -> InlineKeyboardMarkup:
    """生成历史会话切换列表键盘。

    Args:
        convs: 历史会话列表数据。
        active_id: 当前处于活跃状态的会话 ID。

    Returns:
        InlineKeyboardMarkup: 包含每个会话切换入口的按键布局。
    """
    keyboard: List[List[InlineKeyboardButton]] = []
    for c in convs:
        cid = c["conversation_id"]
        title = c["title"] or f"会话 {cid[:8]}"
        is_active = (cid == active_id)
        btn_label = f"{'✅ 当前: ' if is_active else '恢复: '}{title[:20]}"
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"conv_switch:{cid}")])
    return InlineKeyboardMarkup(keyboard)


def get_question_keyboard(options: List[str]) -> InlineKeyboardMarkup:
    """针对 Agent 的 ask_question 多选题生成选项点击键盘。

    Args:
        options: 选项文本列表。

    Returns:
        InlineKeyboardMarkup: 每个选项为一个独立按钮的键盘。
    """
    keyboard: List[List[InlineKeyboardButton]] = []
    for opt in options:
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"ask_ans:{opt[:30]}")])
    return InlineKeyboardMarkup(keyboard)


def get_cancel_task_keyboard() -> InlineKeyboardMarkup:
    """生成任务运行期间的紧急停止键盘。

    Returns:
        InlineKeyboardMarkup: 包含停止按钮的单行键盘。
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 紧急停止任务", callback_data="task_cancel")]
    ])
