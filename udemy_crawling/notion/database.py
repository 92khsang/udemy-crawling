from typing import TYPE_CHECKING, Optional

from pynotion import EndPointRegistry
from pynotion.models import (
    PropertySort,
    TxPagination,
    AndPropertyFilter,
    MultiSelectFilter,
    MultiSelectCondition,
    NumberFilter,
    NumberCondition,
    SortDirection,
)

from udemy_crawling.notion.models import PageTypeTag, LecturePagePropertyType

if TYPE_CHECKING:
    from uuid import UUID
    from pynotion.models import (
        RxPage,
        PropertyFilter,
        PageOrDatabasePagination,
    )


def _build_tag_filter(page_type_tag: PageTypeTag) -> "MultiSelectFilter":
    return MultiSelectFilter(
        property=LecturePagePropertyType.TAG,
        multi_select=MultiSelectCondition(contains=page_type_tag.value),
    )


def _build_number_filter(number: int) -> "NumberFilter":
    return NumberFilter(
        property=LecturePagePropertyType.NUMBER,
        number=NumberCondition(equals=number),
    )


async def _search_from_database(
    endpoint_registry: EndPointRegistry,
    database_id: "UUID",
    property_filter: Optional["PropertyFilter"] = None,
    sort: Optional[list[PropertySort]] = None,
    pagination: Optional[TxPagination] = None,
) -> "PageOrDatabasePagination":
    endpoint = endpoint_registry.databases
    return await endpoint.query_databases(
        database_id=database_id,
        property_filter=property_filter,
        sort=sort,
        pagination=pagination,
    )


async def search_template(
    endpoint_registry: EndPointRegistry,
    database_id: "UUID",
) -> "PageOrDatabasePagination":
    return await _search_from_database(
        endpoint_registry,
        database_id,
        property_filter=_build_tag_filter(PageTypeTag.TEMPLATE),
    )


async def search_lecture_by_number(
    endpoint_registry: EndPointRegistry,
    database_id: "UUID",
    lecture_number: int,
) -> Optional["RxPage"]:
    lectures: "PageOrDatabasePagination" = await _search_from_database(
        endpoint_registry,
        database_id,
        property_filter=AndPropertyFilter(
            filters=[
                _build_tag_filter(PageTypeTag.LECTURE),
                _build_number_filter(lecture_number),
            ],
        ),
    )

    return lectures.results[0] if lectures.results else None


async def search_latest_lecture(
    endpoint_registry: EndPointRegistry, database_id: "UUID"
) -> Optional["RxPage"]:
    lectures: "PageOrDatabasePagination" = await _search_from_database(
        endpoint_registry,
        database_id,
        property_filter=_build_tag_filter(PageTypeTag.LECTURE),
        sort=[PropertySort(property="Number", direction=SortDirection.DESCENDING)],
        pagination=TxPagination(page_size=1),
    )

    return lectures.results[0] if lectures.results else None


async def search_section_by_number(
    endpoint_registry: EndPointRegistry,
    database_id: "UUID",
    section_number: int,
) -> Optional["RxPage"]:
    sections: "PageOrDatabasePagination" = await _search_from_database(
        endpoint_registry,
        database_id,
        property_filter=AndPropertyFilter(
            filters=[
                _build_tag_filter(PageTypeTag.SECTION),
                _build_number_filter(section_number),
            ]
        ),
    )

    return sections.results[0] if sections.results else None
