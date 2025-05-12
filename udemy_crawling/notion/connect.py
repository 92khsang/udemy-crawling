from typing import TYPE_CHECKING

from pynotion import EndPointRegistry

from udemy_crawling.notion.models import NotionClient

if TYPE_CHECKING:
    from uuid import UUID


async def connect_to_notion(token: str, dataset_id: "UUID") -> "NotionClient":
    from udemy_crawling.notion.database import search_template

    py_notion = EndPointRegistry(token, async_mode=True)
    pagination = await search_template(py_notion, dataset_id)

    template_page = None
    if len(pagination.results) > 0:
        from udemy_crawling.notion.converter import rx_page_to_lecture_page

        template_rx_page = pagination.results[0]
        template_page = rx_page_to_lecture_page(template_rx_page)

    return NotionClient(py_notion, dataset_id, template_page)
