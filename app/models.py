import re
from typing import Optional

from pydantic import (
    BaseModel,
    Field,
)


class UdemyLecture(BaseModel):
    """Represents Udemy lecture extracted from WebSocket data."""

    section: str = Field(..., description="Section name")
    title: str = Field(..., description="Lecture title")
    transcripts: list[str] = Field(..., description="Lecture transcript list")
    messageId: Optional[str] = Field(None, description="Message ID for tracking")

    def format_section(self) -> str:
        """Formats the section name to comply with Notion API constraints."""
        match = re.search(r"(\d+)", self.section)
        if match:
            section_number = int(match.group(1))
            title = self.section.split(":")[-1].strip()
            sanitized_title = re.sub(r"[^\w\s.-]", "", title)
            return f"Section {section_number:02}. {sanitized_title}"
        return self.section

    def format_title(self) -> dict[str, Optional[str]]:
        """Extracts lecture number and formatted title."""
        match = re.match(r"(\d+)\.\s*(.+)", self.title)
        if match:
            return {
                "lecture_number": int(match.group(1)),
                "lecture_name": match.group(2),
            }
        return {
            "lecture_number": None,
            "lecture_name": self.title,
        }


class NotionLecture(BaseModel):
    """Represents a Notion-compatible lecture."""

    lecture_number: int
    lecture_name: str
    section_name: str
    transcripts: list[str]

    @staticmethod
    def chunk_transcripts(transcripts: list[str], chunk_size: int = 2000) -> list[str]:
        """Splits transcripts into 2000-character chunks (Notion API limit)."""
        chunks = []
        current_chunk = []
        current_length = 0

        for line in transcripts:
            line_length = len(line) + 1  # Include newline character
            if current_length + line_length > chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    @classmethod
    def from_udemy_lecture(cls, lecture: UdemyLecture):
        """Converts a UdemyLecture instance into a NotionLecture instance."""
        section_name = lecture.format_section()
        title_data = lecture.format_title()
        transcripts_chunked = cls.chunk_transcripts(lecture.transcripts)

        return cls(
            lecture_number=int(title_data["lecture_number"]),
            lecture_name=title_data["lecture_name"],
            section_name=section_name,
            transcripts=transcripts_chunked,
        )


class NotionPage(BaseModel):
    """Represents a Notion page request structure."""

    parent: dict[str, str]
    properties: dict[str, dict]
    children: list[dict]

    @classmethod
    def from_notion_lecture(cls, lecture: NotionLecture, database_id: str):
        """Creates a Notion page request from a NotionLecture."""
        return cls(
            parent={"database_id": database_id},
            properties={
                "Lecture Number": {"number": lecture.lecture_number},
                "Name": {"title": [{"text": {"content": lecture.lecture_name}}]},
                "Section": {"select": {"name": lecture.section_name}},
            },
            children=[
                {
                    "object": "block",
                    "type": "toggle",
                    "toggle": {
                        "rich_text": [{"text": {"content": "Transcripts"}}],
                        "children": [
                            {
                                "object": "block",
                                "type": "code",
                                "code": {
                                    "language": "markdown",
                                    "rich_text": [
                                        {"text": {"content": chunk}}
                                        for chunk in lecture.transcripts
                                    ],
                                },
                            }
                        ],
                    },
                }
            ],
        )
