# Multiple Question Types per Module Implementation Guide

**Date:** 2025-07-25
**Version:** 1.0
**Status:** Implementation Ready

## 1. Feature Overview

### Description
This feature enables instructors to generate multiple types of questions from a single course module in Canvas LMS. Instead of being limited to one question type per quiz, users can now create "batches" of different question types for each module, allowing for more diverse and comprehensive assessments.

### Business Value
- **Increased Flexibility**: Instructors can create varied assessments that test different cognitive levels
- **Better Assessment Quality**: Combining multiple question types provides more comprehensive evaluation
- **Efficiency**: Generate all question types in one workflow instead of creating multiple quizzes
- **Customization**: Fine-grained control over question distribution per module

### User Benefits
- Create up to 4 different question type batches per module
- Specify exact count for each question type (1-20 questions per batch)
- Parallel generation for faster processing
- Selective retry for failed batches without regenerating successful ones

### Context
Previously, the system allowed only one question type per quiz, applied uniformly across all selected modules. This limitation meant instructors had to create multiple quizzes to use different question types for the same content.

## 2. Technical Architecture

### High-Level Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│                 │     │                 │     │                  │
│   Frontend      │────▶│   API Layer     │────▶│  Quiz Service    │
│   (React)       │     │   (FastAPI)     │     │                  │
│                 │     │                 │     │                  │
└─────────────────┘     └─────────────────┘     └────────┬─────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│                 │     │                 │     │                  │
│  LLM Provider   │◀────│   Generation    │◀────│  Orchestrator    │
│  (OpenAI/Mock)  │     │   Workflow      │     │                  │
│                 │     │                 │     │                  │
└─────────────────┘     └─────────────────┘     └──────────────────┘
```

### System Integration
The feature modifies the quiz creation flow at multiple levels:

1. **API Layer**: Accepts new request structure with question batches per module
2. **Data Model**: Stores question type distribution in `selected_modules` JSON field
3. **Generation Workflow**: Processes multiple batches per module in parallel
4. **Batch Tracking**: Each question type per module is tracked as a separate batch in `generation_metadata`

### Key Components
- **Quiz Model**: Central entity storing module selections with question batches
- **Generation Service**: Orchestrates parallel question generation for all batches
- **Module Batch Workflow**: Handles individual batch generation with retry logic
- **Batch Keys**: Unique identifiers format: `{module_id}_{question_type}_{count}`

## 3. Dependencies & Prerequisites

### Backend Dependencies
```toml
# Already included in pyproject.toml
fastapi = "^0.115.0"
sqlmodel = "^0.0.22"
pydantic = "^2.10.2"
langgraph = "^0.2.39"
asyncio = "*"  # Built-in Python
```

### Database Requirements
- PostgreSQL 13+ with JSONB support
- Existing tables: `quiz`, `question`, `user`

### Environment Setup
```bash
# Backend development environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Database must be running
docker compose up -d db
```

### Configuration Prerequisites
- Canvas OAuth credentials configured
- LLM provider API keys set
- Database connection string configured

## 4. Implementation Details

### 4.1 File Structure

```
backend/src/
├── quiz/
│   ├── models.py          # Modified: Remove question_type field
│   ├── schemas.py         # Modified: Add QuestionBatch schema
│   ├── router.py          # Modified: Update endpoint validation
│   ├── service.py         # Modified: Handle new structure
│   └── orchestrator.py    # Modified: Remove single question_type
├── question/
│   ├── services/
│   │   └── generation_service.py  # Modified: Multiple batches logic
│   └── workflows/
│       └── module_batch_workflow.py  # Modified: Process batches
└── tests/
    ├── quiz/
    │   └── test_quiz_service.py  # Modified: New structure tests
    └── question/
        └── test_generation_service.py  # Modified: Multi-batch tests
