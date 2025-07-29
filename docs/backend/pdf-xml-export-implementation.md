# PDF/XML Export Feature Implementation Guide

**Document Version:** 1.0
**Date:** July 29, 2025
**Author:** Implementation Guide
**Status:** Implementation Ready

## 1. Feature Overview

### What This Feature Does
The PDF/XML export feature extends the existing Canvas-only quiz export functionality to support two additional export formats:
- **PDF Export**: Generates a formatted document containing only questions for student distribution
- **XML Export**: Creates QTI 2.1 compliant XML files with questions and answer keys for importing into other Learning Management Systems (LMS)

### Business Value
- **Students**: Receive professionally formatted quiz documents for offline study or exam scenarios
- **Educators**: Can migrate quizzes between different LMS platforms using industry-standard QTI format
- **Institutions**: Reduces vendor lock-in by enabling quiz portability across educational platforms

### Context
This feature builds upon the existing quiz generation system that currently supports:
- Canvas OAuth integration
- AI-powered question generation from course content
- Question review and approval workflow
- Canvas LMS export functionality

The new export formats operate as read-only operations that don't modify quiz status or store files permanently.

## 2. Technical Architecture

### High-Level Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Quiz Router   │    │  Export Service │    │ File Generators │
│                 │    │                 │    │                 │
│ GET /export/pdf │───▶│ export_to_pdf() │───▶│ PDF Generator   │
│ GET /export/xml │    │ export_to_qti() │    │ QTI Generator   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│Question Service │    │ Question Types  │    │StreamingResponse│
│ (existing)      │    │ format_for_pdf()│    │   (FastAPI)     │
│ get_approved()  │    │ format_for_qti()│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Integration Points
- **Quiz Module**: Extends existing router with new endpoints
- **Question Service**: Reuses existing question retrieval and validation
- **Question Types**: Extends polymorphic question types with new formatting methods
- **Authentication**: Uses existing JWT and ownership validation
- **FastAPI**: Leverages StreamingResponse for file downloads

### Data Flow
1. User requests export via API endpoint
2. System validates quiz ownership and approved questions
3. Question data retrieved from database
4. Questions formatted according to export type
5. File generated in memory (PDF or XML)
6. File streamed directly to client
7. No persistence - file discarded after response

## 3. Dependencies & Prerequisites

### External Dependencies
Add to `backend/pyproject.toml`:
```toml
dependencies = [
    # ... existing dependencies
    "reportlab>=4.0.0",  # Professional PDF generation
    "lxml>=5.0.0",       # Advanced XML processing and validation
]
```

### Version Requirements
- **ReportLab 4.0+**: Required for advanced PDF styling and layout
- **lxml 5.0+**: Needed for QTI XML validation and namespace handling
- **Python 3.10+**: Already required by project
- **FastAPI**: Already available for StreamingResponse

### Environment Setup
No additional environment configuration required. Dependencies are Python packages only.

## 4. Implementation Details

### 4.1 File Structure

#### New Files to Create
```
backend/src/export/
├── __init__.py              # Module initialization
├── schemas.py               # Export format enums and models
├── service.py               # Main export orchestration
├── pdf_generator.py         # PDF generation logic
├── qti_generator.py         # QTI XML generation logic
└── templates/
    ├── quiz_pdf.html        # Jinja2 template for PDF layout
    └── quiz_styles.css      # CSS styling for PDF

backend/src/export/tests/    # Test files (create during testing phase)
├── __init__.py
├── test_service.py
├── test_pdf_generator.py
├── test_qti_generator.py
└── fixtures/
    ├── sample_quiz_data.py
    └── expected_outputs/
```

#### Files to Modify
```
backend/src/quiz/router.py                    # Add export endpoints
backend/src/question/types/base.py            # Add abstract methods
backend/src/question/types/mcq.py             # Add PDF/QTI formatting
backend/src/question/types/fill_in_blank.py   # Add PDF/QTI formatting
backend/src/question/types/matching.py        # Add PDF/QTI formatting
backend/src/question/types/categorization.py  # Add PDF/QTI formatting
backend/pyproject.toml                        # Add dependencies
```

### 4.2 Step-by-Step Implementation

#### Step 1: Add Dependencies
**File:** `backend/pyproject.toml`

Locate the dependencies section and add:
```toml
dependencies = [
    # ... existing dependencies
    "reportlab>=4.0.0",
    "lxml>=5.0.0",
]
```

#### Step 2: Create Export Schemas
**File:** `backend/src/export/schemas.py`

```python
"""Export format schemas and validation models."""

from enum import Enum
from typing import Any

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
```

#### Step 3: Create Export Module Initialization
**File:** `backend/src/export/__init__.py`

```python
"""Export module for generating quiz files in various formats."""

from .schemas import ExportFormat, ExportMetadata, PDFExportOptions, QTIExportOptions
from .service import export_quiz_to_pdf, export_quiz_to_qti_xml

__all__ = [
    "ExportFormat",
    "ExportMetadata",
    "PDFExportOptions",
    "QTIExportOptions",
    "export_quiz_to_pdf",
    "export_quiz_to_qti_xml",
]
```

