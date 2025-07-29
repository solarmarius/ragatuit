"""PDF generation service using ReportLab."""

import io
from typing import Any

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4, letter  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
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

    def generate_pdf(self, quiz_title: str, questions: list[dict[str, Any]]) -> bytes:
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
        self, question_num: int, question_data: dict[str, Any]
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
        for option_letter in ["A", "B", "C", "D"]:
            option_key = f"option_{option_letter.lower()}"
            if option_key in question_data:
                option_text = f"{option_letter}. {question_data[option_key]}"
                options.append(Paragraph(option_text, self.styles["OptionText"]))
        return options

    def _format_fill_blank(self, question_data: dict[str, Any]) -> list[Any]:
        """Format fill-in-the-blank questions."""
        elements = []
        if "blank_count" in question_data:
            elements.append(Spacer(1, 10))
            blank_count = question_data["blank_count"]
            instruction_text = (
                f"Fill in the {blank_count} blank{'s' if blank_count > 1 else ''} "
                "with appropriate answers."
            )
            elements.append(Paragraph(instruction_text, self.styles["Normal"]))
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

            table = Table(table_data, colWidths=[3 * inch, 3 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("BACKGROUND", (0, 0), (-1, 1), colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ]
                )
            )
            elements.append(table)

        return elements

    def _format_categorization(self, question_data: dict[str, Any]) -> list[Any]:
        """Format categorization questions."""
        elements = []

        if "items_to_categorize" in question_data and "categories" in question_data:
            elements.append(
                Paragraph("Categorize the following items:", self.styles["Normal"])
            )
            elements.append(Spacer(1, 5))

            # List items to categorize
            items = question_data["items_to_categorize"]
            for item in items:
                elements.append(Paragraph(f"• {item}", self.styles["OptionText"]))

            elements.append(Spacer(1, 10))

            # List categories
            categories = question_data["categories"]
            elements.append(Paragraph("Categories:", self.styles["Normal"]))
            for category in categories:
                elements.append(Paragraph(f"• {category}", self.styles["OptionText"]))

        return elements
