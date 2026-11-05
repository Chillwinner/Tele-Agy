"""系统配置管理模块。

负责从环境变量和 .env 文件中加载运行配置，并提供全局统一的配置对象。
"""

import os
from typing import List
from dotenv import load_dotenv

# 加载当前目录下的 .env 文件
load_dotenv()


class Config:
    """全局配置类。

    Attributes:
        TELEGRAM_BOT_TOKEN: Telegram Bot 访问凭据。
        ALLOWED_USER_IDS: 授权访问的 Telegram User ID 白名单列表。
        DEFAULT_WORKSPACE: 未指定工作区时的默认工作目录。
        AGY_BIN_PATH: Antigravity CLI (agy) 可执行文件路径。
        FASTAPI_HOST: FastAPI 服务监听地址。
        FASTAPI_PORT: FastAPI 服务监听端口。
        DATABASE_PATH: SQLite 数据库存储路径。
    """

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    _allowed_raw: str = os.getenv("ALLOWED_USER_IDS", "")
    ALLOWED_USER_IDS: List[int] = [
        int(uid.strip())
        for uid in _allowed_raw.split(",")
        if uid.strip().isdigit()
    ]

    DEFAULT_WORKSPACE: str = os.getenv("DEFAULT_WORKSPACE", os.getcwd()).strip()
    AGY_BIN_PATH: str = os.getenv("AGY_BIN_PATH", "agy").strip()
    FASTAPI_HOST: str = os.getenv("FASTAPI_HOST", "127.0.0.1").strip()
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8080"))
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join(os.getcwd(), "tele_agy.db")).strip()


config = Config()
