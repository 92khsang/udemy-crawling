import argparse
import asyncio
import logging

from udemy_crawling import start_websocket_server, ServerConfig, set_log_level


def parse_config() -> ServerConfig:
    parser = argparse.ArgumentParser(
        description="Starts the WebSocket server and queue worker."
    )

    parser.add_argument("--notion-token", type=str, required=True)
    parser.add_argument("--database-id", type=str, required=True)
    parser.add_argument("--websocket-port", type=int, default=8765)

    args = parser.parse_args()

    return ServerConfig(
        notion_token=args.notion_token,
        database_id=args.database_id,
        websocket_port=args.websocket_port,
    )


if __name__ == "__main__":
    set_log_level(logging.DEBUG)

    config = parse_config()
    asyncio.run(start_websocket_server(config))
