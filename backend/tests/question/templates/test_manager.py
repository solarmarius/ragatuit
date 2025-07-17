"""Tests for the template manager with question type-based template discovery."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def template_manager(tmp_path):
    """Create a template manager with test templates."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Create test templates
    mcq_template = {
        "name": "batch_multiple_choice",
        "version": "1.0",
        "question_type": "multiple_choice",
        "description": "Test MCQ template",
        "system_prompt": "Generate MCQ questions from {{ module_content }}",
        "user_prompt": "Create {{ target_count }} questions from content: {{ module_content }}",
        "variables": {
            "module_content": "The module content",
            "question_count": "Number of questions",
        },
    }

    mcq_no_template = {
        "name": "batch_multiple_choice_no",
        "version": "1.0",
        "question_type": "multiple_choice",
        "language": "no",
        "description": "Test Norwegian MCQ template",
        "system_prompt": "Generer flervalgsspørsmål fra {{ module_content }}",
        "user_prompt": "Lag {{ target_count }} spørsmål fra innhold: {{ module_content }}",
        "variables": {
            "module_content": "Modulinnholdet",
            "question_count": "Antall spørsmål",
        },
    }

    # Write templates to files
    with open(templates_dir / "batch_multiple_choice.json", "w") as f:
        json.dump(mcq_template, f)

    with open(templates_dir / "batch_multiple_choice_no.json", "w") as f:
        json.dump(mcq_no_template, f)

    from src.question.templates.manager import TemplateManager

    manager = TemplateManager(str(templates_dir))
    manager.initialize()
    return manager


def test_get_template_by_question_type_english(template_manager):
    """Test getting English template by question type."""
    from src.question.types import QuestionType, QuizLanguage

    template = template_manager.get_template(question_type=QuestionType.MULTIPLE_CHOICE)

    assert template.name == "batch_multiple_choice"
    assert template.question_type == QuestionType.MULTIPLE_CHOICE
    assert template.language is None or template.language == QuizLanguage.ENGLISH


def test_get_template_by_question_type_norwegian(template_manager):
    """Test getting Norwegian template by question type."""
    from src.question.types import QuestionType, QuizLanguage

    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language=QuizLanguage.NORWEGIAN
    )

    assert template.name == "batch_multiple_choice_no"
    assert template.question_type == QuestionType.MULTIPLE_CHOICE
    assert template.language == QuizLanguage.NORWEGIAN


def test_get_template_with_string_language(template_manager):
    """Test getting template with language as string."""
    from src.question.types import QuestionType, QuizLanguage

    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language="no"
    )

    assert template.name == "batch_multiple_choice_no"
    assert template.language == QuizLanguage.NORWEGIAN


def test_get_template_with_explicit_name(template_manager):
    """Test getting template with explicit template name."""
    from src.question.types import QuestionType

    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE,
        template_name="batch_multiple_choice_no",
    )

    assert template.name == "batch_multiple_choice_no"


def test_template_not_found_error(template_manager):
    """Test error when template is not found."""
    from src.question.types import QuestionType

    with pytest.raises(ValueError) as exc_info:
        template_manager.get_template(
            question_type=QuestionType.FILL_IN_BLANK  # Not implemented yet
        )

    assert "No template found for question type fill_in_blank" in str(exc_info.value)


def test_list_templates_by_question_type(template_manager):
    """Test listing templates filtered by question type."""
    from src.question.types import QuestionType

    templates = template_manager.list_templates(
        question_type=QuestionType.MULTIPLE_CHOICE
    )

    assert len(templates) == 2
    assert all(t.question_type == QuestionType.MULTIPLE_CHOICE for t in templates)


def test_template_naming_convention(template_manager):
    """Test that default template names follow the convention."""
    from src.question.types import QuestionType, QuizLanguage

    # Test English template name generation
    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language=QuizLanguage.ENGLISH
    )
    assert template.name == "batch_multiple_choice"

    # Test Norwegian template name generation
    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language=QuizLanguage.NORWEGIAN
    )
    assert template.name == "batch_multiple_choice_no"


@pytest.mark.asyncio
async def test_create_messages_with_question_type(template_manager):
    """Test create_messages method works with question type parameter."""
    from src.question.types import GenerationParameters, QuestionType, QuizLanguage

    params = GenerationParameters(target_count=5, language=QuizLanguage.ENGLISH)

    messages = await template_manager.create_messages(
        question_type=QuestionType.MULTIPLE_CHOICE,
        content="Test content",
        generation_parameters=params,
        extra_variables={"module_name": "Test Module"},
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "5" in messages[1].content  # target_count should be rendered


@pytest.mark.asyncio
async def test_create_messages_with_norwegian_language(template_manager):
    """Test create_messages method works with Norwegian language."""
    from src.question.types import GenerationParameters, QuestionType, QuizLanguage

    params = GenerationParameters(target_count=3, language=QuizLanguage.NORWEGIAN)

    messages = await template_manager.create_messages(
        question_type=QuestionType.MULTIPLE_CHOICE,
        content="Test innhold",
        generation_parameters=params,
        language=QuizLanguage.NORWEGIAN,
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    assert "3" in messages[1].content  # target_count should be rendered
    assert "Test innhold" in messages[1].content


def test_template_initialization_loads_templates(template_manager):
    """Test that template manager loads templates during initialization."""
    assert len(template_manager._template_cache) == 2
    template_names = [t.name for t in template_manager._template_cache.values()]
    assert "batch_multiple_choice" in template_names
    assert "batch_multiple_choice_no" in template_names


def test_template_properties_parsed_correctly(template_manager):
    """Test that template properties are parsed correctly."""
    from src.question.types import QuestionType, QuizLanguage

    # Test English template
    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language=QuizLanguage.ENGLISH
    )
    assert template.version == "1.0"
    assert template.description == "Test MCQ template"
    assert "module_content" in template.variables
    assert "question_count" in template.variables

    # Test Norwegian template
    template = template_manager.get_template(
        question_type=QuestionType.MULTIPLE_CHOICE, language=QuizLanguage.NORWEGIAN
    )
    assert template.version == "1.0"
    assert template.description == "Test Norwegian MCQ template"
    assert template.language == QuizLanguage.NORWEGIAN
