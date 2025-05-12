import asyncio
import json
from typing import TYPE_CHECKING

from websockets.exceptions import ConnectionClosed

from udemy_crawling.core.logger import logger
from udemy_crawling.queue_handler import add_to_queue, queue_worker

if TYPE_CHECKING:
    from udemy_crawling.core.config import ServerConfig
    from websockets import ServerConnection

connected_clients = set()


async def handler(websocket: "ServerConnection"):
    """Handles incoming WebSocket connections and processes messages."""
    connected_clients.add(websocket)
    logger.info(
        f"✅ New client connected! Active connections: {len(connected_clients)}"
    )

    try:
        async for message in websocket:
            logger.info(f"📩 Received message: {message}")
            try:
                data = json.loads(message)
                action = data.get("action", "")

                if action == "save_transcript":
                    await add_to_queue(data)
                    response = json.dumps(
                        {
                            "status": "success",
                            "message": "Data received and queued",
                            "messageId": data.get("messageId"),
                        }
                    )
                    await websocket.send(response)

            except json.JSONDecodeError:
                logger.error("Invalid JSON format received")
                await websocket.send(
                    json.dumps({"status": "error", "message": "Invalid JSON format"})
                )
    except ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        logger.info(
            f"❌ Client disconnected! Active connections: {len(connected_clients)}"
        )


async def start_websocket_server(config: "ServerConfig"):
    from websockets import serve
    from udemy_crawling.notion import connect_to_notion

    # Start the websocket server
    server = await serve(handler, "localhost", config.websocket_port)
    logger.info(
        f"🚀 WebSocket server running at ws://localhost:{config.websocket_port}"
    )

    # Await the async Notion connection before passing to worker
    notion_client = await connect_to_notion(config.notion_token, config.database_id)

    # Start queue worker with actual NotionClient
    worker_task = asyncio.create_task(queue_worker(notion_client))

    # Wait for server shutdown and queue worker concurrently
    await asyncio.gather(server.wait_closed(), worker_task)
