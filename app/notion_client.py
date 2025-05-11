import logging
from collections import defaultdict

import requests

from app.config import (
    HEADERS,
    settings,
)
from app.models import (
    NotionLecture,
    NotionPage,
    UdemyLecture,
)

logger = logging.getLogger("notion_client")


def existing_lecture_numbers():
    """Fetches the list of existing lecture numbers from the Notion database."""
    response = requests.post(
        f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query",
        headers=HEADERS,
    )

    if response.status_code != 200:
        logger.error(f"❌ Notion API Error: {response.status_code} - {response.json()}")
        return set()

    data = response.json()
    return {
        item["properties"]["Lecture Number"]["number"]
        for item in data.get("results", [])
        if "Lecture Number" in item["properties"]
    }


def create_notion_page(lecture: UdemyLecture):
    """Creates a new page in Notion for the given lecture if it does not already exist."""
    notion_lecture = NotionLecture.from_udemy_lecture(lecture)
    existing_numbers = existing_lecture_numbers()

    if notion_lecture.lecture_number in existing_numbers:
        logger.warning(
            f"⚠️ Skipping: Lecture {notion_lecture.lecture_number} already exists in Notion."
        )
        return None

    notion_page = NotionPage.from_notion_lecture(
        lecture=notion_lecture, database_id=settings.NOTION_DATABASE_ID
    )

    response = requests.post(
        "https://api.notion.com/v1/pages", headers=HEADERS, json=notion_page.dict()
    )

    try:
        response_data = response.json()
    except Exception as e:
        logger.error(f"❌ Notion API JSON Decode Error: {e}")
        return None

    if response.status_code != 200:
        logger.error(f"❌ Notion API Error: {response.status_code} - {response_data}")

    return response_data


def get_notion_transcript(lecture_number: int):
    """Fetches the transcript and translated subtitles from Notion using the Lecture Number."""
    query_payload = {
        "filter": {"property": "Lecture Number", "number": {"equals": lecture_number}}
    }
    response = requests.post(
        f"https://api.notion.com/v1/databases/{settings.NOTION_DATABASE_ID}/query",
        headers=HEADERS,
        json=query_payload,
    )

    if response.status_code != 200:
        logger.error(f"❌ Notion API Error: {response.status_code} - {response.json()}")
        return None

    results = response.json().get("results", [])
    if not results:
        logger.warning(f"❌ Lecture {lecture_number} not found in Notion")
        return None

    notion_page = results[0]
    page_id = notion_page["id"]

    blocks_response = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children", headers=HEADERS
    )

    if blocks_response.status_code != 200:
        logger.error(
            f"❌ Notion API Error: {blocks_response.status_code} - {blocks_response.json()}"
        )
        return None

    blocks = blocks_response.json().get("results", [])
    transcript_text_dict: dict[int, list[str]] = defaultdict(list)

    for block in blocks:
        if block.get("type") == "toggle" and block.get("has_children"):
            toggle_id = block["id"]
            children_response = requests.get(
                f"https://api.notion.com/v1/blocks/{toggle_id}/children",
                headers=HEADERS,
            )

            if children_response.status_code != 200:
                logger.error(
                    f"❌ Notion API Error: {children_response.status_code} - {children_response.json()}"
                )
                return None

            children_blocks = children_response.json().get("results", [])
            code_blocks = [
                block for block in children_blocks if block.get("type") == "code"
            ]

            if len(code_blocks) not in [1, 2]:
                return None

            for idx, code_block in enumerate(code_blocks):
                code_content = code_block["code"].get("rich_text") or code_block[
                    "code"
                ].get("text")

                if not code_content:
                    logger.warning(
                        f"⚠️ No transcript content in code block: {code_block}"
                    )
                    continue

                transcript_lines = []
                for t in code_content:
                    if "text" in t and "content" in t["text"]:
                        transcript_lines.extend(t["text"]["content"].split("\n"))

                transcript_text_dict[idx].extend(transcript_lines)

    if len(transcript_text_dict) == 0:
        logger.warning(f"⚠️ No transcript found for lecture {lecture_number}")
        return None

    return {
        "lecture_number": lecture_number,
        "original_transcript": transcript_text_dict[0],
        "translated_transcript": (
            transcript_text_dict[1] if len(transcript_text_dict[1]) > 1 else None
        ),
    }
