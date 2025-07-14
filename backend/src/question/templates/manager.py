"""Template manager for prompt templates and question generation."""

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field

from src.config import get_logger

from ..providers import LLMMessage
from ..types import GenerationParameters, QuestionType, QuizLanguage

logger = get_logger("template_manager")


class PromptTemplate(BaseModel):
    """A prompt template configuration."""

    name: str = Field(description="Template name")
    version: str = Field(default="1.0", description="Template version")
    question_type: QuestionType = Field(
        description="Question type this template supports"
    )
    language: QuizLanguage | None = Field(
        default=None, description="Language for this template (None = default/English)"
    )
    description: str | None = Field(default=None, description="Template description")

    # Template content
    system_prompt: str = Field(description="System prompt template")
    user_prompt: str = Field(description="User prompt template")

    # Template variables and their descriptions
    variables: dict[str, str] = Field(
        default_factory=dict, description="Template variables and descriptions"
    )

    # Template metadata
    author: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    created_at: str | None = Field(default=None)
    updated_at: str | None = Field(default=None)

    # Validation rules
    min_content_length: int = Field(
        default=100, description="Minimum content length required"
    )
    max_content_length: int = Field(
        default=10000, description="Maximum content length supported"
    )

    class Config:
        """Pydantic configuration."""

        extra = "forbid"