```

### 4.2 Step-by-Step Implementation

#### Step 1: Update Quiz Schemas
**File: `backend/src/quiz/schemas.py`**

```python
"""Quiz schemas for validation and serialization."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import field_validator
from sqlmodel import Field, SQLModel

# Import QuizLanguage and QuestionType from question types to avoid circular dependency
from src.question.types import QuestionType, QuizLanguage


class QuizStatus(str, Enum):
    """Consolidated status values for quiz workflow."""

    CREATED = "created"
    EXTRACTING_CONTENT = "extracting_content"
    GENERATING_QUESTIONS = "generating_questions"
    READY_FOR_REVIEW = "ready_for_review"
    READY_FOR_REVIEW_PARTIAL = "ready_for_review_partial"
    EXPORTING_TO_CANVAS = "exporting_to_canvas"
    PUBLISHED = "published"
    FAILED = "failed"


class FailureReason(str, Enum):
    """Specific failure reasons for detailed error tracking."""

    CONTENT_EXTRACTION_ERROR = "content_extraction_error"
    NO_CONTENT_FOUND = "no_content_found"
    LLM_GENERATION_ERROR = "llm_generation_error"
    NO_QUESTIONS_GENERATED = "no_questions_generated"
    CANVAS_EXPORT_ERROR = "canvas_export_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"


class QuestionBatch(SQLModel):
    """Schema for a batch of questions of a specific type."""

    question_type: QuestionType
    count: int = Field(ge=1, le=20, description="Number of questions (1-20)")


class ModuleSelection(SQLModel):
    """Schema for module selection with multiple question type batches."""

    name: str
    question_batches: list[QuestionBatch] = Field(
        min_length=1,
        max_length=4,
        description="Question type batches (1-4 per module)"
    )

    @property
    def total_questions(self) -> int:
        """Calculate total questions across all batches."""
        return sum(batch.count for batch in self.question_batches)


class QuizCreate(SQLModel):
    """Schema for creating a new quiz with module-based questions."""

    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, ModuleSelection]
    title: str = Field(min_length=1, max_length=255)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    language: QuizLanguage = Field(default=QuizLanguage.ENGLISH)
    # Removed: question_type field

    @field_validator("selected_modules")
    def validate_modules(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate selected modules structure."""
        if not v:
            raise ValueError("At least one module must be selected")

        for module_id, module_data in v.items():
            if not isinstance(module_data, (dict, ModuleSelection)):
                raise ValueError(f"Module {module_id} must be a valid module selection")

            # Convert to ModuleSelection if dict
            if isinstance(module_data, dict):
                try:
                    module_selection = ModuleSelection(**module_data)
                except Exception as e:
                    raise ValueError(f"Module {module_id} has invalid structure: {e}")
            else:
                module_selection = module_data

            # Validate batch count
            if len(module_selection.question_batches) > 4:
                raise ValueError(f"Module {module_id} cannot have more than 4 question batches")

            # Validate no duplicate question types in same module
            question_types = [batch.question_type for batch in module_selection.question_batches]
            if len(question_types) != len(set(question_types)):
                raise ValueError(f"Module {module_id} has duplicate question types")

        return v

    @property
    def total_question_count(self) -> int:
        """Calculate total questions across all modules and batches."""
        total = 0
        for module in self.selected_modules.values():
            if isinstance(module, ModuleSelection):
                total += module.total_questions
            elif isinstance(module, dict) and "question_batches" in module:
                for batch in module["question_batches"]:
                    total += batch.get("count", 0)
        return total


class QuizUpdate(SQLModel):
    """Schema for updating quiz settings."""

    title: str | None = Field(None, min_length=1, max_length=255)
    llm_model: str | None = None
    llm_temperature: float | None = Field(None, ge=0.0, le=2.0)
    language: QuizLanguage | None = None


class QuizRead(SQLModel):
    """Schema for reading quiz data."""

    id: UUID
    owner_id: UUID | None
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[str, dict[str, Any]]
    title: str
    llm_model: str
    llm_temperature: float
    language: QuizLanguage
    status: QuizStatus
    failure_reason: FailureReason | None
    last_status_update: datetime
    created_at: datetime | None
    updated_at: datetime | None
    canvas_quiz_id: str | None
    exported_at: datetime | None
    generation_metadata: dict[str, Any]
    deleted: bool
    deleted_at: datetime | None
```

**Key Changes:**
- Added `QuestionBatch` schema for type-count pairs
- Updated `ModuleSelection` to include `question_batches` list
- Removed `question_type` from `QuizCreate`
- Added validation for max 4 batches and no duplicate types per module

#### Step 2: Update Quiz Model
**File: `backend/src/quiz/models.py`**

```python
"""Quiz database models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import field_validator
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.auth.models import User
    from src.question.models import Question

from src.question.types import QuizLanguage

from .schemas import FailureReason, QuizStatus


class Quiz(SQLModel, table=True):
    """Quiz model representing a quiz with questions generated from Canvas content."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID | None = Field(foreign_key="user.id", nullable=True, index=True)
    owner: Optional["User"] = Relationship(back_populates="quizzes")
    canvas_course_id: int = Field(index=True)
    canvas_course_name: str
    selected_modules: dict[str, dict[str, Any]] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, default={})
    )
    title: str = Field(min_length=1)
    # Removed: question_count field (now calculated from modules)
    llm_model: str = Field(default="o3")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)
    language: QuizLanguage = Field(
        default=QuizLanguage.ENGLISH,
        description="Language for question generation",
    )
    # Removed: question_type field
    status: QuizStatus = Field(
        default=QuizStatus.CREATED,
        description="Consolidated quiz status",
        index=True,
    )
    failure_reason: FailureReason | None = Field(
        default=None,
        description="Specific failure reason when status is failed",
        index=True,
    )
    last_status_update: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
    )
    extracted_content: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    content_extracted_at: datetime | None = Field(
        default=None,
        description="Timestamp when content extraction was completed",
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=True
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            onupdate=func.now(),
            nullable=True,
        ),
    )
    canvas_quiz_id: str | None = Field(
        default=None, description="Canvas quiz assignment ID after export"
    )
    exported_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True),
        default=None,
        description="Timestamp when quiz was exported to Canvas",
    )
    generation_metadata: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, default={}),
        description="Additional metadata for tracking generation details",
    )
    questions: list["Question"] = Relationship(
        back_populates="quiz", cascade_delete=True
    )
    deleted: bool = Field(
        default=False,
        index=True,
        description="Soft delete flag for data preservation",
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp when quiz was soft deleted",
    )

    @property
    def total_question_count(self) -> int:
        """Calculate total questions from all module batches."""
        total = 0
        for module_data in self.selected_modules.values():
            if "question_batches" in module_data:
                for batch in module_data["question_batches"]:
                    total += batch.get("count", 0)
        return total

    @property
    def module_batch_distribution(self) -> dict[str, list[dict[str, Any]]]:
        """Get question batch distribution per module."""
        distribution = {}
        for module_id, module_data in self.selected_modules.items():
            if "question_batches" in module_data:
                distribution[module_id] = module_data["question_batches"]
        return distribution

    # Pydantic validators for structure
    @field_validator("selected_modules")
    def validate_selected_modules(cls, v: Any) -> dict[str, dict[str, Any]]:
        """Ensure selected_modules has correct structure."""
        if not isinstance(v, dict):
            raise ValueError("selected_modules must be a dictionary")

        # Validate structure for each module
        for module_id, module_data in v.items():
            if not isinstance(module_data, dict):
                raise ValueError(f"Module {module_id} data must be a dictionary")

            # Check required fields
            if "name" not in module_data:
                raise ValueError(f"Module {module_id} missing required 'name' field")

            if "question_batches" not in module_data:
                raise ValueError(f"Module {module_id} missing required 'question_batches' field")

            # Validate types
            if not isinstance(module_data["name"], str):
                raise ValueError(f"Module {module_id} name must be string")

            if not isinstance(module_data["question_batches"], list):
                raise ValueError(f"Module {module_id} question_batches must be a list")

            # Validate batch structure
            if not module_data["question_batches"]:
                raise ValueError(f"Module {module_id} must have at least one question batch")

            if len(module_data["question_batches"]) > 4:
                raise ValueError(f"Module {module_id} cannot have more than 4 question batches")

            # Validate each batch
            for i, batch in enumerate(module_data["question_batches"]):
                if not isinstance(batch, dict):
                    raise ValueError(f"Module {module_id} batch {i} must be a dictionary")

                if "question_type" not in batch or "count" not in batch:
                    raise ValueError(f"Module {module_id} batch {i} missing required fields")

                if not isinstance(batch["count"], int):
                    raise ValueError(f"Module {module_id} batch {i} count must be integer")

                if not (1 <= batch["count"] <= 20):
                    raise ValueError(f"Module {module_id} batch {i} count must be between 1 and 20")

        return v

    @field_validator("extracted_content")
    def validate_extracted_content(cls, v: Any) -> dict[str, Any] | None:
        """Validate extracted content structure."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("extracted_content must be a dictionary")
        return v
```

**Key Changes:**
- Removed `question_type` and `question_count` fields
- Updated `selected_modules` validator for new structure with `question_batches`
- Added properties for batch distribution and total count calculation
- Enhanced validation for batch limits and structure

#### Step 3: Update Generation Service
**File: `backend/src/question/services/generation_service.py`**

```python
"""Module-based question generation service."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session