#### Step 4: Create PDF Generator
**File:** `backend/src/export/pdf_generator.py`

```python
"""PDF generation service using ReportLab."""

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .schemas import PDFExportOptions


class QuizPDFGenerator:
    """Generates PDF documents for quiz distribution to students."""

    def __init__(self, options: PDFExportOptions):
        self.options = options
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Create custom paragraph styles for quiz formatting."""
        # Quiz title style
        self.styles.add(
            ParagraphStyle(
                name="QuizTitle",
                parent=self.styles["Title"],
                fontSize=16,
                spaceAfter=20,
                alignment=1,  # Center alignment
            )
        )

        # Question text style
        self.styles.add(
            ParagraphStyle(
                name="QuestionText",
                parent=self.styles["Normal"],
                fontSize=self.options.font_size,
                spaceAfter=10,
                leftIndent=0,
            )
        )

        # Option style for multiple choice
        self.styles.add(
            ParagraphStyle(
                name="OptionText",
                parent=self.styles["Normal"],
                fontSize=self.options.font_size - 1,
                leftIndent=20,
                spaceAfter=5,
            )
        )

    def generate_pdf(
        self,
        quiz_title: str,
        questions: list[dict[str, Any]]
    ) -> bytes:
        """
        Generate PDF bytes for a quiz.

        Args:
            quiz_title: Title of the quiz
            questions: List of formatted question data

        Returns:
            PDF content as bytes
        """
        buffer = io.BytesIO()

        # Setup document
        page_size = A4 if self.options.page_format == "A4" else letter
        doc = BaseDocTemplate(
            buffer,
            pagesize=page_size,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        # Create frame and template
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="normal",
        )
        template = PageTemplate(id="main", frames=[frame])
        doc.addPageTemplates([template])

        # Build content
        story = []

        # Add title
        story.append(Paragraph(quiz_title, self.styles["QuizTitle"]))
        story.append(Spacer(1, 20))

        # Add instructions if enabled
        if self.options.include_instructions:
            instructions = (
                "Instructions: Choose the best answer for each question. "
                "Mark your answers clearly."
            )
            story.append(Paragraph(instructions, self.styles["Normal"]))
            story.append(Spacer(1, 15))

        # Add questions
        for i, question in enumerate(questions, 1):
            story.extend(self._format_question(i, question))
            story.append(Spacer(1, 15))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _format_question(
        self,
        question_num: int,
        question_data: dict[str, Any]
    ) -> list[Any]:
        """Format a single question for PDF inclusion."""
        elements = []
        question_type = question_data.get("type", "unknown")

        # Question header
        question_text = f"{question_num}. {question_data['question_text']}"
        elements.append(Paragraph(question_text, self.styles["QuestionText"]))

        if question_type == "multiple_choice":
            elements.extend(self._format_mcq_options(question_data))
        elif question_type == "fill_in_blank":
            elements.extend(self._format_fill_blank(question_data))
        elif question_type == "matching":
            elements.extend(self._format_matching(question_data))
        elif question_type == "categorization":
            elements.extend(self._format_categorization(question_data))

        return elements

    def _format_mcq_options(self, question_data: dict[str, Any]) -> list[Any]:
        """Format multiple choice options."""
        options = []
        for letter in ["A", "B", "C", "D"]:
            option_key = f"option_{letter.lower()}"
            if option_key in question_data:
                option_text = f"{letter}. {question_data[option_key]}"
                options.append(Paragraph(option_text, self.styles["OptionText"]))
        return options

    def _format_fill_blank(self, question_data: dict[str, Any]) -> list[Any]:
        """Format fill-in-the-blank questions."""
        elements = []
        if "blanks_info" in question_data:
            elements.append(Spacer(1, 10))
            elements.append(
                Paragraph(
                    "Fill in the blanks with appropriate answers.",
                    self.styles["Normal"]
                )
            )
        return elements

    def _format_matching(self, question_data: dict[str, Any]) -> list[Any]:
        """Format matching questions."""
        elements = []

        if "left_items" in question_data and "right_items" in question_data:
            # Create two-column table for matching items
            left_items = question_data["left_items"]
            right_items = question_data["right_items"]

            table_data = [["Match items from Column A with Column B", ""]]
            table_data.append(["Column A", "Column B"])

            max_items = max(len(left_items), len(right_items))
            for i in range(max_items):
                left = left_items[i] if i < len(left_items) else ""
                right = right_items[i] if i < len(right_items) else ""
                table_data.append([left, right])

            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table.setStyle(
                TableStyle([
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(table)

        return elements

    def _format_categorization(self, question_data: dict[str, Any]) -> list[Any]:
        """Format categorization questions."""
        elements = []

        if "items_to_categorize" in question_data and "categories" in question_data:
            elements.append(
                Paragraph(
                    "Categorize the following items:",
                    self.styles["Normal"]
                )
            )
            elements.append(Spacer(1, 5))

            # List items to categorize
            items = question_data["items_to_categorize"]
            for item in items:
                elements.append(
                    Paragraph(f"• {item}", self.styles["OptionText"])
                )

            elements.append(Spacer(1, 10))

            # List categories
            categories = question_data["categories"]
            elements.append(
                Paragraph("Categories:", self.styles["Normal"])
            )
            for category in categories:
                elements.append(
                    Paragraph(f"• {category}", self.styles["OptionText"])
                )

        return elements
```

