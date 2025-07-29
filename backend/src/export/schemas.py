"""Export format schemas and validation models."""

from enum import Enum

from pydantic import BaseModel


class ExportFormat(str, Enum):
    """Supported export formats for quiz files."""

    PDF = "pdf"
    QTI_XML = "qti_xml"


class ExportMetadata(BaseModel):
    """Metadata for quiz export operations."""

    quiz_id: str
    quiz_title: str
    question_count: int
    export_format: ExportFormat


class PDFExportOptions(BaseModel):
    """Configuration options for PDF export."""

    include_instructions: bool = True
    page_format: str = "A4"  # A4, Letter
    font_size: int = 12


class QTIExportOptions(BaseModel):
    """Configuration options for QTI XML export."""

    qti_version: str = "2.1"
    include_metadata: bool = True
    points_per_question: float = 1.0
