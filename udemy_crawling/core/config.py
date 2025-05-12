from dataclasses import dataclass
from uuid import UUID


def set_log_level(level: int) -> None:
    import logging

    logging.getLogger("udemy_crawling").setLevel(level)


@dataclass(frozen=True)
class ServerConfig:
    notion_token: str
    database_id: UUID
    websocket_port: int = 8765