class TemplateManager:
    """
    Manager for prompt templates with file-based storage.

    Provides loading, caching, and rendering of prompt templates for
    different question types and use cases.
    """

    def __init__(self, templates_dir: str | None = None):
        """
        Initialize template manager.

        Args:
            templates_dir: Directory containing template files
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            self.templates_dir = current_dir / "files"
        else:
            self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # We're not rendering HTML
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Template cache
        self._template_cache: dict[str, PromptTemplate] = {}
        self._jinja_cache: dict[str, Template] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the template manager and load templates."""
        if self._initialized:
            return

        try:
            self._load_templates()

            logger.info(
                "template_manager_initialized",
                templates_dir=str(self.templates_dir),
                loaded_templates=len(self._template_cache),
            )

        except Exception as e:
            logger.error(
                "template_manager_initialization_failed",
                templates_dir=str(self.templates_dir),
                error=str(e),
                exc_info=True,
            )
            # Continue with empty cache rather than failing

        self._initialized = True

    def get_template(
        self,
        question_type: QuestionType,
        template_name: str | None = None,
        language: QuizLanguage | str | None = None,
    ) -> PromptTemplate:
        """
        Get a prompt template for a question type.

        Args:
            question_type: The question type
            template_name: Specific template name, uses default if None
            language: Language for template, uses English if None

        Returns:
            Prompt template

        Raises:
            ValueError: If no template is found
        """
        if not self._initialized:
            self.initialize()

        # Normalize language (None means English/default)
        if language is None:
            language = QuizLanguage.ENGLISH
        elif isinstance(language, str):
            # Handle string values
            language = QuizLanguage(language)

        # If no specific template name, use default for question type
        if template_name is None:
            # Try language-specific template first
            if language == QuizLanguage.NORWEGIAN:
                template_name = f"default_{question_type.value}_no"
            else:
                template_name = f"default_{question_type.value}"

        # Try exact match first with language consideration
        if template_name in self._template_cache:
            template = self._template_cache[template_name]
            if template.question_type == question_type:
                # Check if template language matches requested language
                template_lang = template.language or QuizLanguage.ENGLISH
                if template_lang == language:
                    return template

        # Try language-specific template by appending language suffix
        if language == QuizLanguage.NORWEGIAN and not template_name.endswith("_no"):
            language_specific_name = f"{template_name}_no"
            if language_specific_name in self._template_cache:
                template = self._template_cache[language_specific_name]
                if template.question_type == question_type:
                    return template

        # Try finding by question type and language
        for template in self._template_cache.values():
            if template.question_type == question_type:
                template_lang = template.language or QuizLanguage.ENGLISH
                if template_lang == language and (
                    template_name is None or template.name == template_name
                ):
                    return template

        # Fallback: try English template if Norwegian was requested but not found
        if language == QuizLanguage.NORWEGIAN:
            logger.warning(
                "norwegian_template_not_found_fallback_to_english",
                question_type=question_type.value,
                template_name=template_name,
            )
            return self.get_template(question_type, template_name, QuizLanguage.ENGLISH)

        raise ValueError(
            f"No template found for question type {question_type} with name {template_name} and language {language}"
        )

    def list_templates(
        self, question_type: QuestionType | None = None
    ) -> list[PromptTemplate]:
        """
        List available templates.

        Args:
            question_type: Filter by question type, returns all if None

        Returns:
            List of available templates
        """
        if not self._initialized:
            self.initialize()

        templates = list(self._template_cache.values())

        if question_type is not None:
            templates = [t for t in templates if t.question_type == question_type]

        return sorted(templates, key=lambda t: (t.question_type.value, t.name))

    async def create_messages(
        self,
        question_type: QuestionType,
        content: str,
        generation_parameters: GenerationParameters,
        template_name: str | None = None,
        language: QuizLanguage | str | None = None,
        extra_variables: dict[str, Any] | None = None,
    ) -> list[LLMMessage]:
        """
        Create LLM messages using a template.

        Args:
            question_type: The question type
            content: Content to generate questions from
            generation_parameters: Generation parameters
            template_name: Specific template to use
            language: Language for template selection
            extra_variables: Additional template variables

        Returns:
            List of LLM messages
        """
        # Normalize language if it's a string
        if isinstance(language, str):
            language = QuizLanguage(language)

        template = self.get_template(question_type, template_name, language)

        # Prepare template variables
        variables = {
            "module_content": content,
            "target_count": generation_parameters.target_count,
            "difficulty": generation_parameters.difficulty.value
            if generation_parameters.difficulty
            else None,
            "tags": generation_parameters.tags or [],
            "custom_instructions": generation_parameters.custom_instructions,
            "question_type": question_type.value,
        }

        # Add extra variables if provided
        if extra_variables:
            variables.update(extra_variables)

        # Render templates
        system_prompt = self._render_template(template.system_prompt, variables)
        user_prompt = self._render_template(template.user_prompt, variables)

        logger.debug(
            "template_messages_created",
            question_type=question_type.value,
            template_name=template.name,
            system_prompt_length=len(system_prompt),
            user_prompt_length=len(user_prompt),
            variables_count=len(variables),
        )

        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

    def save_template(self, template: PromptTemplate) -> None:
        """
        Save a template to file.

        Args:
            template: Template to save
        """
        filename = f"{template.name}.json"
        filepath = self.templates_dir / filename

        # Save as JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(template.dict(), f, indent=2, ensure_ascii=False)

        # Update cache
        self._template_cache[template.name] = template

        logger.info(
            "template_saved",
            template_name=template.name,
            question_type=template.question_type.value,
            filepath=str(filepath),
        )

    def delete_template(self, template_name: str) -> None:
        """
        Delete a template.

        Args:
            template_name: Name of template to delete

        Raises:
            ValueError: If template is not found
        """
        if template_name not in self._template_cache:
            raise ValueError(f"Template {template_name} not found")

        # Remove from filesystem
        filename = f"{template_name}.json"
        filepath = self.templates_dir / filename

        if filepath.exists():
            filepath.unlink()

        # Remove from cache
        del self._template_cache[template_name]

        # Remove from Jinja cache if present
        if template_name in self._jinja_cache:
            del self._jinja_cache[template_name]

        logger.info(
            "template_deleted", template_name=template_name, filepath=str(filepath)
        )

    def validate_template(self, template: PromptTemplate) -> list[str]:
        """
        Validate a template for common issues.

        Args:
            template: Template to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check required fields
        if not template.system_prompt.strip():
            errors.append("System prompt cannot be empty")

        if not template.user_prompt.strip():
            errors.append("User prompt cannot be empty")

        # Check template syntax
        try:
            self._render_template(template.system_prompt, {"content": "test"})
        except Exception as e:
            errors.append(f"System prompt template syntax error: {str(e)}")

        try:
            self._render_template(template.user_prompt, {"content": "test"})
        except Exception as e:
            errors.append(f"User prompt template syntax error: {str(e)}")

        # Check for required variables
        required_vars = ["content"]
        for var in required_vars:
            if var not in template.system_prompt and var not in template.user_prompt:
                errors.append(f"Template must include required variable: {{{{{var}}}}}")

        return errors

    def _load_templates(self) -> None:
        """Load templates from filesystem."""
        if not self.templates_dir.exists():
            return

        for filepath in self.templates_dir.glob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)

                template = PromptTemplate(**data)

                # Validate template
                errors = self.validate_template(template)
                if errors:
                    logger.warning(
                        "template_validation_failed",
                        filepath=str(filepath),
                        errors=errors,
                    )
                    continue

                self._template_cache[template.name] = template

                logger.debug(
                    "template_loaded",
                    template_name=template.name,
                    question_type=template.question_type.value,
                    filepath=str(filepath),
                )

            except Exception as e:
                logger.error(
                    "template_load_failed",
                    filepath=str(filepath),
                    error=str(e),
                    exc_info=True,
                )

    def _render_template(self, template_string: str, variables: dict[str, Any]) -> str:
        """
        Render a template string with variables.

        Args:
            template_string: Template string to render
            variables: Variables for template

        Returns:
            Rendered template
        """
        template = self.jinja_env.from_string(template_string)
        return template.render(**variables)


# Default template manager instance
_default_template_manager: TemplateManager | None = None


def get_template_manager() -> TemplateManager:
    """Get the default template manager instance."""
    global _default_template_manager

    if _default_template_manager is None:
        _default_template_manager = TemplateManager()
        _default_template_manager.initialize()

    return _default_template_manager
