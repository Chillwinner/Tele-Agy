"""FastAPI 服务与 Telegram Long Polling 守护入口模块。

负责管理应用生命周期（数据库初始化、Telegram Application 启动与优雅退出）并暴露健康检查 API。
"""

import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from telegram.ext import ApplicationBuilder, Application

from .core.config import config
from .core.database import init_db
from .bot import setup_bot_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("tele_agy")

telegram_app: Optional[Application] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理器。

    负责在服务启动时初始化数据库与 Telegram 轮询守护，在服务终止时安全释放连接。

    Args:
        app: FastAPI 实例。
    """
    global telegram_app
    logger.info("Initializing database...")
    init_db()

    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured! Telegram bot will not start polling.")
        yield
        return

    logger.info("Starting Telegram Bot application...")
    # 配置显式超时与连接池重试，防止网络长轮询死锁假死
    telegram_app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .connect_timeout(15.0)
        .read_timeout(20.0)
        .write_timeout(15.0)
        .pool_timeout(10.0)
        .build()
    )
    setup_bot_handlers(telegram_app)

    await telegram_app.initialize()
    await telegram_app.start()
    # poll_interval 设置 0.5s，read_timeout 20s，超时自动循环拉取杜绝死锁
    await telegram_app.updater.start_polling(
        drop_pending_updates=True,
        poll_interval=0.5,
        timeout=15,
        bootstrap_retries=-1
    )
    logger.info("Telegram Bot Long Polling is active with resilient timeouts!")

    yield

    logger.info("Shutting down Telegram Bot...")
    if telegram_app and telegram_app.updater:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()
    logger.info("tele-agy service stopped.")


app: FastAPI = FastAPI(
    title="tele-agy Daemon",
    description="Headless Telegram Remote Controller for Antigravity",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root() -> Dict[str, Any]:
    """服务概览接口。

    Returns:
        Dict[str, Any]: 当前运行状态与白名单配置概况。
    """
    return {
        "service": "tele-agy",
        "status": "running",
        "bot_active": bool(telegram_app and telegram_app.updater and telegram_app.updater.running),
        "allowed_users_count": len(config.ALLOWED_USER_IDS)
    }


class NotifyPayload(BaseModel):
    """主动推送给 Telegram 用户的请求结构体。"""
    text: str
    user_id: Optional[int] = None
    parse_mode: Optional[str] = "Markdown"


@app.post("/api/notify")
async def notify_telegram(payload: NotifyPayload) -> Dict[str, Any]:
    """系统级主动推送接口。

    供后台定时任务（schedule）或外部监控脚本唤醒时向授权用户 Telegram 自动推送通知。
    """
    if not telegram_app or not telegram_app.bot:
        raise HTTPException(status_code=503, detail="Telegram bot is not active")

    target_user_id = payload.user_id
    if not target_user_id:
        if config.ALLOWED_USER_IDS:
            target_user_id = config.ALLOWED_USER_IDS[0]
        else:
            raise HTTPException(status_code=400, detail="No allowed target user configured")

    try:
        await telegram_app.bot.send_message(
            chat_id=target_user_id,
            text=payload.text,
            parse_mode=payload.parse_mode
        )
    except Exception as e:
        # 降级纯文本重试
        try:
            await telegram_app.bot.send_message(
                chat_id=target_user_id,
                text=payload.text
            )
        except Exception as e2:
            logger.error(f"Failed to send Telegram notification: {e2}")
            raise HTTPException(status_code=500, detail=str(e2))

    return {"status": "success", "user_id": target_user_id}


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查心跳接口。

    Returns:
        Dict[str, str]: 状态响应。
    """
    return {"status": "ok"}