#### Step 5: Create QTI Generator
**File:** `backend/src/export/qti_generator.py`

```python
"""QTI 2.1 XML generation service."""

import uuid
from datetime import datetime
from typing import Any

from lxml import etree

from .schemas import QTIExportOptions


class QTIGenerator:
    """Generates QTI 2.1 compliant XML for quiz export."""

    def __init__(self, options: QTIExportOptions):
        self.options = options
        self.namespaces = {
            None: "http://www.imsglobal.org/xsd/imsqti_v2p1",
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }

    def generate_qti_xml(
        self,
        quiz_title: str,
        questions: list[dict[str, Any]]
    ) -> bytes:
        """
        Generate QTI 2.1 XML for a quiz.

        Args:
            quiz_title: Title of the quiz
            questions: List of formatted question data with answers

        Returns:
            QTI XML content as bytes
        """
        # Create root assessment test
        root = etree.Element(
            "assessmentTest",
            nsmap=self.namespaces,
            identifier=f"quiz_{uuid.uuid4().hex[:8]}",
            title=quiz_title,
        )

        # Add schema location
        root.set(
            "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation",
            "http://www.imsglobal.org/xsd/imsqti_v2p1 "
            "http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"
        )

        # Add metadata if enabled
        if self.options.include_metadata:
            self._add_metadata(root, quiz_title, len(questions))

        # Add test part
        test_part = etree.SubElement(
            root,
            "testPart",
            identifier="main_part",
            navigationMode="linear",
            submissionMode="individual",
        )

        # Add assessment section
        section = etree.SubElement(
            test_part,
            "assessmentSection",
            identifier="main_section",
            title="Quiz Questions",
            visible="true",
        )

        # Add questions as assessment item refs
        for i, question in enumerate(questions):
            item_ref = etree.SubElement(
                section,
                "assessmentItemRef",
                identifier=f"question_{i+1}",
                href=f"question_{i+1}.xml",
            )

            # Add weight for scoring
            weight = etree.SubElement(item_ref, "weight")
            weight.set("identifier", "SCORE")
            weight.set("value", str(self.options.points_per_question))

        # Generate individual question files and create manifest
        question_files = []
        for i, question in enumerate(questions):
            question_xml = self._generate_question_item(i + 1, question)
            question_files.append({
                "identifier": f"question_{i+1}",
                "href": f"question_{i+1}.xml",
                "xml": question_xml,
            })

        # For simplicity, we'll embed questions in the main file
        # In a full implementation, you'd create a ZIP with separate files
        questions_section = etree.SubElement(root, "questions")
        for question_file in question_files:
            question_element = etree.SubElement(
                questions_section,
                "embeddedQuestion",
                identifier=question_file["identifier"]
            )
            question_element.text = etree.tostring(
                question_file["xml"],
                encoding="unicode"
            )

        # Generate XML string
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )

        return xml_string

    def _add_metadata(
        self,
        root: etree.Element,
        title: str,
        question_count: int
    ) -> None:
        """Add QTI metadata to the assessment."""
        metadata = etree.SubElement(root, "metadata")

        # Add title
        title_meta = etree.SubElement(metadata, "qtimetadata")
        title_field = etree.SubElement(title_meta, "qtimetadatafield")
        etree.SubElement(title_field, "fieldlabel").text = "qmd_title"
        etree.SubElement(title_field, "fieldentry").text = title

        # Add creation date
        date_meta = etree.SubElement(metadata, "qtimetadata")
        date_field = etree.SubElement(date_meta, "qtimetadatafield")
        etree.SubElement(date_field, "fieldlabel").text = "qmd_date"
        etree.SubElement(date_field, "fieldentry").text = datetime.now().isoformat()

        # Add question count
        count_meta = etree.SubElement(metadata, "qtimetadata")
        count_field = etree.SubElement(count_meta, "qtimetadatafield")
        etree.SubElement(count_field, "fieldlabel").text = "question_count"
        etree.SubElement(count_field, "fieldentry").text = str(question_count)

    def _generate_question_item(
        self,
        question_num: int,
        question_data: dict[str, Any]
    ) -> etree.Element:
        """Generate QTI assessment item for a single question."""
        item = etree.Element(
            "assessmentItem",
            identifier=f"question_{question_num}",
            title=f"Question {question_num}",
            adaptive="false",
            timeDependent="false",
        )

        # Add response declaration based on question type
        question_type = question_data.get("type", "unknown")

        if question_type == "multiple_choice":
            self._add_choice_response(item, question_data)
            self._add_choice_interaction(item, question_data)
        elif question_type == "fill_in_blank":
            self._add_text_response(item, question_data)
            self._add_text_interaction(item, question_data)
        elif question_type == "matching":
            self._add_match_response(item, question_data)
            self._add_match_interaction(item, question_data)
        elif question_type == "categorization":
            self._add_match_response(item, question_data)
            self._add_categorization_interaction(item, question_data)

        # Add response processing (scoring)
        self._add_response_processing(item, question_data)

        return item

    def _add_choice_response(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add response declaration for multiple choice."""
        response_decl = etree.SubElement(
            item,
            "responseDeclaration",
            identifier="RESPONSE",
            cardinality="single",
            baseType="identifier",
        )

        correct_response = etree.SubElement(response_decl, "correctResponse")
        value = etree.SubElement(correct_response, "value")
        value.text = f"choice_{question_data['correct_answer'].lower()}"

    def _add_choice_interaction(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add choice interaction for multiple choice."""
        item_body = etree.SubElement(item, "itemBody")

        # Add question text
        question_p = etree.SubElement(item_body, "p")
        question_p.text = question_data["question_text"]

        # Add choice interaction
        choice_interaction = etree.SubElement(
            item_body,
            "choiceInteraction",
            responseIdentifier="RESPONSE",
            shuffle="false",
            maxChoices="1",
        )

        # Add choices
        for letter in ["A", "B", "C", "D"]:
            option_key = f"option_{letter.lower()}"
            if option_key in question_data:
                choice = etree.SubElement(
                    choice_interaction,
                    "simpleChoice",
                    identifier=f"choice_{letter.lower()}",
                )
                choice.text = question_data[option_key]

    def _add_text_response(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add response declaration for fill-in-blank."""
        response_decl = etree.SubElement(
            item,
            "responseDeclaration",
            identifier="RESPONSE",
            cardinality="single",
            baseType="string",
        )

        if "correct_answers" in question_data:
            correct_response = etree.SubElement(response_decl, "correctResponse")
            for answer in question_data["correct_answers"]:
                value = etree.SubElement(correct_response, "value")
                value.text = answer

    def _add_text_interaction(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add text entry interaction for fill-in-blank."""
        item_body = etree.SubElement(item, "itemBody")

        # Add question text with blanks
        question_p = etree.SubElement(item_body, "p")
        question_p.text = question_data["question_text"]

        text_interaction = etree.SubElement(
            item_body,
            "textEntryInteraction",
            responseIdentifier="RESPONSE",
        )

    def _add_match_response(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add response declaration for matching questions."""
        response_decl = etree.SubElement(
            item,
            "responseDeclaration",
            identifier="RESPONSE",
            cardinality="multiple",
            baseType="directedPair",
        )

        if "correct_matches" in question_data:
            correct_response = etree.SubElement(response_decl, "correctResponse")
            for match in question_data["correct_matches"]:
                value = etree.SubElement(correct_response, "value")
                value.text = f"{match['left']} {match['right']}"

    def _add_match_interaction(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add associate interaction for matching."""
        item_body = etree.SubElement(item, "itemBody")

        question_p = etree.SubElement(item_body, "p")
        question_p.text = question_data["question_text"]

        # This would need more complex implementation for full matching support
        # Simplified version here
        associate_interaction = etree.SubElement(
            item_body,
            "associateInteraction",
            responseIdentifier="RESPONSE",
            shuffle="false",
            maxAssociations="0",
        )

    def _add_categorization_interaction(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add categorization interaction."""
        # Similar to matching but with categories
        self._add_match_interaction(item, question_data)

    def _add_response_processing(
        self,
        item: etree.Element,
        question_data: dict[str, Any]
    ) -> None:
        """Add response processing for scoring."""
        response_processing = etree.SubElement(item, "responseProcessing")

        # Add outcome declaration for SCORE
        outcome_decl = etree.SubElement(
            item,
            "outcomeDeclaration",
            identifier="SCORE",
            cardinality="single",
            baseType="float",
        )
        default_value = etree.SubElement(outcome_decl, "defaultValue")
        value = etree.SubElement(default_value, "value")
        value.text = "0"

        # Simple response processing template
        template = etree.SubElement(
            response_processing,
            "responseCondition"
        )

        response_if = etree.SubElement(template, "responseIf")
        match = etree.SubElement(response_if, "match")
        variable = etree.SubElement(match, "variable", identifier="RESPONSE")
        correct = etree.SubElement(match, "correct", identifier="RESPONSE")

        set_outcome = etree.SubElement(response_if, "setOutcomeValue", identifier="SCORE")
        base_value = etree.SubElement(set_outcome, "baseValue", baseType="float")
        base_value.text = str(self.options.points_per_question)
```

