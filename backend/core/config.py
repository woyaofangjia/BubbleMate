"""
BubbleMate - 配置管理
"""

import os
from typing import Optional

class Config:
    """应用配置"""
    
    # API配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # 应用配置
    APP_NAME: str = "BubbleMate"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Agent配置
    MAX_MEMORY_WINDOW: int = 5  # 滑动窗口大小
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    
    # 数据路径
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    
    @classmethod
    def get_data_path(cls, filename: str) -> str:
        """获取数据文件路径"""
        return os.path.join(cls.DATA_DIR, filename)
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置"""
        if not cls.OPENAI_API_KEY:
            print("警告: OPENAI_API_KEY 未设置，请设置环境变量")
            return False
        return True

config = Config()