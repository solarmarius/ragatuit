"""QTI 2.1 XML generation service using lxml."""

import uuid
from datetime import datetime
from typing import Any

from lxml import etree  # type: ignore[import-untyped]

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
        questions: list[dict[str, Any]],
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
            "http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd",
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
        for i, _question in enumerate(questions):
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

        # Generate individual question files and embed them
        questions_section = etree.SubElement(root, "questions")
        for i, question in enumerate(questions):
            question_xml = self._generate_question_item(i + 1, question)
            question_element = etree.SubElement(
                questions_section,
                "embeddedQuestion",
                identifier=f"question_{i+1}",
            )
            question_element.text = etree.tostring(
                question_xml,
                encoding="unicode",
            )

        # Generate XML string
        xml_bytes = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )

        # Ensure we return bytes
        if isinstance(xml_bytes, str):
            return xml_bytes.encode("utf-8")
        return xml_bytes  # type: ignore[no-any-return]

    def _add_metadata(
        self,
        root: etree.Element,
        title: str,
        question_count: int,
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
        question_data: dict[str, Any],
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
        question_data: dict[str, Any],
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
        question_data: dict[str, Any],
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
        for option_letter in ["A", "B", "C", "D"]:
            option_key = f"option_{option_letter.lower()}"
            if option_key in question_data:
                choice = etree.SubElement(
                    choice_interaction,
                    "simpleChoice",
                    identifier=f"choice_{option_letter.lower()}",
                )
                choice.text = question_data[option_key]

    def _add_text_response(
        self,
        item: etree.Element,
        question_data: dict[str, Any],
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
        question_data: dict[str, Any],
    ) -> None:
        """Add text entry interaction for fill-in-blank."""
        item_body = etree.SubElement(item, "itemBody")

        # Add question text with blanks
        question_p = etree.SubElement(item_body, "p")
        question_p.text = question_data["question_text"]

        etree.SubElement(
            item_body,
            "textEntryInteraction",
            responseIdentifier="RESPONSE",
        )

    def _add_match_response(
        self,
        item: etree.Element,
        question_data: dict[str, Any],
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
        question_data: dict[str, Any],
    ) -> None:
        """Add associate interaction for matching."""
        item_body = etree.SubElement(item, "itemBody")

        question_p = etree.SubElement(item_body, "p")
        question_p.text = question_data["question_text"]

        # Simplified version for matching
        etree.SubElement(
            item_body,
            "associateInteraction",
            responseIdentifier="RESPONSE",
            shuffle="false",
            maxAssociations="0",
        )

    def _add_categorization_interaction(
        self,
        item: etree.Element,
        question_data: dict[str, Any],
    ) -> None:
        """Add categorization interaction."""
        # Similar to matching but with categories
        self._add_match_interaction(item, question_data)

    def _add_response_processing(
        self,
        item: etree.Element,
        question_data: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """Add response processing for scoring."""
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
        response_processing = etree.SubElement(item, "responseProcessing")
        template = etree.SubElement(response_processing, "responseCondition")

        response_if = etree.SubElement(template, "responseIf")
        match = etree.SubElement(response_if, "match")
        etree.SubElement(match, "variable", identifier="RESPONSE")
        etree.SubElement(match, "correct", identifier="RESPONSE")

        set_outcome = etree.SubElement(
            response_if, "setOutcomeValue", identifier="SCORE"
        )
        base_value = etree.SubElement(set_outcome, "baseValue", baseType="float")
        base_value.text = str(self.options.points_per_question)
