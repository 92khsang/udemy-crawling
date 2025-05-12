from typing import TYPE_CHECKING, Optional

from pynotion.models import (
    DatabaseParent,
    NotionObjectIdWrapper,
    Text,
    TxMultiSelectPropertyValue,
    TxNumberPropertyValue,
    TxOptionValue,
    TxPage,
    TxRelationPropertyValue,
    TxSelectPropertyValue,
    TxTextRichText,
    TxTitlePropertyValue,
    TxToggleBlock,
    TxToggle,
    TxCodeBlock,
    TxCode,
    ProgrammingLanguage,
)

from udemy_crawling.core.logger import logger
from udemy_crawling.notion.converter import rx_page_to_lecture_page
from udemy_crawling.notion.database import (
    search_lecture_by_number,
    search_section_by_number,
    search_latest_lecture,
)
from udemy_crawling.notion.models import (
    LecturePage,
    PageTypeTag,
    LecturePagePropertyType,
)

if TYPE_CHECKING:
    from uuid import UUID
    from pynotion.models import RxPage, TxPropertyValue, TxBlock
    from udemy_crawling.core import TitleSet, UdemyLecture
    from udemy_crawling.notion.models import NotionClient


async def _fetch_latest_lecture(client: "NotionClient") -> Optional[LecturePage]:
    latest_page = await search_latest_lecture(
        client.endpoint_registry, client.dataset_id
    )
    return rx_page_to_lecture_page(latest_page) if latest_page else None


def _build_lecture_page_blocks(udemy_lecture: "UdemyLecture") -> list["TxBlock"]:
    return [
        TxToggleBlock(
            toggle=TxToggle(
                rich_text=[TxTextRichText(text=Text(content="Script"))],
                children=[
                    TxCodeBlock(
                        code=TxCode(
                            rich_text=[
                                TxTextRichText(text=Text(content=chunk))
                                for chunk in udemy_lecture.chunks
                            ],
                            language=ProgrammingLanguage.PLAIN_TEXT,
                        )
                    )
                ],
            )
        )
    ]


async def _create_page(
    client: "NotionClient",
    title_set: "TitleSet",
    page_type_tag: PageTypeTag,
    prev_relation_id: Optional["UUID"] = None,
    parent_relation_id: Optional["UUID"] = None,
    children: list["TxBlock"] = None,
) -> "RxPage":

    endpoint = client.endpoint_registry.pages

    properties: dict[str, "TxPropertyValue"] = {
        LecturePagePropertyType.NAME: TxTitlePropertyValue(
            title=[TxTextRichText(text=Text(content=title_set.name))]
        ),
        LecturePagePropertyType.TAG: TxMultiSelectPropertyValue(
            multi_select=[TxOptionValue(name=page_type_tag.value)]
        ),
        LecturePagePropertyType.NUMBER: TxNumberPropertyValue(number=title_set.number),
    }

    if client.template_page and client.template_page.properties.version:
        properties[LecturePagePropertyType.VERSION] = TxSelectPropertyValue(
            select=TxOptionValue(name=client.template_page.properties.version)
        )

    if prev_relation_id:
        properties[LecturePagePropertyType.PREV_RELATION] = TxRelationPropertyValue(
            relation=[NotionObjectIdWrapper(id=prev_relation_id)]
        )

    if parent_relation_id:
        properties[LecturePagePropertyType.PARENT_RELATION] = TxRelationPropertyValue(
            relation=[NotionObjectIdWrapper(id=parent_relation_id)]
        )

    tx_page = TxPage(
        parent=DatabaseParent(database_id=client.dataset_id),
        icon=client.template_page.icon,
        properties=properties,
        children=children,
    )

    logger.debug(f"Creating page: {tx_page.model_dump(mode='json')}")

    return await endpoint.create_page(tx_page)


async def _create_section_page(
    client: "NotionClient", section: "TitleSet"
) -> LecturePage:
    if TYPE_CHECKING:
        section_page: "RxPage"

    section_page = await search_section_by_number(
        client.endpoint_registry, client.dataset_id, section.number
    )

    if section_page is None:
        logger.debug(f"Section page not found for {section}")
        latest_page: Optional[LecturePage] = await _fetch_latest_lecture(client)

        section_page = await _create_page(
            client,
            section,
            PageTypeTag.SECTION,
            latest_page.id if latest_page else None,
        )

        logger.debug(f"Created section page: {section_page.model_dump(mode='json')}")
    else:
        logger.debug(f"Section page found for {section}")

    return rx_page_to_lecture_page(section_page)


async def create_lecture_page(client: "NotionClient", udemy_lecture: "UdemyLecture"):
    found_lecture = await search_lecture_by_number(
        client.endpoint_registry, client.dataset_id, udemy_lecture.lecture.number
    )

    if found_lecture:
        logger.debug(f"Found lecture page for {found_lecture.model_dump(mode='json')}")
        return

    section_page: LecturePage = await _create_section_page(
        client, udemy_lecture.section
    )

    latest_page: Optional[LecturePage] = await _fetch_latest_lecture(client)
    if latest_page and latest_page.properties.parent_relation_id != section_page.id:
        latest_page = section_page

    created_page = await _create_page(
        client,
        udemy_lecture.lecture,
        PageTypeTag.LECTURE,
        latest_page.id if latest_page else None,
        section_page.id,
        children=_build_lecture_page_blocks(udemy_lecture),
    )

    logger.debug(f"Created lecture page: {created_page.model_dump(mode='json')}")
