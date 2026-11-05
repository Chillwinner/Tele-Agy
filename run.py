"""服务启动入口脚本。"""

import uvicorn
from tele_agy.core.config import config

if __name__ == "__main__":
    uvicorn.run(
        "tele_agy.app:app",
        host=config.FASTAPI_HOST,
        port=config.FASTAPI_PORT,
        reload=False
    )
