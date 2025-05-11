import asyncio
import json
import logging

import websockets
from websockets import ServerConnection

from app.notion_client import get_notion_transcript
from app.queue_handler import (
    add_to_queue,
    queue_worker,
)

logger = logging.getLogger("websocket_server")

connected_clients = set()


async def handler(websocket: ServerConnection):
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

                if action == "fetch_transcript":
                    lecture_number = data.get("lecture_number")
                    if not lecture_number:
                        await websocket.send(
                            json.dumps({"error": "Lecture number required"})
                        )
                        continue

                    logger.info(
                        f"🔍 Fetching transcript for Lecture {lecture_number}..."
                    )
                    notion_data = get_notion_transcript(lecture_number)

                    if notion_data:
                        await websocket.send(
                            json.dumps({"status": "success", **notion_data})
                        )
                    else:
                        await websocket.send(
                            json.dumps({"error": "Lecture isn't found in Notion"})
                        )

                elif action == "save_transcript":
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
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        logger.info(
            f"❌ Client disconnected! Active connections: {len(connected_clients)}"
        )


async def start_websocket_server():
    """Starts the WebSocket server and queue worker."""
    server = await websockets.serve(handler, "localhost", 8765)
    logger.info("🚀 WebSocket server running at ws://localhost:8765...")

    worker_task = asyncio.create_task(queue_worker())
    await asyncio.gather(server.wait_closed(), worker_task)