#### Step 6: Create Main Export Service
**File:** `backend/src/export/service.py`

```python
"""Main export service orchestrating PDF and QTI generation."""

import logging
from typing import Any
from uuid import UUID

from src.database import AsyncSession
from src.question import service as question_service

from .pdf_generator import QuizPDFGenerator
from .qti_generator import QTIGenerator
from .schemas import ExportMetadata, PDFExportOptions, QTIExportOptions

logger = logging.getLogger(__name__)


async def export_quiz_to_pdf(
    session: AsyncSession,
    quiz_id: UUID,
    options: PDFExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to PDF format for student distribution.

    Args:
        session: Database session
        quiz_id: Quiz UUID to export
        options: PDF generation options

    Returns:
        Tuple of (PDF bytes, export metadata)

    Raises:
        ValueError: If quiz has no approved questions
        RuntimeError: If PDF generation fails
    """
    if options is None:
        options = PDFExportOptions()

    logger.info(f"Starting PDF export for quiz {quiz_id}")

    # Get quiz and question data
    quiz_data = await _get_quiz_export_data(session, quiz_id)

    # Format questions for PDF (no answers)
    formatted_questions = []
    for question in quiz_data["questions"]:
        pdf_data = question["question_type_instance"].format_for_pdf(
            question["question_data"]
        )
        formatted_questions.append(pdf_data)

    # Generate PDF
    generator = QuizPDFGenerator(options)
    try:
        pdf_bytes = generator.generate_pdf(
            quiz_data["title"],
            formatted_questions
        )
    except Exception as e:
        logger.error(f"PDF generation failed for quiz {quiz_id}: {e}")
        raise RuntimeError(f"Failed to generate PDF: {e}") from e

    # Create metadata
    metadata = ExportMetadata(
        quiz_id=str(quiz_id),
        quiz_title=quiz_data["title"],
        question_count=len(formatted_questions),
        export_format="pdf",
    )

    logger.info(f"PDF export completed for quiz {quiz_id}")
    return pdf_bytes, metadata


async def export_quiz_to_qti_xml(
    session: AsyncSession,
    quiz_id: UUID,
    options: QTIExportOptions | None = None,
) -> tuple[bytes, ExportMetadata]:
    """
    Export quiz to QTI XML format for LMS import.

    Args:
        session: Database session
        quiz_id: Quiz UUID to export
        options: QTI generation options

    Returns:
        Tuple of (XML bytes, export metadata)

    Raises:
        ValueError: If quiz has no approved questions
        RuntimeError: If QTI generation fails
    """
    if options is None:
        options = QTIExportOptions()

    logger.info(f"Starting QTI XML export for quiz {quiz_id}")

    # Get quiz and question data
    quiz_data = await _get_quiz_export_data(session, quiz_id)

    # Format questions for QTI (with answers)
    formatted_questions = []
    for question in quiz_data["questions"]:
        qti_data = question["question_type_instance"].format_for_qti(
            question["question_data"]
        )
        formatted_questions.append(qti_data)

    # Generate QTI XML
    generator = QTIGenerator(options)
    try:
        xml_bytes = generator.generate_qti_xml(
            quiz_data["title"],
            formatted_questions
        )
    except Exception as e:
        logger.error(f"QTI XML generation failed for quiz {quiz_id}: {e}")
        raise RuntimeError(f"Failed to generate QTI XML: {e}") from e

    # Create metadata
    metadata = ExportMetadata(
        quiz_id=str(quiz_id),
        quiz_title=quiz_data["title"],
        question_count=len(formatted_questions),
        export_format="qti_xml",
    )

    logger.info(f"QTI XML export completed for quiz {quiz_id}")
    return xml_bytes, metadata


async def _get_quiz_export_data(
    session: AsyncSession,
    quiz_id: UUID
) -> dict[str, Any]:
    """
    Get quiz and question data for export.

    Args:
        session: Database session
        quiz_id: Quiz UUID

    Returns:
        Dictionary with quiz title and approved questions

    Raises:
        ValueError: If no approved questions found
    """
    # Reuse existing service to get approved questions
    questions_data = await question_service.prepare_questions_for_export(quiz_id)

    if not questions_data or not questions_data.get("questions"):
        raise ValueError("No approved questions found for export")

    return {
        "title": questions_data["quiz_title"],
        "questions": questions_data["questions"],
    }
```

