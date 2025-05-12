from typing import TYPE_CHECKING, Any, Optional

from udemy_crawling.notion.models import (
    LecturePage,
    LecturePagePropertySet,
    LecturePagePropertyType,
)

if TYPE_CHECKING:
    from uuid import UUID
    from pynotion.models import RxPage, RxPropertyValue


def _extract_property_value(value: Optional["RxPropertyValue"]) -> Any:
    """
    Extract the raw value object from a Notion RxPropertyValue, based on its type.
    """
    if not value:
        return None
    return getattr(value, value.type, None)


def _extract_option_value(value: Optional["RxPropertyValue"]) -> Optional[str]:
    """
    Extract the 'name' field from a select/single option property value.
    """
    extracted = _extract_property_value(value)
    return getattr(extracted, "name", None) if extracted else None


def _extract_option_values(value: Optional["RxPropertyValue"]) -> Optional[list[str]]:
    """
    Extract the list of 'name' fields from a multi-select property value.
    """
    extracted = _extract_property_value(value)
    if not extracted:
        return None
    return [getattr(option, "name", None) for option in extracted]


def _extract_relation_ids(value: Optional["RxPropertyValue"]) -> Optional[list["UUID"]]:
    """
    Extract the list of UUIDs from a relation property value.
    """
    extracted = _extract_property_value(value)
    if not extracted:
        return None
    return [option.id for option in extracted]


def rx_page_to_lecture_page(rx_page: "RxPage") -> LecturePage:
    """
    Convert a Notion RxPage object into a structured LecturePage domain model.
    """
    get_prop = rx_page.properties.get  # shorthand

    # Safely extract property values using property keys
    properties = LecturePagePropertySet(
        version=_extract_option_value(get_prop(LecturePagePropertyType.VERSION)),
        status=_extract_option_value(get_prop(LecturePagePropertyType.STATUS)),
        tag=_extract_option_values(get_prop(LecturePagePropertyType.TAG)),
        number=_extract_property_value(get_prop(LecturePagePropertyType.NUMBER)),
        prev_relation_id=(
            (
                _ids := _extract_relation_ids(
                    get_prop(LecturePagePropertyType.PREV_RELATION)
                )
            )
            and _ids[0]
        ),
        parent_relation_id=(
            (
                _ids := _extract_relation_ids(
                    get_prop(LecturePagePropertyType.PARENT_RELATION)
                )
            )
            and _ids[0]
        ),
    )

    return LecturePage(
        id=rx_page.id,
        properties=properties,
        icon=rx_page.icon,
    )
