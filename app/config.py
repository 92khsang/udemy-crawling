import logging

from pydantic import (
    Field,
    ValidationError,
)
from pydantic_settings import BaseSettings

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("config")


class Settings(BaseSettings):
    NOTION_API_TOKEN: str = Field(..., strict=True, description="Notion API Token")
    NOTION_DATABASE_ID: str = Field(..., strict=True, description="Notion Database ID")

    class Config:
        env_file = ".env"


try:
    settings = Settings()
    logger.info("✅ Configuration loaded successfully.")
except ValidationError as e:
    logger.error(f"❌ Configuration Error: {e}")
    exit(1)

HEADERS = {
    "Authorization": f"Bearer {settings.NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2021-08-16",
}