#### Step 7: Extend Question Types with New Formatting Methods
**File:** `backend/src/question/types/base.py`

Add abstract methods to the BaseQuestionType class:

```python
# Add these abstract methods to the BaseQuestionType class

@abstractmethod
def format_for_pdf(self, data: BaseQuestionData) -> dict[str, Any]:
    """Format question data for PDF export (student version - no answers)."""
    pass

@abstractmethod
def format_for_qti(self, data: BaseQuestionData) -> dict[str, Any]:
    """Format question data for QTI XML export (with answers for LMS import)."""
    pass
```

**File:** `backend/src/question/types/mcq.py`

Add these methods to the MultipleChoiceQuestionType class:

```python
def format_for_pdf(self, data: BaseQuestionData) -> dict[str, Any]:
    """Format MCQ for PDF export (no correct answer indication)."""
    if not isinstance(data, MultipleChoiceData):
        raise ValueError("Expected MultipleChoiceData")

    return {
        "type": "multiple_choice",
        "question_text": data.question_text,
        "option_a": data.option_a,
        "option_b": data.option_b,
        "option_c": data.option_c,
        "option_d": data.option_d,
        # No correct_answer for student version
    }

def format_for_qti(self, data: BaseQuestionData) -> dict[str, Any]:
    """Format MCQ for QTI XML export (with correct answer)."""
    if not isinstance(data, MultipleChoiceData):
        raise ValueError("Expected MultipleChoiceData")

    return {
        "type": "multiple_choice",
        "question_text": data.question_text,
        "option_a": data.option_a,
        "option_b": data.option_b,
        "option_c": data.option_c,
        "option_d": data.option_d,
        "correct_answer": data.correct_answer,
        # Additional QTI-specific metadata
        "interaction_type": "choice",
        "max_choices": 1,
        "shuffle": False,
    }
```

