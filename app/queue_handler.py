import asyncio
import logging

from app.models import UdemyLecture
from app.notion_client import create_notion_page

logger = logging.getLogger("queue_handler")

message_queue = asyncio.Queue()


async def queue_worker():
    while True:
        message_data = await message_queue.get()
        logger.info(f"🟢 Processing message: {message_data}")

        if message_data:
            try:
                transcript_data = UdemyLecture(**message_data)
                logger.info(f"✅ Parsed lecture data: {transcript_data}")

                response = create_notion_page(transcript_data)
                logger.info(f"📩 Notion API Response: {response}")

            except Exception as e:
                logger.error(f"⚠️ Error processing message: {e}")

        message_queue.task_done()


async def add_to_queue(message: dict):
    logger.info(f"🟡 Adding to queue: {message}")
    await message_queue.put(message)
