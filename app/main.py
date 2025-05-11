import asyncio

from app.websocket_server import start_websocket_server

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