from ..providers import get_llm_provider_registry
from ..templates import get_template_manager
from ..types import QuizLanguage, QuestionType
from ..workflows.module_batch_workflow import ParallelModuleProcessor

logger = get_logger("generation_service")


class QuestionGenerationService:
    """Service for orchestrating module-based question generation."""

    def __init__(self) -> None:
        """Initialize question generation service."""
        self.provider_registry = get_llm_provider_registry()
        self.template_manager = get_template_manager()

    async def generate_questions_for_quiz_with_batch_tracking(
        self,
        quiz_id: UUID,
        extracted_content: dict[str, str],
        provider_name: str = "openai",
    ) -> dict[str, list[Any]]:
        """
        Generate questions for quiz with batch-level tracking and selective retry support.

        This method checks existing generation metadata to skip successfully completed batches
        and only process modules that need generation or retry.

        Args:
            quiz_id: Quiz identifier
            extracted_content: Module content mapped by module ID
            provider_name: LLM provider to use

        Returns:
            Dictionary mapping module IDs to lists of generated questions

        Raises:
            ValueError: If quiz not found or invalid parameters
            Exception: If generation fails
        """
        try:
            # Get quiz to access module configuration and metadata
            from src.quiz.models import Quiz

            async with get_async_session() as session:
                quiz = await session.get(Quiz, quiz_id)
                if not quiz:
                    raise ValueError(f"Quiz {quiz_id} not found")

                # Check generation metadata for successful batches to skip
                successful_batch_keys = set()
                if (
                    quiz.generation_metadata
                    and "successful_batches" in quiz.generation_metadata
                ):
                    successful_batch_keys = set(
                        quiz.generation_metadata["successful_batches"]
                    )

                logger.info(
                    "batch_tracking_generation_started",
                    quiz_id=str(quiz_id),
                    total_modules=len(quiz.selected_modules),
                    successful_batches_to_skip=len(successful_batch_keys),
                    provider=provider_name,
                )

                # Get provider instance
                from ..providers import LLMProvider

                provider_enum = LLMProvider(provider_name.lower())
                provider = self.provider_registry.get_provider(provider_enum)

                # Build modules to process with their batches
                modules_to_process = {}
                skipped_batches = []
                total_batches_to_process = 0

                for module_id, module_info in quiz.selected_modules.items():
                    module_name = module_info.get("name", "Unknown")

                    # Skip if no content extracted for this module
                    if module_id not in extracted_content:
                        logger.warning(
                            "batch_tracking_module_content_missing",
                            quiz_id=str(quiz_id),
                            module_id=module_id,
                            module_name=module_name,
                        )
                        continue

                    # Process each batch in the module
                    batches_to_process = []
                    for batch in module_info.get("question_batches", []):
                        question_type = batch["question_type"]
                        count = batch["count"]

                        # Create batch key
                        batch_key = f"{module_id}_{question_type}_{count}"

                        if batch_key in successful_batch_keys:
                            # Skip this batch - already successful
                            skipped_batches.append({
                                "module_id": module_id,
                                "module_name": module_name,
                                "batch_key": batch_key,
                                "question_type": question_type,
                                "count": count,
                                "reason": "already_successful",
                            })
                            logger.debug(
                                "batch_tracking_skipping_successful_batch",
                                quiz_id=str(quiz_id),
                                batch_key=batch_key,
                            )
                        else:
                            # Add to processing list
                            batches_to_process.append({
                                "question_type": QuestionType(question_type),
                                "count": count,
                                "batch_key": batch_key,
                            })
                            total_batches_to_process += 1

                    # Only add module if it has batches to process
                    if batches_to_process:
                        modules_to_process[module_id] = {
                            "name": module_name,
                            "content": extracted_content[module_id],
                            "batches": batches_to_process,
                        }

                logger.info(
                    "batch_tracking_modules_filtered",
                    quiz_id=str(quiz_id),
                    modules_to_process=len(modules_to_process),
                    total_batches_to_process=total_batches_to_process,
                    batches_skipped=len(skipped_batches),
                    skipped_details=skipped_batches,
                )

                # If no modules need processing, return empty results
                if not modules_to_process:
                    logger.info(
                        "batch_tracking_no_modules_to_process",
                        quiz_id=str(quiz_id),
                        reason="all_batches_already_successful_or_no_content",
                    )
                    return {}

                # Convert language string to enum
                language = (
                    QuizLanguage.NORWEGIAN
                    if quiz.language == "no"
                    else QuizLanguage.ENGLISH
                )

                # Process modules with their batches
                processor = ParallelModuleProcessor(
                    llm_provider=provider,
                    template_manager=self.template_manager,
                    language=language,
                )

                results = await processor.process_all_modules_with_batches(
                    quiz_id, modules_to_process
                )

                logger.info(
                    "batch_tracking_generation_completed",
                    quiz_id=str(quiz_id),
                    modules_processed=len(results),
                    total_questions_generated=sum(
                        len(questions) for questions in results.values()
                    ),
                )

                return results

        except Exception as e:
            logger.error(
                "batch_tracking_generation_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
            raise
```

**Key Changes:**
- Modified to process multiple batches per module
- Each batch gets its own batch key with question type
- Tracks skipped batches with question type information
- Passes batch information to the processor

#### Step 4: Update Module Batch Workflow
**File: `backend/src/question/workflows/module_batch_workflow.py`**

```python
"""Module batch workflow for parallel question generation."""

import asyncio
import json
from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from src.config import get_logger, settings
from src.database import get_async_session

from ..providers import BaseLLMProvider, LLMMessage
from ..templates.manager import TemplateManager, get_template_manager
from ..types import GenerationParameters, Question, QuestionType, QuizLanguage

logger = get_logger("module_batch_workflow")


class ModuleBatchState(BaseModel):
    """State for module batch generation workflow."""

    # Input parameters
    quiz_id: UUID
    module_id: str
    module_name: str
    module_content: str
    target_question_count: int
    language: QuizLanguage = QuizLanguage.ENGLISH
    question_type: QuestionType  # Now passed per batch, not at init

    # Provider configuration
    llm_provider: BaseLLMProvider
    template_manager: TemplateManager

    # Workflow state
    generated_questions: list[Question] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = Field(default_factory=lambda: settings.MAX_GENERATION_RETRIES)

    # JSON correction state
    parsing_error: bool = False
    correction_attempts: int = 0
    max_corrections: int = Field(default_factory=lambda: settings.MAX_JSON_CORRECTIONS)

    # Validation error state
    validation_error: bool = False
    validation_error_details: list[str] = Field(default_factory=list)
    validation_correction_attempts: int = 0
    max_validation_corrections: int = Field(
        default_factory=lambda: settings.MAX_JSON_CORRECTIONS
    )

    # Smart retry state for failed question tracking
    failed_questions_data: list[dict[str, Any]] = Field(default_factory=list)
    failed_questions_errors: list[str] = Field(default_factory=list)
    successful_questions_preserved: list[Question] = Field(default_factory=list)

    # Current LLM interaction
    system_prompt: str = ""
    user_prompt: str = ""
    raw_response: str = ""

    # Error handling
    error_message: str | None = None

    # Metadata
    workflow_metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class ModuleBatchWorkflow:
    """
    Workflow for generating multiple questions per module in batch.

    This workflow implements a self-healing JSON correction mechanism:
    1. If JSON parsing fails, it triggers a correction path
    2. The correction prompt includes the error and malformed JSON
    3. The LLM is asked to fix and return only valid JSON
    4. This can happen up to max_corrections times before failing

    This makes the system robust against common LLM formatting errors.
    """

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language
        # Removed: question_type initialization
        self.graph = self._build_graph()

    async def run(
        self,
        module_id: str,
        module_name: str,
        module_content: str,
        quiz_id: UUID,
        target_count: int,
        question_type: QuestionType,  # Now passed as parameter
    ) -> list[Question]:
        """
        Run the workflow to generate questions for a module batch.

        Args:
            module_id: Unique identifier for the module
            module_name: Human-readable module name
            module_content: Extracted text content from the module
            quiz_id: UUID of the parent quiz
            target_count: Number of questions to generate
            question_type: Type of questions to generate for this batch

        Returns:
            List of generated Question objects
        """
        initial_state = ModuleBatchState(
            quiz_id=quiz_id,
            module_id=module_id,
            module_name=module_name,
            module_content=module_content,
            target_question_count=target_count,
            language=self.language,
            question_type=question_type,  # Set from parameter
            llm_provider=self.llm_provider,
            template_manager=self.template_manager,
        )

        final_state = await self.graph.ainvoke(initial_state)
        return final_state["generated_questions"]

    # ... rest of the workflow implementation remains the same ...


class ParallelModuleProcessor:
    """Processor for handling multiple modules with multiple batches in parallel."""

    def __init__(
        self,
        llm_provider: BaseLLMProvider,
        template_manager: TemplateManager | None = None,
        language: QuizLanguage = QuizLanguage.ENGLISH,
    ):
        self.llm_provider = llm_provider
        self.template_manager = template_manager or get_template_manager()
        self.language = language

    async def process_all_modules_with_batches(
        self,
        quiz_id: UUID,
        modules_data: dict[str, dict[str, Any]],
    ) -> dict[str, list[Question]]:
        """
        Process all modules with their batches in parallel.

        Args:
            quiz_id: The quiz identifier
            modules_data: Dictionary with module data including batches:
                {
                    "module_id": {
                        "name": "Module Name",
                        "content": "...",
                        "batches": [
                            {"question_type": QuestionType, "count": int, "batch_key": str},
                            ...
                        ]
                    }
                }

        Returns:
            Dictionary mapping module IDs to lists of generated questions
        """
        # Create tasks for all batches across all modules
        tasks = []
        batch_info_map = {}  # Track which task belongs to which module/batch

        for module_id, module_info in modules_data.items():
            module_name = module_info["name"]
            module_content = module_info["content"]

            for batch in module_info["batches"]:
                question_type = batch["question_type"]
                count = batch["count"]
                batch_key = batch["batch_key"]

                # Create workflow for this specific batch
                workflow = ModuleBatchWorkflow(
                    llm_provider=self.llm_provider,
                    template_manager=self.template_manager,
                    language=self.language,
                )

                # Create task for this batch
                task = asyncio.create_task(
                    self._process_single_batch(
                        workflow,
                        module_id,
                        module_name,
                        module_content,
                        quiz_id,
                        count,
                        question_type,
                        batch_key,
                    )
                )

                tasks.append(task)
                batch_info_map[id(task)] = {
                    "module_id": module_id,
                    "batch_key": batch_key,
                    "question_type": question_type,
                }

        # Execute all batch tasks in parallel
        logger.info(
            "parallel_batch_processing_started",
            quiz_id=str(quiz_id),
            total_batches=len(tasks),
            modules_count=len(modules_data),
        )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and organize by module
        final_results = {}
        successful_batches = []
        failed_batches = []

        for task_idx, result in enumerate(results):
            task = tasks[task_idx]
            batch_info = batch_info_map[id(task)]
            module_id = batch_info["module_id"]
            batch_key = batch_info["batch_key"]

            if isinstance(result, Exception):
                logger.error(
                    "parallel_batch_processing_batch_failed",
                    quiz_id=str(quiz_id),
                    module_id=module_id,
                    batch_key=batch_key,
                    error=str(result),
                )
                failed_batches.append(batch_key)
            else:
                questions, metadata = result

                # Initialize module results if needed
                if module_id not in final_results:
                    final_results[module_id] = []

                # Add questions from this batch
                final_results[module_id].extend(questions)

                if questions:
                    successful_batches.append(batch_key)
                    logger.info(
                        "parallel_batch_processing_batch_completed",
                        quiz_id=str(quiz_id),
                        module_id=module_id,
                        batch_key=batch_key,
                        questions_generated=len(questions),
                    )
                else:
                    failed_batches.append(batch_key)

        # Update generation metadata
        await self._update_generation_metadata(
            quiz_id, successful_batches, failed_batches
        )

        logger.info(
            "parallel_batch_processing_completed",
            quiz_id=str(quiz_id),
            successful_batches=len(successful_batches),
            failed_batches=len(failed_batches),
            total_questions=sum(len(q) for q in final_results.values()),
        )

        return final_results

    async def _process_single_batch(
        self,
        workflow: ModuleBatchWorkflow,
        module_id: str,
        module_name: str,
        module_content: str,
        quiz_id: UUID,
        target_count: int,
        question_type: QuestionType,
        batch_key: str,
    ) -> tuple[list[Question], dict[str, Any]]:
        """
        Process a single batch for a module.

        Returns:
            Tuple of (questions, metadata)
        """
        try:
            logger.info(
                "processing_single_batch",
                quiz_id=str(quiz_id),
                module_id=module_id,
                batch_key=batch_key,
                question_type=question_type.value,
                target_count=target_count,
            )

            questions = await workflow.run(
                module_id=module_id,
                module_name=module_name,
                module_content=module_content,
                quiz_id=quiz_id,
                target_count=target_count,
                question_type=question_type,
            )

            metadata = {
                "batch_key": batch_key,
                "questions_generated": len(questions),
                "target_count": target_count,
                "question_type": question_type.value,
            }

            return questions, metadata

        except Exception as e:
            logger.error(
                "batch_processing_error",
                quiz_id=str(quiz_id),
                module_id=module_id,
                batch_key=batch_key,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _update_generation_metadata(
        self,
        quiz_id: UUID,
        successful_batches: list[str],
        failed_batches: list[str],
    ) -> None:
        """Update quiz generation metadata with batch results."""
        try:
            from src.quiz.models import Quiz

            async with get_async_session() as session:
                quiz = await session.get(Quiz, quiz_id)
                if quiz:
                    # Initialize metadata if needed
                    if not quiz.generation_metadata:
                        quiz.generation_metadata = {}

                    # Update successful batches
                    existing_successful = set(
                        quiz.generation_metadata.get("successful_batches", [])
                    )
                    existing_successful.update(successful_batches)
                    quiz.generation_metadata["successful_batches"] = list(
                        existing_successful
                    )

                    # Update failed batches (remove any that succeeded)
                    existing_failed = set(
                        quiz.generation_metadata.get("failed_batches", [])
                    )
                    existing_failed.update(failed_batches)
                    existing_failed -= existing_successful
                    quiz.generation_metadata["failed_batches"] = list(existing_failed)

                    # Force update of JSONB column
                    quiz.generation_metadata = {**quiz.generation_metadata}

                    session.add(quiz)
                    await session.commit()

        except Exception as e:
            logger.error(
                "metadata_update_failed",
                quiz_id=str(quiz_id),
                error=str(e),
                exc_info=True,
            )
```

**Key Changes:**
- `ModuleBatchWorkflow` now accepts `question_type` as a parameter in `run()` method
- Removed `question_type` from workflow initialization
- `ParallelModuleProcessor` processes multiple batches per module
- Each batch is processed independently with its own question type
- Batch tracking maintains the same key format

#### Step 5: Update Quiz Orchestrator
**File: `backend/src/quiz/orchestrator.py`**

Locate the question generation orchestration sections and update them to remove the single question_type parameter. The orchestrator should now rely on the generation service to handle multiple question types per module.

```python
# In the question generation orchestration function, update calls like:

# OLD:
# processor = ParallelModuleProcessor(
#     llm_provider=provider,
#     template_manager=self.template_manager,
#     language=language,
#     question_type=quiz.question_type,  # Remove this
# )

# NEW:
processor = ParallelModuleProcessor(
    llm_provider=provider,
    template_manager=self.template_manager,
    language=language,
)
```

#### Step 6: Update Quiz Service
**File: `backend/src/quiz/service.py`**

Update the quiz creation logic to handle the new schema structure:

```python
async def create_quiz(
    session: AsyncSession,
    quiz_create: QuizCreate,
    owner_id: UUID,
) -> Quiz:
    """Create a new quiz with module-based question batches."""
    # Convert ModuleSelection objects to dict for storage
    selected_modules_dict = {}
    for module_id, module_selection in quiz_create.selected_modules.items():
        if isinstance(module_selection, ModuleSelection):
            # Convert to dict with proper structure
            selected_modules_dict[module_id] = {
                "name": module_selection.name,
                "question_batches": [
                    {
                        "question_type": batch.question_type.value,
                        "count": batch.count,
                    }
                    for batch in module_selection.question_batches
                ],
            }
        else:
            # Already a dict, ensure question types are strings
            batches = []
            for batch in module_selection.get("question_batches", []):
                batches.append({
                    "question_type": (
                        batch["question_type"].value
                        if hasattr(batch.get("question_type"), "value")
                        else batch["question_type"]
                    ),
                    "count": batch["count"],
                })
            selected_modules_dict[module_id] = {
                "name": module_selection["name"],
                "question_batches": batches,
            }

    quiz = Quiz(
        owner_id=owner_id,
        canvas_course_id=quiz_create.canvas_course_id,
        canvas_course_name=quiz_create.canvas_course_name,
        selected_modules=selected_modules_dict,
        title=quiz_create.title,
        llm_model=quiz_create.llm_model,
        llm_temperature=quiz_create.llm_temperature,
        language=quiz_create.language,
        # Note: question_type field removed
    )

    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)

    logger.info(
        "quiz_created",
        quiz_id=str(quiz.id),
        total_modules=len(quiz.selected_modules),
        total_questions=quiz.total_question_count,
    )

    return quiz
```

### 4.3 Data Models & Schemas

#### Request Structure
```json
{
  "canvas_course_id": 12345,
  "canvas_course_name": "Introduction to Biology",
  "title": "Midterm Quiz",
  "selected_modules": {
    "module_001": {
      "name": "Cell Structure",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 10},
        {"question_type": "fill_in_blank", "count": 5}
      ]
    },
    "module_002": {
      "name": "Photosynthesis",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 15},
        {"question_type": "matching", "count": 3},
        {"question_type": "categorization", "count": 2}
      ]
    }
  },
  "llm_model": "o3",
  "llm_temperature": 1.0,
  "language": "en"
}
```

#### Database Structure
The `selected_modules` JSONB field stores:
```json
{
  "module_id": {
    "name": "Module Name",
    "question_batches": [
      {"question_type": "multiple_choice", "count": 10},
      {"question_type": "fill_in_blank", "count": 5}
    ]
  }
}
```

#### Generation Metadata Structure
```json
{
  "successful_batches": [
    "module_001_multiple_choice_10",
    "module_001_fill_in_blank_5",
    "module_002_multiple_choice_15"
  ],
  "failed_batches": [
    "module_002_matching_3",
    "module_002_categorization_2"
  ],
  "batch_details": {
    "module_001_multiple_choice_10": {
      "generated_count": 10,
      "target_count": 10,
      "timestamp": "2025-01-15T10:30:00Z"
    }
  }
}
```

### 4.4 Configuration

No new configuration parameters are required. The existing settings apply:

```python
# backend/src/config.py
MAX_GENERATION_RETRIES = 3  # Per batch retries
MAX_JSON_CORRECTIONS = 3    # JSON fix attempts
```

Validation limits are hardcoded:
- Max 4 batches per module
- Max 20 questions per batch
- Min 1 question per batch
- Min 1 batch per module

## 5. Testing Strategy

### Unit Tests

#### Test Quiz Schema Validation
```python
# backend/tests/quiz/test_quiz_schemas.py