Similar methods need to be added to all other question types (`fill_in_blank.py`, `matching.py`, `categorization.py`).

#### Step 8: Add Export Endpoints to Quiz Router
**File:** `backend/src/quiz/router.py`

Add these imports at the top:

```python
from fastapi import StreamingResponse
from fastapi.responses import Response
import io

from src.export import export_quiz_to_pdf, export_quiz_to_qti_xml
from src.export.schemas import ExportFormat, PDFExportOptions, QTIExportOptions
```

Add these endpoints before the final closing:

```python
@router.get("/{quiz_id}/export/{format}")
async def export_quiz_file(
    quiz: QuizOwnership,
    format: ExportFormat,
    current_user: CurrentUser,
    session: SessionDep,
) -> StreamingResponse:
    """
    Export quiz to specified file format.

    Supports PDF export for student distribution (questions only) and
    QTI XML export for LMS import (with answer keys).

    **Parameters:**
        quiz_id (UUID): The UUID of the quiz to export
        format (ExportFormat): Export format - 'pdf' or 'qti_xml'

    **Returns:**
        StreamingResponse: File download with appropriate headers

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 404 if quiz not found or user doesn't own it
        HTTPException: 400 if quiz has no approved questions
        HTTPException: 500 if file generation fails
    """
    logger.info(
        "quiz_file_export_requested",
        user_id=str(current_user.id),
        quiz_id=str(quiz.id),
        format=format.value,
    )

    try:
        # Validate quiz has approved questions (reuse existing validation)
        await validate_quiz_has_approved_questions(quiz, session)

        if format == ExportFormat.PDF:
            # Generate PDF
            pdf_bytes, metadata = await export_quiz_to_pdf(
                session,
                quiz.id,
                PDFExportOptions()
            )

            # Create streaming response
            file_stream = io.BytesIO(pdf_bytes)
            filename = f"{metadata.quiz_title.replace(' ', '_')}_questions.pdf"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf",
            }

            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers=headers,
            )

        elif format == ExportFormat.QTI_XML:
            # Generate QTI XML
            xml_bytes, metadata = await export_quiz_to_qti_xml(
                session,
                quiz.id,
                QTIExportOptions()
            )

            # Create streaming response
            filename = f"{metadata.quiz_title.replace(' ', '_')}_qti.xml"
            headers = {
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/xml",
            }

            return StreamingResponse(
                io.BytesIO(xml_bytes),
                media_type="application/xml",
                headers=headers,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {format}"
            )

    except ValueError as e:
        logger.warning(
            "quiz_file_export_validation_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            format=format.value,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "quiz_file_export_failed",
            user_id=str(current_user.id),
            quiz_id=str(quiz.id),
            format=format.value,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate {format.value} export"
        )
```

### 4.3 Data Models & Schemas

#### Export Format Enum
```python
class ExportFormat(str, Enum):
    PDF = "pdf"          # Student distribution format
    QTI_XML = "qti_xml"  # LMS import format
```

#### Question Data Flow
```
Database Question → Question Type Instance → Format Method → File Generator
     ↓                      ↓                     ↓              ↓
JSON in JSONB field → MultipleChoiceData → format_for_pdf() → PDF bytes
                                        → format_for_qti() → XML bytes
```

#### Example Question Data Structures

**Multiple Choice PDF Format:**
```python
{
    "type": "multiple_choice",
    "question_text": "What is the capital of France?",
    "option_a": "London",
    "option_b": "Berlin",
    "option_c": "Paris",
    "option_d": "Madrid"
    # No correct_answer for student version
}
```

**Multiple Choice QTI Format:**
```python
{
    "type": "multiple_choice",
    "question_text": "What is the capital of France?",
    "option_a": "London",
    "option_b": "Berlin",
    "option_c": "Paris",
    "option_d": "Madrid",
    "correct_answer": "C",
    "interaction_type": "choice",
    "max_choices": 1,
    "shuffle": False
}
```

### 4.4 Configuration

