"""配置文件 - 所有模块共享"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 数据库
    DATABASE_URL: str = "sqlite:///./judicial.db"
    
    # LLM API Keys (各成员根据需要使用)
    ZHIPU_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    
    class Config:
        env_file = ".env"


settings = Settings()