def test_question_batch_validation():
    """Test QuestionBatch schema validation."""
    # Valid batch
    batch = QuestionBatch(
        question_type=QuestionType.MULTIPLE_CHOICE,
        count=10
    )
    assert batch.count == 10

    # Invalid count
    with pytest.raises(ValidationError):
        QuestionBatch(question_type=QuestionType.FILL_IN_BLANK, count=25)

def test_module_selection_validation():
    """Test ModuleSelection with multiple batches."""
    # Valid module with multiple batches
    module = ModuleSelection(
        name="Test Module",
        question_batches=[
            QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10),
            QuestionBatch(question_type=QuestionType.FILL_IN_BLANK, count=5),
        ]
    )
    assert module.total_questions == 15

    # Too many batches
    with pytest.raises(ValidationError):
        ModuleSelection(
            name="Test Module",
            question_batches=[
                QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=5),
                QuestionBatch(question_type=QuestionType.FILL_IN_BLANK, count=5),
                QuestionBatch(question_type=QuestionType.MATCHING, count=5),
                QuestionBatch(question_type=QuestionType.CATEGORIZATION, count=5),
                QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=3),  # 5th batch
            ]
        )

def test_quiz_create_no_duplicate_types():
    """Test that duplicate question types in same module are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        QuizCreate(
            canvas_course_id=123,
            canvas_course_name="Test Course",
            title="Test Quiz",
            selected_modules={
                "mod1": ModuleSelection(
                    name="Module 1",
                    question_batches=[
                        QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=10),
                        QuestionBatch(question_type=QuestionType.MULTIPLE_CHOICE, count=5),  # Duplicate
                    ]
                )
            }
        )
    assert "duplicate question types" in str(exc_info.value)
```

#### Test Generation Service
```python
# backend/tests/question/test_generation_service.py

async def test_multiple_batches_per_module():
    """Test generation of multiple question types per module."""
    # Create quiz with multiple batches
    quiz = await create_test_quiz(
        selected_modules={
            "mod1": {
                "name": "Module 1",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 5},
                    {"question_type": "fill_in_blank", "count": 3},
                ]
            }
        }
    )

    # Mock content
    extracted_content = {"mod1": "Test content for module 1"}

    # Generate questions
    service = QuestionGenerationService()
    results = await service.generate_questions_for_quiz_with_batch_tracking(
        quiz.id, extracted_content, "mock"
    )

    # Verify results
    assert "mod1" in results
    assert len(results["mod1"]) == 8  # 5 MCQ + 3 FIB

    # Check batch keys in metadata
    async with get_async_session() as session:
        updated_quiz = await session.get(Quiz, quiz.id)
        successful_batches = updated_quiz.generation_metadata.get("successful_batches", [])
        assert "mod1_multiple_choice_5" in successful_batches
        assert "mod1_fill_in_blank_3" in successful_batches
```

### Integration Tests

```python
# backend/tests/test_quiz_creation_flow.py

async def test_full_quiz_creation_with_multiple_types():
    """Test complete flow from creation to generation."""
    # Create quiz via API
    quiz_data = {
        "canvas_course_id": 12345,
        "canvas_course_name": "Test Course",
        "title": "Integration Test Quiz",
        "selected_modules": {
            "mod1": {
                "name": "Module 1",
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 10},
                    {"question_type": "matching", "count": 3},
                ]
            },
            "mod2": {
                "name": "Module 2",
                "question_batches": [
                    {"question_type": "fill_in_blank", "count": 5},
                ]
            }
        },
        "language": "en"
    }

    response = await client.post("/api/v1/quizzes", json=quiz_data)
    assert response.status_code == 200
    quiz = response.json()

    # Verify structure
    assert quiz["selected_modules"]["mod1"]["question_batches"][0]["count"] == 10
    assert len(quiz["selected_modules"]["mod1"]["question_batches"]) == 2

    # Trigger generation (would be done via orchestrator)
    # ... generation tests ...
```

### Manual Testing Steps

1. **Create Quiz with Multiple Types**:
   - POST to `/api/v1/quizzes` with multiple batches per module
   - Verify response structure
   - Check database for correct storage

2. **Test Batch Limits**:
   - Try creating quiz with 5 batches (should fail)
   - Try creating quiz with 25 questions per batch (should fail)
   - Try creating quiz with 0 batches (should fail)

3. **Test Generation**:
   - Create quiz with 2 modules, 2 batches each
   - Monitor logs for parallel processing
   - Verify batch keys in generation_metadata

4. **Test Partial Retry**:
   - Simulate failure for one batch
   - Retry generation
   - Verify only failed batch is regenerated

### Performance Benchmarks

- **Parallel Processing**: All batches for all modules should process concurrently
- **Expected Times** (with mock provider):
  - 1 module, 1 batch: ~1 second
  - 1 module, 4 batches: ~1-2 seconds (parallel)
  - 5 modules, 4 batches each: ~2-3 seconds (all parallel)

## 6. Deployment Instructions

### Step 1: Database Migration
Since the database is empty (per requirements), no migration needed. The JSONB column supports the new structure.

### Step 2: Update Backend
```bash
# From project root
cd backend

# Run tests first
source .venv/bin/activate
bash scripts/test.sh

# If tests pass, restart backend
docker compose restart backend
```

### Step 3: Verify API
```bash
# Test new endpoint structure
curl -X POST http://localhost:8000/api/v1/quizzes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "canvas_course_id": 123,
    "canvas_course_name": "Test",
    "title": "Test Quiz",
    "selected_modules": {
      "mod1": {
        "name": "Module 1",
        "question_batches": [
          {"question_type": "multiple_choice", "count": 5}
        ]
      }
    }
  }'
```

### Rollback Procedure
If issues arise:
```bash
# Revert to previous version
git checkout main
docker compose down
docker compose up -d
```

## 7. Monitoring & Maintenance

### Key Metrics to Monitor

1. **Batch Processing Metrics**:
   - Log pattern: `"parallel_batch_processing_started"`
   - Track: total_batches, modules_count
   - Alert if: batch count > 20 (indicates validation bypass)

2. **Batch Success Rates**:
   - Log pattern: `"parallel_batch_processing_completed"`
   - Track: successful_batches vs failed_batches ratio
   - Alert if: failure rate > 30%

3. **Performance Metrics**:
   - Track time between `processing_started` and `processing_completed`
   - Alert if: processing time > 60 seconds for < 20 batches

### Log Entries to Watch

```python
# Successful batch generation
{
  "event": "parallel_batch_processing_batch_completed",
  "quiz_id": "...",
  "module_id": "mod1",
  "batch_key": "mod1_multiple_choice_10",
  "questions_generated": 10
}

# Failed batch
{
  "event": "parallel_batch_processing_batch_failed",
  "quiz_id": "...",
  "module_id": "mod1",
  "batch_key": "mod1_matching_5",
  "error": "LLM timeout"
}

# Validation errors
{
  "event": "quiz_validation_error",
  "error": "Module mod1 cannot have more than 4 question batches"
}
```

### Common Issues & Troubleshooting

1. **"Module missing required 'question_batches' field"**
   - Cause: Frontend sending old format
   - Fix: Ensure frontend updated or add compatibility layer

2. **"Duplicate question types"**
   - Cause: Same question type twice in one module
   - Fix: Validate in frontend or merge duplicates

3. **Batch generation timeout**
   - Cause: Too many parallel requests to LLM
   - Fix: Consider rate limiting or queue system

4. **Missing questions in result**
   - Cause: Some batches failed
   - Fix: Check generation_metadata for failed_batches

## 8. Security Considerations

### Input Validation
- All batch counts validated (1-20 range)
- Maximum 4 batches per module enforced
- Question types validated against enum

### Data Privacy
- No change to existing privacy model
- Question batches stored in same JSONB field as before
- No new PII exposure

### Authorization
- Existing quiz ownership checks apply
- No new endpoints or permissions needed

### Rate Limiting
- Consider implementing rate limits for large batch counts
- Current parallel processing could overwhelm LLM providers

## 9. Future Considerations

### Known Limitations

1. **Fixed Batch Limits**:
   - Hard-coded max 4 batches per module
   - Consider making configurable

2. **No Batch Priority**:
   - All batches process with equal priority
   - Could add priority for certain question types

3. **No Cross-Module Deduplication**:
   - Same content might generate similar questions across modules
   - Future: implement similarity detection

### Potential Improvements

1. **Smart Batch Distribution**:
   - Auto-suggest question type distribution based on content
   - ML model to recommend optimal mix

2. **Batch Templates**:
   - Save common batch configurations
   - "Apply template" option for quick setup

3. **Progressive Generation**:
   - Start showing results as batches complete
   - Don't wait for all batches to finish

4. **Batch Dependencies**:
   - Allow batches to reference each other
   - E.g., "Generate matching questions from MCQ distractors"

### Scalability Considerations

1. **Database**:
   - JSONB queries might slow with many quizzes
   - Consider indexing generation_metadata->successful_batches

2. **LLM Provider Limits**:
   - 20 modules × 4 batches = 80 parallel requests max
   - Implement request queuing for large quizzes

3. **Memory Usage**:
   - Large batches hold all questions in memory
   - Consider streaming for very large generations

4. **Frontend Updates**:
   - Current frontend shows single question type
   - Need UI for batch management
   - Progress tracking per batch

## Appendix: Complete Example Flow

```python
# 1. User creates quiz with multiple question types
POST /api/v1/quizzes
{
  "canvas_course_id": 12345,
  "canvas_course_name": "Biology 101",
  "title": "Chapter 3-5 Quiz",
  "selected_modules": {
    "mod_ch3": {
      "name": "Chapter 3: Cell Structure",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 15},
        {"question_type": "fill_in_blank", "count": 5}
      ]
    },
    "mod_ch4": {
      "name": "Chapter 4: Cell Division",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 10},
        {"question_type": "matching", "count": 3},
        {"question_type": "categorization", "count": 2}
      ]
    },
    "mod_ch5": {
      "name": "Chapter 5: Photosynthesis",
      "question_batches": [
        {"question_type": "multiple_choice", "count": 20}
      ]
    }
  },
  "language": "en",
  "llm_model": "o3",
  "llm_temperature": 1.0
}

# 2. System generates batch keys:
# - mod_ch3_multiple_choice_15
# - mod_ch3_fill_in_blank_5
# - mod_ch4_multiple_choice_10
# - mod_ch4_matching_3
# - mod_ch4_categorization_2
# - mod_ch5_multiple_choice_20

# 3. All 6 batches process in parallel

# 4. If mod_ch4_matching_3 fails:
# - generation_metadata.successful_batches has 5 items
# - generation_metadata.failed_batches has ["mod_ch4_matching_3"]

# 5. User retries failed batches
# - Only mod_ch4_matching_3 regenerates
# - Other 5 batches remain unchanged
```

This implementation provides a robust, scalable solution for generating multiple question types per module while maintaining backward compatibility with the existing retry mechanism and batch tracking system.
