"""FastAPI 服务与 Telegram Long Polling 守护入口模块。

负责管理应用生命周期（数据库初始化、Telegram Application 启动与优雅退出）并暴露健康检查 API。
"""

import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI
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
    telegram_app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    setup_bot_handlers(telegram_app)

    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram Bot Long Polling is active!")

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


@app.get("/health")
async def health() -> Dict[str, str]:
    """健康检查心跳接口。

    Returns:
        Dict[str, str]: 状态响应。
    """
    return {"status": "ok"}
