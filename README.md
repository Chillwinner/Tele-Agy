# Tele-Agy 🛸

> **Empower Antigravity (`agy`) CLI with Headless Telegram Remote Control — Leveraging Your Google Account Pro / Subscriber Quota Instead of Costly API Tokens!**

---

## ⚡ Key Highlight: Zero API Bill — Use Your Pro / Advanced Subscription Quota!

> [!IMPORTANT]
> **No Pay-Per-Token API Charges!**  
> Most LLM tools and bridges force developers to pay per prompt/completion via billing APIs (e.g., Google Cloud Vertex AI, OpenAI Platform).  
> **Tele-Agy takes a fundamentally different approach:**  
> It communicates directly with your locally authenticated **Antigravity (`agy`) CLI binary**, utilizing the **Google Pro / Advanced subscriber subscription quota** linked to your personal Google account.  
> - **Zero API Bills**: Enjoy high-limit, state-of-the-art models without worrying about token meter drain.
> - **Headless Linux Server Ready**: Runs completely in the background on remote VPS/bare-metal servers without requiring any desktop GUI or Electron environment.

---

## 🌟 Overview

**Tele-Agy** is an enterprise-grade, high-performance remote control bridge that bridges your mobile Telegram app to your server's local `agy` Agent. It gives you full command over your AI engineering assistant from anywhere in the world — whether you're commuting, away from your desk, or monitoring long-running builds on remote headless machines.

### Architecture Highlights

```
  ┌─────────────────┐             Telegram Bot API
  │  Telegram App   │ ◄──────────────────────────────────────────────┐
  │ (User on Mobile)│ ──────────────────────────────────────────┐    │
  └─────────────────┘                                           │    │
                                                                ▼    │
┌────────────────────────────────────────────────────────────────────┴┐
│                           Tele-Agy Daemon                           │
│                                                                     │
│  ┌───────────────────────────────┐  ┌────────────────────────────┐  │
│  │   Out-of-Band Control Plane   │  │   Workload / Stream Engine │  │
│  │   (Non-blocking IPMI/BMC)     │  │   (Throttled Markdown)     │  │
│  │   /list, /status, /power, /stop│ │   Real-time Thought & Delta│  │
│  └───────────────────────────────┘  └────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────┐  ┌────────────────────────────┐  │
│  │   FastAPI Webhook Service     │  │   Local SQLite Database    │  │
│  │   /api/notify (Alerts/Cron)   │  │   User States & Workspaces │  │
│  └───────────────────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ stdio NDJSON Stream
                                  ▼
                    ┌───────────────────────────┐
                    │      Antigravity CLI      │
                    │      (`agy` Process)      │
                    └───────────────────────────┘
```

---

## ✨ Features

- **💎 Pro Quota First**: Seamlessly consumes your personal/Google One Pro plan quota via local OAuth tokens.
- **🚀 Out-of-Band Management (BMC/IPMI Architecture)**:
  - System control commands (`/list`, `/status`, `/power`, `/stop`, mode switching, button callbacks) run completely independent of heavy workloads (`block=False`).
  - Even if `agy` is running a massive build, stress test, or reasoning chain, your control panel responds in milliseconds without deadlocks.
- **🌊 Anti-Flood Throttled Streaming**:
  - Live typing deltas, thinking thoughts (`<thought>`), and tool calls are aggregated and rate-limited with an adaptive 1.2s debounce buffer.
  - Guarantees smooth streaming while strictly preventing Telegram `429 Too Many Requests` rate limit bans.
- **🛡️ Global Power Switch & Hardware Kill**:
  - `/power` or `/off` instantly kills active `agy` child processes and pauses listening, achieving zero CPU/RAM footprint when idle.
- **🗂️ Trajectory-Aware Conversation Management**:
  - Automatically scans existing CLI trajectory databases (`~/.gemini/antigravity-cli/`).
  - `/list` presents genuine titles and bound workspace directories with **dynamic pagination** (`⬅️ Prev`, `📄 Page`, `Next ➡️`).
- **⏰ Smart Async Background Scheduling**:
  - Compatible with `/schedule` and long-term recurring cron timers.
  - Built-in `/api/notify` endpoint allows background tasks to push notifications straight back to your phone upon completion.
- **🔒 Whitelist-Enforced Security**:
  - Hardened authorization: Only Telegram IDs configured in the local `.env` whitelist can interact with or view the bot.

---

## 📋 Requirements

- **Operating System**: Linux (Ubuntu, Debian, CentOS, Arch) or macOS.
- **Python**: Python 3.9, 3.10, 3.11, or 3.12.
- **Antigravity CLI**: `agy` installed and authenticated (`agy --version`).
- **Telegram Bot Token**: Created via [@BotFather](https://t.me/BotFather).

---

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/Chillwinner/Tele-Agy.git
cd Tele-Agy
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the provided example template to your private `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your preferred editor:

```ini
# Telegram Bot API Token obtained from @BotFather
TELEGRAM_BOT_TOKEN="123456789:AAXYZ...your_bot_token"

# Comma-separated Telegram User IDs allowed to control the machine
ALLOWED_USER_IDS="8921122625"

# Path to agy binary (Default matches standard Antigravity CLI path)
AGY_BIN_PATH="agy"

# Default project directory for newly initialized conversations
DEFAULT_WORKSPACE="/home/user/workspace"

# Host & Port for Tele-Agy internal FastAPI webhook daemon
HOST="127.0.0.1"
PORT=8080
```

> [!NOTE]
> `.env` is strictly ignored by `.gitignore` and will never be committed or leaked to git.

### 4. Verify Local `agy` Login

Make sure your server is logged in to your Google Account with Pro/Advanced subscription:

```bash
agy --version
agy "Hello, reply with OK"
```

### 5. Launch Tele-Agy

```bash
python run.py
```

You should see logs indicating database initialization and polling activation:
```text
INFO:     Started server process [...]
INFO:     Telegram Bot Long Polling is active with resilient timeouts!
INFO:     Uvicorn running on http://127.0.0.1:8080
```

---

## 🎮 Telegram Commands & Usage

Open your Telegram bot and use either the native Menu button or type commands:

| Command | Description |
| :--- | :--- |
| `/start` | Open the comprehensive control dashboard with interactive buttons. |
| `/status` | View global health, active model, workspace path, and power status. |
| `/list` | Browse historical conversations with interactive pagination buttons. |
| `/new [path]` | Start a fresh trajectory session (optionally in a custom folder). |
| `/cd <path>` | Switch the active workspace working directory for the current session. |
| `/mode` | Toggle between **Plan** (read-only architectural planning) and **Build** (full execution). |
| `/model` | Switch between Gemini Flash, Claude Sonnet, Opus Thinking, etc. |
| `/policy` | Configure security policy: **Auto** (unattended), **Sandbox**, or **Review**. |
| `/power` | Toggle global power switch (**Power ON** / **Power OFF**). |
| `/stop` | Emergency interrupt: immediately terminates the active running task. |

---

## 🛠️ Production Deployment (systemd Service)

To keep Tele-Agy running continuously across reboots on a headless Linux server, create a `systemd` unit file:

```bash
sudo tee /etc/systemd/system/tele-agy.service <<EOF
[Unit]
Description=Tele-Agy Remote Control Gateway
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/python $(pwd)/run.py
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tele-agy
sudo systemctl status tele-agy
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
