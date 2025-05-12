import asyncio
from typing import TYPE_CHECKING

from udemy_crawling.core import logger, UdemyLecture
from udemy_crawling.notion.creator import create_lecture_page

if TYPE_CHECKING:
    from udemy_crawling.notion.models import NotionClient

message_queue = asyncio.Queue()


async def queue_worker(client: "NotionClient"):
    while True:
        message_data = await message_queue.get()
        logger.info(f"🟢 Processing message: {message_data}")

        if message_data:
            try:
                udemy_lecture = UdemyLecture(**message_data)
                logger.info(f"✅ Parsed udemy lecture: {udemy_lecture}")

                await create_lecture_page(client, udemy_lecture)
                logger.info(f"📩 Successfully created page for {udemy_lecture}")

            except Exception as e:
                logger.error(f"⚠️ Error processing message: {e}")

        message_queue.task_done()


async def add_to_queue(message: dict):
    logger.info(f"🟡 Adding to queue: {message}")
    await message_queue.put(message)
