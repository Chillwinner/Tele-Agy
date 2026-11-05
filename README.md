# 🚀 tele-agy

> **针对无桌面 Linux 服务器的 Antigravity 远程控制网关**  
> 通过 Telegram 随时随地遥控服务器上的 Antigravity (`agy`)，完整保留个人会员 / Pro 订阅配额，零 API 调用费。

---

## 🏗️ 架构分层与解耦设计 (Decoupled Architecture)

为了便于二次开发、逻辑扩展与功能维护，本项目采用了严格的**分层解耦架构**，所有函数均具备完整的**类型提示（Type Annotations）**与**中文文档注释（Docstrings）**：

```text
tele_agy/
├── core/                  # 1. 核心基础设施层
│   ├── config.py          # 环境变量与运行配置管理
│   └── database.py        # SQLite 仓储层（维护用户偏好、会话与工作区映射）
│
├── engine/                # 2. 引擎执行与底层协议层
│   ├── driver.py          # agy 子进程生命周期驱动器（流式管道、取消与超时治理）
│   └── protocol.py        # NDJSON 协议与事件解析器（强类型 StreamEvent 转换）
│
├── presentation/          # 3. 表现与渲染层
│   ├── keyboards.py       # Telegram 内联按钮组件库（解耦 UI 布局与按键生成）
│   └── renderer.py        # 防抖打字机渲染器（1.2s 时间窗口聚合，免疫 429 风控）
│
├── handlers/              # 4. 业务控制器与分发层
│   ├── base.py            # 鉴权过滤中间件与跨模块活跃任务注册表
│   ├── start.py           # /start 与 /help 首页概览导航
│   ├── power.py           # /power, /on, /off 全局总电源控制（休眠与强杀）
│   ├── session.py         # /new, /list, /cd, /status 会话与工作区管理
│   ├── settings.py        # /mode, /model, /policy 模式、模型与安全策略调节
│   ├── tools.py           # /mcp, /skills 插件与技能扩展管理
│   ├── chat.py            # 核心文本对话接收、问答中断 (ask_question) 调度
│   └── callbacks.py       # 中央内联按钮回调分发路由器
│
├── bot.py                 # 5. Telegram Application 路由组装中心
├── app.py                 # 6. FastAPI 守护服务与 Long Polling 轮询生命周期
└── run.py                 # 7. 服务统一启动入口脚本
```

---

## ✨ 核心特性

- 🧠 **原汁原味会员配额**：通过服务器本地已授权的 Google 账号执行任务，直接消耗个人会员额度，无需按 Token 付费的 API Key。
- ⚡ **全局总电源开关 (`/power`)**：关了强杀后台进程、零资源占用；开了随时就绪接收指令。
- 🔄 **会话与工作区无缝绑定**：每个会话自动关联独立的代码仓库路径，支持在 Telegram 中无刷屏切换历史会话。
- 🎚️ **全功能动态切换**：
  - 模式切换 (`/mode`)：随时切 Plan 规划模式 与 Build 执行模式。
  - 模型切换 (`/model`)：动态切换 Gemini Flash / Pro 及思考深度 (Effort)。
  - 安全策略 (`/policy`)：动态调整全自动 (Auto) / 沙箱隔离 (Sandbox) / 需审批 (Review)。
- 💭 **打字机流式输出与防抖保护**：在 Telegram 端呈现思考流（Thinking）与工具执行过程（Tool Calls），内置时间窗口节流器，100% 避免 Telegram `429 Too Many Requests` 风控。
- ❓ **分支决策与人机交互 (Interrupts)**：自动捕获 `ask_question` 工具调用，在手机端弹出选项按钮，点击即答。
- 🛡️ **严格白名单鉴权**：只响应你在 `.env` 中指定的 Telegram User ID，防盗用防越权。
- 🌐 **无需公网 IP**：基于 Telegram Long Polling 长轮询，服务器在内网、局域网或 NAT 后面均可秒级连通。

---

## 🛠️ 快速开始

### 1. 确保服务器上已安装并登录 agy
在无桌面服务器终端上运行一次登录（消耗会员额度）：
```bash
agy
```
按照终端提示打开授权链接，登录你的 Google 会员账号并授权。凭证将自动保存在 `~/.gemini/`。

### 2. 克隆与安装依赖
```bash
# 1. 创建虚拟环境 (Python 3.9+)
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
复制 `.env.example` 为 `.env`：
```bash
cp .env.example .env
```
编辑 `.env`：
- `TELEGRAM_BOT_TOKEN`: 找 Telegram 的 `@BotFather` 创建机器人获得。
- `ALLOWED_USER_IDS`: 找 Telegram 的 `@userinfobot` 获取你的数字 ID（只有你才能操控此 Bot）。
- `DEFAULT_WORKSPACE`: 你的项目代码根目录。

### 4. 启动服务
```bash
python3 run.py
```
终端输出 `Telegram Bot Long Polling is active!` 即表示连接成功！

---

## 📱 Telegram 常用指令速查

| 指令 | 说明 |
| :--- | :--- |
| `/start` / `/help` | 打开交互主面板与功能导航 |
| `/power` | 查看总电源状态，并弹出开关按钮（关了杀进程，开了就绪） |
| `/on` ｜ `/off` | 快捷开启或彻底关闭 Agent 守护 |
| `/mode` | 切换 Plan (规划模式) / Build (构建执行模式) |
| `/model` | 切换模型 (Flash / Pro) 及思考深度 (Effort) |
| `/policy` | 切换安全策略 (🚀 全自动 / 🛡️ 沙箱 / ✋ 严格审批) |
| `/new [目录路径]` | 创建新会话（可选绑定指定的项目工作区） |
| `/list` | 浏览历史对话摘要，点击按钮一键无刷屏切换 |
| `/cd [新目录路径]` | 查看或变更当前会话绑定的代码目录 |
| `/status` | 查看当前会话、模式、工作区、运行状态完整看板 |
| `/stop` | 紧急中断当前正在执行的任务 |
| `/mcp` | 查看与管理当前生效的 MCP 服务器 |
| `/skills` | 查看当前工作区已加载的 Skill 技能列表 |

---

## ⚙️ 生产环境后台托管 (systemd)

在 Linux 服务器上创建服务文件 `/etc/systemd/system/tele-agy.service`：

```ini
[Unit]
Description=tele-agy Telegram Remote Controller
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/tele-agy
ExecStart=/path/to/tele-agy/.venv/bin/python3 run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tele-agy
sudo systemctl status tele-agy
```