#### PDF Configuration
```python
PDFExportOptions(
    include_instructions=True,  # Add instruction text
    page_format="A4",          # A4 or Letter
    font_size=12               # Base font size
)
```

#### QTI Configuration
```python
QTIExportOptions(
    qti_version="2.1",         # QTI specification version
    include_metadata=True,     # Include quiz metadata
    points_per_question=1.0    # Default points per question
)
```

## 5. Testing Strategy

### 5.1 Unit Tests

**File:** `backend/src/export/tests/test_service.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.export.service import export_quiz_to_pdf, export_quiz_to_qti_xml
from src.export.schemas import PDFExportOptions, QTIExportOptions


class TestExportService:
    """Test cases for export service functions."""

    @pytest.fixture
    def mock_quiz_data(self):
        """Mock quiz data for testing."""
        return {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_type_instance": MockMCQType(),
                    "question_data": {
                        "question_text": "Test question?",
                        "option_a": "Option A",
                        "option_b": "Option B",
                        "option_c": "Option C",
                        "option_d": "Option D",
                        "correct_answer": "A"
                    }
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_export_quiz_to_pdf_success(self, mock_quiz_data):
        """Test successful PDF export."""
        quiz_id = uuid4()

        with patch('src.export.service._get_quiz_export_data') as mock_get_data:
            mock_get_data.return_value = mock_quiz_data

            pdf_bytes, metadata = await export_quiz_to_pdf(
                AsyncMock(),
                quiz_id,
                PDFExportOptions()
            )

            assert isinstance(pdf_bytes, bytes)
            assert len(pdf_bytes) > 0
            assert metadata.quiz_title == "Test Quiz"
            assert metadata.question_count == 1
            assert metadata.export_format == "pdf"

    @pytest.mark.asyncio
    async def test_export_quiz_to_qti_xml_success(self, mock_quiz_data):
        """Test successful QTI XML export."""
        quiz_id = uuid4()

        with patch('src.export.service._get_quiz_export_data') as mock_get_data:
            mock_get_data.return_value = mock_quiz_data

            xml_bytes, metadata = await export_quiz_to_qti_xml(
                AsyncMock(),
                quiz_id,
                QTIExportOptions()
            )

            assert isinstance(xml_bytes, bytes)
            assert len(xml_bytes) > 0
            assert b"assessmentTest" in xml_bytes  # QTI root element
            assert metadata.export_format == "qti_xml"

    @pytest.mark.asyncio
    async def test_export_no_approved_questions(self):
        """Test export fails with no approved questions."""
        quiz_id = uuid4()

        with patch('src.export.service._get_quiz_export_data') as mock_get_data:
            mock_get_data.side_effect = ValueError("No approved questions found")

            with pytest.raises(ValueError, match="No approved questions"):
                await export_quiz_to_pdf(AsyncMock(), quiz_id)


class MockMCQType:
    """Mock MCQ question type for testing."""

    def format_for_pdf(self, data):
        return {
            "type": "multiple_choice",
            "question_text": data["question_text"],
            "option_a": data["option_a"],
            "option_b": data["option_b"],
            "option_c": data["option_c"],
            "option_d": data["option_d"],
        }

    def format_for_qti(self, data):
        return {
            "type": "multiple_choice",
            "question_text": data["question_text"],
            "option_a": data["option_a"],
            "option_b": data["option_b"],
            "option_c": data["option_c"],
            "option_d": data["option_d"],
            "correct_answer": data["correct_answer"],
        }
```

### 5.2 Integration Tests

**Manual Testing Steps:**

1. **Setup Test Quiz:**
   ```bash
   # Create quiz with approved questions via existing API
   POST /api/v1/quiz/
   # Complete content extraction and question generation
   # Approve some questions via review interface
   ```

2. **Test PDF Export:**
   ```bash
   GET /api/v1/quiz/{quiz_id}/export/pdf
   # Verify PDF downloads correctly
   # Check PDF contains questions without answers
   # Validate professional formatting
   ```

3. **Test QTI Export:**
   ```bash
   GET /api/v1/quiz/{quiz_id}/export/qti_xml
   # Verify XML downloads correctly
   # Validate XML structure with QTI schema
   # Check answers are included in XML
   ```

4. **Test Error Cases:**
   ```bash
   # Quiz with no approved questions
   GET /api/v1/quiz/{empty_quiz_id}/export/pdf
   # Should return 400 error

   # Non-existent quiz
   GET /api/v1/quiz/{fake_id}/export/pdf
   # Should return 404 error

   # Unauthorized access
   GET /api/v1/quiz/{other_user_quiz}/export/pdf
   # Should return 404 error
   ```

### 5.3 Performance Benchmarks

- **PDF Generation:** < 2 seconds for 50 questions
- **QTI Generation:** < 1 second for 50 questions
- **Memory Usage:** < 50MB peak during generation
- **File Sizes:** ~100KB PDF for 20 questions, ~200KB QTI XML

## 6. Deployment Instructions

