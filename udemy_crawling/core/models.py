import re
import textwrap
from functools import cached_property
from typing import Optional, NamedTuple

from pydantic import BaseModel, Field


class TitleSet(NamedTuple):
    name: str = "Unknown"
    number: Optional[int] = None


class UdemyLecture(BaseModel):
    """Represents Udemy lecture extracted from WebSocket data."""

    raw_section: str = Field(..., description="Section")
    raw_lecture: str = Field(..., description="Lecture")
    transcripts: list[str] = Field(..., description="Lecture transcript list")
    messageId: Optional[str] = Field(None, description="Message ID for tracking")

    @cached_property
    def section(self) -> TitleSet:
        """Formats the section name to comply with Notion API constraints."""
        match = re.search(r"(\d+)", self.raw_section)
        if match:
            section_number = int(match.group(1))
            title = self.raw_section.split(":")[-1].strip()
            sanitized_title = re.sub(r"[^\w\s.-]", "", title)
            return TitleSet(sanitized_title, section_number)
        return TitleSet(self.raw_section)

    @cached_property
    def lecture(self) -> TitleSet:
        """Extracts lecture number and formatted title."""
        match = re.match(r"(\d+)\.\s*(.+)", self.raw_lecture)
        if match:
            return TitleSet(match.group(2), int(match.group(1)))
        return TitleSet(self.raw_lecture)

    @cached_property
    def chunks(self) -> list[str]:
        total_scripts = "\n".join(self.transcripts)
        return textwrap.wrap(total_scripts, width=2000)
