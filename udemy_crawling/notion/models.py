from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from pynotion import EndPointRegistry
from pynotion.models import SingleEmoji, CustomEmoji


class PageTypeTag(str, Enum):
    SECTION = "Section"
    LECTURE = "Lecture"
    TEMPLATE = "Template"


class LecturePagePropertyType(str, Enum):
    NAME = "Name"
    VERSION = "Version"
    TAG = "Tag"
    NUMBER = "Number"
    STATUS = "Status"
    PREV_RELATION = "Prev"
    PARENT_RELATION = "Parent"


class LecturePagePropertySet(BaseModel):
    version: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[list[str]] = None
    number: Optional[int] = None
    prev_relation_id: Optional[UUID] = None
    parent_relation_id: Optional[UUID] = None


class LecturePage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    properties: LecturePagePropertySet
    icon: Optional[SingleEmoji | CustomEmoji] = None


@dataclass(frozen=True)
class NotionClient:
    endpoint_registry: EndPointRegistry
    dataset_id: UUID
    template_page: "LecturePage"