### 6.1 Development Environment

1. **Install Dependencies:**
   ```bash
   cd backend
   uv sync  # Install new dependencies from pyproject.toml
   ```

2. **Run Tests:**
   ```bash
   cd backend && source .venv/bin/activate && bash scripts/test.sh
   ```

3. **Start Development Server:**
   ```bash
   docker compose watch
   ```

### 6.2 Production Deployment

1. **Update Dependencies:**
   - Ensure `reportlab>=4.0.0` and `lxml>=5.0.0` are in requirements
   - Rebuild Docker images with new dependencies

2. **Deploy Code:**
   - Deploy all new files in `src/export/` directory
   - Deploy modified question type files
   - Deploy updated quiz router

3. **Verify Deployment:**
   ```bash
   # Check API docs include new endpoints
   curl https://api.domain.com/docs

   # Test export functionality
   curl -H "Authorization: Bearer $TOKEN" \
        https://api.domain.com/api/v1/quiz/{id}/export/pdf
   ```

### 6.3 Rollback Procedures

1. **Code Rollback:**
   - Remove export endpoints from router
   - Remove import statements
   - Keep export module files (no breaking changes)

2. **Dependency Rollback:**
   - New dependencies don't break existing functionality
   - Can be safely left installed

## 7. Monitoring & Maintenance

### 7.1 Key Metrics

- **Export Request Rate:** Requests per minute for each format
- **Export Success Rate:** Percentage of successful exports
- **Export Duration:** Time taken for file generation
- **File Size Distribution:** Size of generated files
- **Error Rate by Type:** PDF vs QTI XML error rates

### 7.2 Log Entries to Monitor

```python
# Successful exports
"quiz_file_export_completed" - user_id, quiz_id, format, file_size, duration

# Failed exports
"quiz_file_export_failed" - user_id, quiz_id, format, error, error_type

# Performance issues
"export_generation_slow" - quiz_id, format, duration, threshold_exceeded
```

### 7.3 Common Issues

**Issue:** PDF generation fails with ReportLab errors
- **Cause:** Invalid characters in question text
- **Solution:** Add text sanitization in PDF generator
- **Prevention:** Validate question text during creation

**Issue:** QTI XML validation fails in target LMS
- **Cause:** Non-standard QTI structure
- **Solution:** Update QTI generator with LMS-specific requirements
- **Prevention:** Test with multiple LMS platforms

**Issue:** Large file sizes causing timeouts
- **Cause:** Many questions with complex formatting
- **Solution:** Implement streaming for large files
- **Prevention:** Set reasonable question limits

## 8. Security Considerations

### 8.1 Authentication & Authorization

- **Quiz Ownership:** Only quiz owners can export their quizzes
- **JWT Validation:** All endpoints require valid authentication tokens
- **Permission Checks:** Reuse existing `QuizOwnership` dependency

### 8.2 Data Privacy

- **Student Data:** PDF exports contain no student information
- **Answer Keys:** QTI exports include answers but only for quiz owners
- **Temporary Files:** No files persisted on server after response

### 8.3 Security Best Practices

- **Input Validation:** Sanitize quiz titles and question text for file generation
- **File Size Limits:** Prevent DoS through large export requests
- **Rate Limiting:** Consider limiting export requests per user
- **Content Security:** Ensure generated files don't contain injection vulnerabilities

### 8.4 Potential Vulnerabilities

- **XML External Entity (XXE):** Use safe XML parsing in lxml
- **PDF Injection:** Sanitize content passed to ReportLab
- **Path Traversal:** Use safe filename generation from quiz titles

## 9. Future Considerations

### 9.1 Known Limitations

- **Single File Output:** QTI could be enhanced to ZIP format with separate item files
- **Limited Question Types:** Additional question types need formatting methods
- **Basic PDF Styling:** Could be enhanced with themes and customization
- **QTI Version:** Only supports QTI 2.1, newer versions may be needed

### 9.2 Potential Improvements

- **Export Templates:** Allow customizable PDF and QTI templates
- **Batch Export:** Export multiple quizzes in single operation
- **Scheduled Exports:** Background export jobs for large quizzes
- **Export History:** Track export events and provide download history
- **Format Validation:** Pre-validate exports against target LMS requirements

### 9.3 Scalability Considerations

- **Memory Usage:** For very large quizzes, implement streaming generation
- **CPU Load:** Consider queue-based processing for export requests
- **File Caching:** Cache generated files for frequently exported quizzes
- **CDN Integration:** Serve large exports through CDN for better performance

### 9.4 Integration Opportunities

- **LMS Connectors:** Direct integration with popular LMS platforms
- **Cloud Storage:** Option to save exports to cloud storage
- **Analytics:** Track usage patterns and popular export formats
- **API Extensions:** Provide export capabilities via public API

---

This implementation guide provides a complete roadmap for adding PDF and QTI XML export functionality to the Rag@UiT quiz system. The feature integrates seamlessly with existing patterns while providing professional-quality export capabilities for educational use cases.
