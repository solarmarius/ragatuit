# 21. Question Generator Modularization

## Priority: High

**Estimated Effort**: 5 weeks (phased implementation)
**Python Version**: 3.10+
**Dependencies**: SQLModel, Pydantic, LangChain, Multiple LLM SDKs

## Problem Statement

### Current Situation

The question generation system is tightly coupled to multiple-choice questions (MCQ) and OpenAI as the sole LLM provider. This rigid architecture prevents the system from supporting diverse question types (true/false, matching, short answer) and alternative LLM providers (Anthropic, Google, local models).

### Why It's a Problem

- **Limited Question Variety**: Only 4-option multiple choice questions
- **Vendor Lock-in**: Hardcoded dependency on OpenAI
- **Rigid Database Schema**: Fixed columns for options A-D
- **Poor Extensibility**: Adding new question types requires major refactoring
- **Canvas Integration Limitations**: Only supports "choice" interaction type
- **No Provider Flexibility**: Cannot switch or mix LLM providers
- **Testing Complexity**: Tightly coupled components are hard to test

### Affected Modules

- `app/models.py` - Question model with fixed MCQ structure
- `app/services/mcq_generation.py` - Hardcoded for OpenAI MCQ
- `app/services/canvas_quiz_export.py` - Limited to MCQ export
- `app/api/routes/quiz.py` - MCQ-specific endpoints
- Database schema with fixed option columns

### Technical Debt Assessment

- **Risk Level**: High - Blocks product evolution
- **Impact**: Core functionality limitation
- **Cost of Delay**: Increases with each MCQ-only feature

## Current Implementation Analysis

```python
# File: app/models.py (current rigid MCQ structure)
class Question(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: uuid.UUID = Field(foreign_key="quiz.id", nullable=False)

    # PROBLEM: Fixed MCQ structure
    question_text: str = Field(min_length=1, max_length=1000)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(regex="^[A-D]$")  # Only A, B, C, or D

    # PROBLEM: No question type field
    # PROBLEM: No flexibility for other formats

# File: app/services/mcq_generation.py (OpenAI coupling)
from langchain_openai import ChatOpenAI

class MCQGenerationService:
    def __init__(self):
        # PROBLEM: Hardcoded OpenAI
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=1,
            api_key=settings.OPENAI_API_KEY,
        )

    def _create_mcq_prompt(self, content: str) -> str:
        # PROBLEM: Fixed prompt for MCQ only
        return f"""Generate a multiple-choice question with:
        - Exactly 4 options (A, B, C, D)
        - Only one correct answer
        ..."""

# File: app/services/canvas_quiz_export.py (limited export)
def _convert_question_to_canvas_item(self, question: Question):
    # PROBLEM: Only handles MCQ format
    return {
        "interaction_type_slug": "choice",  # Hardcoded!
        "interaction_data": {
            "choices": [
                {"id": "A", "text": question.option_a},
                {"id": "B", "text": question.option_b},
                {"id": "C", "text": question.option_c},
                {"id": "D", "text": question.option_d},
            ]
        }
    }

# Current limitations:
# 1. Cannot create true/false questions
# 2. Cannot use Claude or Gemini
# 3. Cannot have 5 or 6 option MCQs
# 4. Cannot create matching questions
# 5. Cannot mix question types in one quiz
```

### Database Constraints

```sql
-- Current schema problems:
-- Fixed columns for exactly 4 options
-- No question type discrimination
-- No flexible data storage
-- Wasted space for non-MCQ questions

CREATE TABLE question (
    id UUID PRIMARY KEY,
    quiz_id UUID REFERENCES quiz(id),
    question_text TEXT NOT NULL,
    option_a VARCHAR(500) NOT NULL,  -- Wasted for T/F
    option_b VARCHAR(500) NOT NULL,  -- Wasted for T/F
    option_c VARCHAR(500) NOT NULL,  -- Always empty for T/F
    option_d VARCHAR(500) NOT NULL,  -- Always empty for T/F
    correct_answer CHAR(1) CHECK (correct_answer IN ('A','B','C','D'))
);
```

### Python Anti-patterns Identified

- **Tight Coupling**: Service tied to specific LLM provider
- **Rigid Data Model**: Fixed structure prevents extension
- **No Abstraction**: Direct implementation without interfaces
- **Missing Polymorphism**: No base class for question types
- **Hard-coded Logic**: Question format baked into code

## Proposed Solution

### Pythonic Approach

Implement a modular architecture using abstract base classes, strategy pattern for question generation, provider abstraction for LLMs, and polymorphic storage with JSONB for flexible question data.

### Architecture Overview

1. **Polymorphic Question Models**: Base class with type-specific implementations
2. **LLM Provider Abstraction**: Interface for multiple providers
3. **Strategy Pattern**: Different strategies for each question type
4. **Flexible Storage**: JSONB for variable question data
5. **Factory Pattern**: Dynamic question and provider creation

### Code Examples

```python
# File: app/models/questions/base.py (NEW - Question abstraction)
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

class QuestionType(str, Enum):
    """Supported question types."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    MATCHING = "matching"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_IN_BLANK = "fill_in_blank"

class QuestionBase(SQLModel, ABC):
    """Abstract base for all question types."""

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    quiz_id: UUID = Field(foreign_key="quiz.id", nullable=False)
    question_type: QuestionType
    question_text: str = Field(min_length=1, max_length=2000)
    points: float = Field(default=1.0, ge=0)
    is_approved: bool = Field(default=False)
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    display_order: int = Field(default=0)

    @abstractmethod
    def to_canvas_format(self) -> Dict[str, Any]:
        """Convert to Canvas quiz item format."""
        pass

    @abstractmethod
    def validate_answer(self, answer: Any) -> bool:
        """Validate if given answer is correct."""
        pass

    @abstractmethod
    def get_answer_key(self) -> Any:
        """Get the correct answer(s)."""
        pass

    @abstractmethod
    def to_display_format(self) -> Dict[str, Any]:
        """Convert to frontend display format."""
        pass

# File: app/models/questions/storage.py (NEW - Polymorphic storage)
class Question(QuestionBase, table=True):
    """Polymorphic question storage with flexible data."""

    # Store type-specific data as JSONB
    question_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False)
    )

    def get_typed_instance(self) -> QuestionBase:
        """Return properly typed question instance."""

        from app.models.questions import (
            MultipleChoiceQuestion,
            TrueFalseQuestion,
            MatchingQuestion,
            ShortAnswerQuestion,
        )

        type_map = {
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceQuestion,
            QuestionType.TRUE_FALSE: TrueFalseQuestion,
            QuestionType.MATCHING: MatchingQuestion,
            QuestionType.SHORT_ANSWER: ShortAnswerQuestion,
        }

        question_class = type_map.get(self.question_type)
        if not question_class:
            raise ValueError(f"Unknown question type: {self.question_type}")

        # Create typed instance with data
        return question_class(
            **self.model_dump(exclude={"question_data"}),
            **self.question_data
        )

    @classmethod
    def from_typed(cls, typed_question: QuestionBase) -> "Question":
        """Create storage instance from typed question."""

        # Extract base fields
        base_data = typed_question.model_dump(
            exclude={"question_data"},
            exclude_unset=True
        )

        # Extract type-specific data
        type_fields = set(typed_question.model_fields.keys()) - set(QuestionBase.model_fields.keys())
        type_data = {
            field: getattr(typed_question, field)
            for field in type_fields
            if hasattr(typed_question, field)
        }

        return cls(
            **base_data,
            question_data=type_data
        )

# File: app/models/questions/multiple_choice.py (NEW)
from pydantic import BaseModel, Field as PydanticField
from typing import List, Optional

class MCQOption(BaseModel):
    """Single option in multiple choice question."""
    id: str
    text: str
    feedback: Optional[str] = None

class MultipleChoiceQuestion(QuestionBase):
    """Multiple choice question with flexible options."""

    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: List[MCQOption] = PydanticField(min_items=2, max_items=10)
    correct_answers: List[str] = PydanticField(min_items=1)
    shuffle_options: bool = True
    allow_multiple: bool = False

    def to_canvas_format(self) -> Dict[str, Any]:
        """Convert to Canvas multiple choice format."""

        choices = [
            {
                "id": f"choice_{opt.id}",
                "position": i,
                "item_body": f"<p>{opt.text}</p>",
            }
            for i, opt in enumerate(self.options)
        ]

        # Handle single or multiple correct answers
        if len(self.correct_answers) == 1:
            scoring_data = {"value": f"choice_{self.correct_answers[0]}"}
            interaction_type = "choice"
        else:
            scoring_data = {
                "value": [f"choice_{ans}" for ans in self.correct_answers]
            }
            interaction_type = "multiple_answers"

        return {
            "interaction_type_slug": interaction_type,
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {
                "choices": choices,
                "shuffle": self.shuffle_options
            },
            "scoring_algorithm": "Equivalence",
            "scoring_data": scoring_data,
            "points_possible": self.points,
        }

    def validate_answer(self, answer: str | List[str]) -> bool:
        """Check if answer is correct."""
        if isinstance(answer, str):
            answer = [answer]
        return set(answer) == set(self.correct_answers)

    def get_answer_key(self) -> List[str]:
        """Get correct answer IDs."""
        return self.correct_answers

    def to_display_format(self) -> Dict[str, Any]:
        """Format for frontend display."""
        return {
            "id": str(self.id),
            "type": self.question_type,
            "text": self.question_text,
            "options": [opt.model_dump() for opt in self.options],
            "allow_multiple": self.allow_multiple,
            "points": self.points,
        }

# File: app/models/questions/true_false.py (NEW)
class TrueFalseQuestion(QuestionBase):
    """True/False question type."""

    question_type: QuestionType = QuestionType.TRUE_FALSE
    correct_answer: bool
    true_feedback: Optional[str] = None
    false_feedback: Optional[str] = None

    def to_canvas_format(self) -> Dict[str, Any]:
        """Convert to Canvas true/false format."""
        return {
            "interaction_type_slug": "true_false",
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {
                "true_choice": {
                    "id": "true",
                    "text": "True",
                    "feedback": self.true_feedback
                },
                "false_choice": {
                    "id": "false",
                    "text": "False",
                    "feedback": self.false_feedback
                }
            },
            "scoring_algorithm": "Equivalence",
            "scoring_data": {"value": str(self.correct_answer).lower()},
            "points_possible": self.points,
        }

    def validate_answer(self, answer: bool | str) -> bool:
        """Check if answer is correct."""
        if isinstance(answer, str):
            answer = answer.lower() == "true"
        return answer == self.correct_answer

    def get_answer_key(self) -> bool:
        """Get correct answer."""
        return self.correct_answer

    def to_display_format(self) -> Dict[str, Any]:
        """Format for frontend display."""
        return {
            "id": str(self.id),
            "type": self.question_type,
            "text": self.question_text,
            "points": self.points,
        }

# File: app/models/questions/matching.py (NEW)
class MatchingPair(BaseModel):
    """A matching pair in matching question."""
    left_id: str
    left_text: str
    right_id: str
    right_text: str

class MatchingQuestion(QuestionBase):
    """Matching question type."""

    question_type: QuestionType = QuestionType.MATCHING
    pairs: List[MatchingPair] = PydanticField(min_items=2, max_items=10)
    instructions: Optional[str] = None
    shuffle_left: bool = True
    shuffle_right: bool = True

    def to_canvas_format(self) -> Dict[str, Any]:
        """Convert to Canvas matching format."""
        return {
            "interaction_type_slug": "matching",
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {
                "left_items": [
                    {"id": pair.left_id, "text": pair.left_text}
                    for pair in self.pairs
                ],
                "right_items": [
                    {"id": pair.right_id, "text": pair.right_text}
                    for pair in self.pairs
                ],
                "instructions": self.instructions,
            },
            "scoring_algorithm": "Matching",
            "scoring_data": {
                "matches": [
                    {"left": pair.left_id, "right": pair.right_id}
                    for pair in self.pairs
                ]
            },
            "points_possible": self.points * len(self.pairs),
        }

    def validate_answer(self, answer: Dict[str, str]) -> bool:
        """Check if all matches are correct."""
        correct_matches = {
            pair.left_id: pair.right_id
            for pair in self.pairs
        }
        return answer == correct_matches

    def get_answer_key(self) -> Dict[str, str]:
        """Get correct matches."""
        return {pair.left_id: pair.right_id for pair in self.pairs}

    def to_display_format(self) -> Dict[str, Any]:
        """Format for frontend display."""
        return {
            "id": str(self.id),
            "type": self.question_type,
            "text": self.question_text,
            "instructions": self.instructions,
            "left_items": [
                {"id": p.left_id, "text": p.left_text}
                for p in self.pairs
            ],
            "right_items": [
                {"id": p.right_id, "text": p.right_text}
                for p in self.pairs
            ],
            "points": self.points * len(self.pairs),
        }

# File: app/services/llm/base.py (NEW - LLM abstraction)
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel

class LLMResponse(BaseModel):
    """Standardized LLM response."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model: str
    provider: str

class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text completion."""
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Count tokens in text."""
        pass

    @abstractmethod
    def get_max_context_length(self) -> int:
        """Get maximum context window."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass

# File: app/services/llm/openai_provider.py (NEW)
from langchain_openai import ChatOpenAI
import tiktoken

class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""

    provider_name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4"):
        super().__init__(api_key, model)
        self._client = None
        self._tokenizer = None

    @property
    def client(self):
        if not self._client:
            self._client = ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                timeout=settings.LLM_API_TIMEOUT,
            )
        return self._client

    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using OpenAI."""
        try:
            response = await self.client.ainvoke(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return LLMResponse(
                success=True,
                content=response.content,
                usage={
                    "prompt_tokens": response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.response_metadata.get("token_usage", {}).get("completion_tokens", 0),
                },
                model=self.model,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(
                "openai_completion_failed",
                error=str(e),
                model=self.model
            )
            return LLMResponse(
                success=False,
                error=str(e),
                model=self.model,
                provider=self.provider_name
            )

    def get_token_count(self, text: str) -> int:
        """Count tokens using tiktoken."""
        if not self._tokenizer:
            self._tokenizer = tiktoken.encoding_for_model(self.model)
        return len(self._tokenizer.encode(text))

    def get_max_context_length(self) -> int:
        """Get model context window."""
        context_lengths = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4o": 128000,
            "gpt-3.5-turbo": 4096,
        }
        return context_lengths.get(self.model, 4096)

# File: app/services/llm/anthropic_provider.py (NEW)
from anthropic import AsyncAnthropic

class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation."""

    provider_name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        super().__init__(api_key, model)
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Claude."""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            return LLMResponse(
                success=True,
                content=response.content[0].text,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                },
                model=self.model,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(
                "anthropic_completion_failed",
                error=str(e),
                model=self.model
            )
            return LLMResponse(
                success=False,
                error=str(e),
                model=self.model,
                provider=self.provider_name
            )

    def get_token_count(self, text: str) -> int:
        """Estimate token count."""
        # Anthropic doesn't provide tokenizer, use approximation
        return len(text) // 4

    def get_max_context_length(self) -> int:
        """Get model context window."""
        return 200000  # Claude 3 context window

# File: app/services/generation/strategies/base.py (NEW)
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, Any

T = TypeVar('T', bound=QuestionBase)

class QuestionGenerationStrategy(ABC, Generic[T]):
    """Abstract strategy for generating specific question types."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the prompt template for this question type."""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> T:
        """Parse LLM response into question object."""
        pass

    @abstractmethod
    def validate_response(self, response: str) -> bool:
        """Validate if response is properly formatted."""
        pass

    async def generate_question(
        self,
        content: str,
        difficulty: str = "medium",
        temperature: float = 1.0,
        **kwargs
    ) -> T:
        """Generate a question from content."""

        prompt = self.get_prompt_template().format(
            content=content,
            difficulty=difficulty,
            **kwargs
        )

        llm_response = await self.provider.generate_completion(
            prompt,
            temperature=temperature
        )

        if not llm_response.success:
            raise ValueError(f"LLM generation failed: {llm_response.error}")

        if not self.validate_response(llm_response.content):
            raise ValueError("Invalid response format from LLM")

        return self.parse_response(llm_response.content)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response."""
        import re

        # Try to find JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find JSON without code block
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return text

# File: app/services/generation/strategies/multiple_choice.py (NEW)
import json
from typing import List

class MultipleChoiceStrategy(QuestionGenerationStrategy[MultipleChoiceQuestion]):
    """Strategy for generating multiple choice questions."""

    def get_prompt_template(self) -> str:
        return """You are an expert educator creating multiple-choice questions.

Based on the following content, generate ONE high-quality multiple-choice question.

Content:
{content}

Requirements:
- Create exactly {num_options} options
- Make all options plausible but only {num_correct} should be correct
- Options should be similar in length and complexity
- Test understanding and application, not just memorization
- Use clear, concise language
- Difficulty level: {difficulty}

Return your response as valid JSON:
{{
    "question_text": "Your question here",
    "options": [
        {{"id": "0", "text": "First option"}},
        {{"id": "1", "text": "Second option"}},
        ...
    ],
    "correct_answers": ["0"],  // Array of correct option IDs
    "explanation": "Brief explanation of why this is the correct answer"
}}
"""

    def parse_response(self, response: str) -> MultipleChoiceQuestion:
        """Parse JSON response into MCQ object."""
        json_text = self._extract_json(response)
        data = json.loads(json_text)

        # Convert to MCQOption objects
        options = [
            MCQOption(id=opt["id"], text=opt["text"])
            for opt in data["options"]
        ]

        return MultipleChoiceQuestion(
            question_text=data["question_text"],
            options=options,
            correct_answers=data["correct_answers"],
            allow_multiple=len(data["correct_answers"]) > 1
        )

    def validate_response(self, response: str) -> bool:
        """Validate response format."""
        try:
            json_text = self._extract_json(response)
            data = json.loads(json_text)

            required = ["question_text", "options", "correct_answers"]
            if not all(field in data for field in required):
                return False

            # Validate options structure
            if not isinstance(data["options"], list) or len(data["options"]) < 2:
                return False

            for opt in data["options"]:
                if not all(key in opt for key in ["id", "text"]):
                    return False

            return True
        except:
            return False

# File: app/services/generation/service.py (NEW - Unified service)
from typing import Type, List, Dict, Any

class QuestionGenerationService:
    """Unified service for generating questions with any provider."""

    def __init__(self):
        # Provider registry
        self._providers: Dict[str, Type[LLMProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
        }

        # Strategy registry
        self._strategies: Dict[QuestionType, Type[QuestionGenerationStrategy]] = {
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceStrategy,
            QuestionType.TRUE_FALSE: TrueFalseStrategy,
            QuestionType.MATCHING: MatchingStrategy,
        }

    def get_provider(
        self,
        provider_name: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> LLMProvider:
        """Get configured LLM provider."""

        provider_class = self._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Get API key from settings if not provided
        if not api_key:
            api_key = getattr(settings, f"{provider_name.upper()}_API_KEY", None)
            if not api_key:
                raise ValueError(f"No API key configured for {provider_name}")

        # Use default model if not specified
        if not model:
            model = getattr(settings, f"DEFAULT_{provider_name.upper()}_MODEL", None)
            if not model:
                raise ValueError(f"No default model configured for {provider_name}")

        return provider_class(api_key=api_key, model=model)

    def get_strategy(
        self,
        question_type: QuestionType,
        provider: LLMProvider
    ) -> QuestionGenerationStrategy:
        """Get generation strategy for question type."""

        strategy_class = self._strategies.get(question_type)
        if not strategy_class:
            raise ValueError(f"No strategy for question type: {question_type}")

        return strategy_class(provider)

    async def generate_questions(
        self,
        content: str,
        question_types: List[QuestionType],
        quiz_id: UUID,
        provider_name: str = "openai",
        model: Optional[str] = None,
        temperature: float = 1.0,
        count_per_type: int = 1,
        **kwargs
    ) -> List[QuestionBase]:
        """Generate questions of multiple types."""

        # Get provider
        provider = self.get_provider(provider_name, model)

        generated_questions = []

        for question_type in question_types:
            strategy = self.get_strategy(question_type, provider)

            # Type-specific parameters
            type_params = self._get_type_parameters(question_type, **kwargs)

            for i in range(count_per_type):
                try:
                    question = await strategy.generate_question(
                        content,
                        temperature=temperature,
                        **type_params
                    )

                    # Set common fields
                    question.quiz_id = quiz_id
                    question.display_order = len(generated_questions)

                    generated_questions.append(question)

                except Exception as e:
                    logger.error(
                        "question_generation_failed",
                        question_type=question_type.value,
                        provider=provider_name,
                        error=str(e),
                        attempt=i + 1
                    )
                    continue

        return generated_questions

    def _get_type_parameters(
        self,
        question_type: QuestionType,
        **kwargs
    ) -> Dict[str, Any]:
        """Get type-specific generation parameters."""

        if question_type == QuestionType.MULTIPLE_CHOICE:
            return {
                "num_options": kwargs.get("mcq_options", 4),
                "num_correct": kwargs.get("mcq_correct", 1),
            }
        elif question_type == QuestionType.MATCHING:
            return {
                "num_pairs": kwargs.get("matching_pairs", 4),
            }

        return {}

# File: app/services/generation/workflow.py (UPDATED workflow)
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List, Dict, Any

class QuestionGenerationState(TypedDict):
    """Enhanced state for multi-type generation."""
    quiz_id: UUID
    content_chunks: List[str]
    target_counts: Dict[QuestionType, int]
    provider_config: Dict[str, Any]
    generated_questions: List[QuestionBase]
    current_chunk_index: int
    error_messages: List[str]
    temperature: float

class EnhancedQuestionGenerationWorkflow:
    """Workflow supporting multiple question types and providers."""

    def __init__(self, generation_service: QuestionGenerationService):
        self.generation_service = generation_service
        self.workflow = self._build_workflow()

    async def generate_questions_for_chunk(
        self,
        state: QuestionGenerationState
    ) -> QuestionGenerationState:
        """Generate questions from current chunk."""

        chunk_index = state["current_chunk_index"]
        if chunk_index >= len(state["content_chunks"]):
            return state

        content = state["content_chunks"][chunk_index]

        # Calculate distribution for this chunk
        questions_per_type = self._calculate_chunk_distribution(
            state["target_counts"],
            len(state["content_chunks"]),
            chunk_index
        )

        # Generate questions
        try:
            questions = await self.generation_service.generate_questions(
                content=content,
                question_types=list(questions_per_type.keys()),
                quiz_id=state["quiz_id"],
                provider_name=state["provider_config"]["provider"],
                model=state["provider_config"].get("model"),
                temperature=state["temperature"],
                count_per_type=1,
            )

            state["generated_questions"].extend(questions)

        except Exception as e:
            state["error_messages"].append(
                f"Chunk {chunk_index}: {str(e)}"
            )

        state["current_chunk_index"] += 1
        return state

    def should_continue_generation(self, state: QuestionGenerationState) -> str:
        """Determine if generation should continue."""

        # Count generated questions by type
        generated_counts = {}
        for question in state["generated_questions"]:
            q_type = question.question_type
            generated_counts[q_type] = generated_counts.get(q_type, 0) + 1

        # Check if we have enough of each type
        for q_type, target in state["target_counts"].items():
            if generated_counts.get(q_type, 0) < target:
                if state["current_chunk_index"] < len(state["content_chunks"]):
                    return "generate"

        return "save"

    async def save_questions(
        self,
        state: QuestionGenerationState
    ) -> QuestionGenerationState:
        """Save questions to database."""

        from app.crud.bulk_operations import BulkOperations

        with Session(engine) as session:
            # Convert typed questions to storage format
            storage_questions = []

            for i, question in enumerate(state["generated_questions"]):
                storage_question = Question.from_typed(question)
                storage_question.display_order = i
                storage_questions.append(storage_question.model_dump())

            # Bulk insert
            BulkOperations.bulk_insert(
                session,
                Question,
                storage_questions
            )

            # Update quiz status
            quiz = session.get(Quiz, state["quiz_id"])
            if quiz:
                quiz.question_generation_status = "completed"
                quiz.questions_generated = len(storage_questions)
                quiz.generation_completed_at = datetime.utcnow()
                session.commit()

        return state

    def _calculate_chunk_distribution(
        self,
        target_counts: Dict[QuestionType, int],
        total_chunks: int,
        chunk_index: int
    ) -> Dict[QuestionType, int]:
        """Calculate how many questions of each type for this chunk."""

        distribution = {}

        for q_type, total_count in target_counts.items():
            per_chunk = total_count // total_chunks
            remainder = total_count % total_chunks

            # Distribute remainder across first chunks
            if chunk_index < remainder:
                per_chunk += 1

            distribution[q_type] = per_chunk

        return distribution

    def _build_workflow(self) -> StateGraph:
        """Build the workflow graph."""

        workflow = StateGraph(QuestionGenerationState)

        # Add nodes
        workflow.add_node("generate", self.generate_questions_for_chunk)
        workflow.add_node("save", self.save_questions)

        # Add edges
        workflow.add_edge(START, "generate")
        workflow.add_conditional_edges(
            "generate",
            self.should_continue_generation,
            {
                "generate": "generate",
                "save": "save"
            }
        )
        workflow.add_edge("save", END)

        return workflow.compile()
```

## Implementation Details

### Database Migration

```sql
-- Phase 1: Add new columns
ALTER TABLE question
ADD COLUMN question_type VARCHAR(50) NOT NULL DEFAULT 'multiple_choice',
ADD COLUMN question_data JSONB,
ADD COLUMN display_order INTEGER DEFAULT 0,
ADD COLUMN points FLOAT DEFAULT 1.0;

-- Phase 2: Migrate existing data
UPDATE question
SET question_data = jsonb_build_object(
    'options', jsonb_build_array(
        jsonb_build_object('id', '0', 'text', option_a),
        jsonb_build_object('id', '1', 'text', option_b),
        jsonb_build_object('id', '2', 'text', option_c),
        jsonb_build_object('id', '3', 'text', option_d)
    ),
    'correct_answers',
    CASE correct_answer
        WHEN 'A' THEN jsonb_build_array('0')
        WHEN 'B' THEN jsonb_build_array('1')
        WHEN 'C' THEN jsonb_build_array('2')
        WHEN 'D' THEN jsonb_build_array('3')
    END,
    'allow_multiple', false,
    'shuffle_options', true
);

-- Phase 3: Create indexes
CREATE INDEX idx_question_type ON question(question_type);
CREATE INDEX idx_question_quiz_type ON question(quiz_id, question_type);
CREATE INDEX idx_question_data_gin ON question USING gin(question_data);

-- Phase 4: Drop old columns (after verification)
-- ALTER TABLE question
-- DROP COLUMN option_a,
-- DROP COLUMN option_b,
-- DROP COLUMN option_c,
-- DROP COLUMN option_d,
-- DROP COLUMN correct_answer;
```

### Files to Modify

```
backend/
├── app/
│   ├── models/
│   │   ├── questions/
│   │   │   ├── __init__.py          # Export all question types
│   │   │   ├── base.py              # NEW: Abstract base
│   │   │   ├── storage.py           # NEW: Polymorphic storage
│   │   │   ├── multiple_choice.py   # NEW: MCQ implementation
│   │   │   ├── true_false.py        # NEW: T/F implementation
│   │   │   └── matching.py          # NEW: Matching implementation
│   │   └── __init__.py              # UPDATE: Export question types
│   ├── services/
│   │   ├── llm/
│   │   │   ├── __init__.py          # NEW: LLM providers
│   │   │   ├── base.py              # NEW: Provider interface
│   │   │   ├── openai_provider.py   # NEW: OpenAI implementation
│   │   │   └── anthropic_provider.py # NEW: Anthropic implementation
│   │   ├── generation/
│   │   │   ├── __init__.py          # NEW: Generation module
│   │   │   ├── service.py           # NEW: Unified service
│   │   │   ├── workflow.py          # UPDATE: Multi-type workflow
│   │   │   └── strategies/
│   │   │       ├── base.py          # NEW: Strategy interface
│   │   │       └── *.py             # NEW: Type strategies
│   │   └── canvas_quiz_export.py    # UPDATE: Handle all types
│   ├── api/
│   │   └── routes/
│   │       └── quiz.py              # UPDATE: Multi-type endpoints
│   ├── alembic/
│   │   └── versions/
│   │       └── xxx_question_types.py # NEW: Migration script
│   └── tests/
│       └── models/
│           └── test_questions.py     # NEW: Question type tests
```

### Configuration Updates

```python
# app/core/config.py
class Settings(BaseSettings):
    # LLM Provider settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # Default models
    DEFAULT_OPENAI_MODEL: str = "gpt-4"
    DEFAULT_ANTHROPIC_MODEL: str = "claude-3-opus-20240229"
    DEFAULT_GOOGLE_MODEL: str = "gemini-pro"

    # Question generation limits
    MAX_QUESTIONS_PER_QUIZ: int = 200
    MAX_QUESTIONS_PER_TYPE: int = 100

    # Supported configurations
    SUPPORTED_QUESTION_TYPES: List[str] = [
        "multiple_choice",
        "true_false",
        "matching",
    ]

    SUPPORTED_LLM_PROVIDERS: List[str] = [
        "openai",
        "anthropic",
        "google",
    ]
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/models/test_question_types.py
import pytest
from app.models.questions import (
    MultipleChoiceQuestion,
    TrueFalseQuestion,
    MatchingQuestion,
    Question,
    MCQOption,
    MatchingPair,
)

def test_multiple_choice_question():
    """Test MCQ creation and methods."""

    mcq = MultipleChoiceQuestion(
        quiz_id=uuid.uuid4(),
        question_text="What is 2+2?",
        options=[
            MCQOption(id="0", text="3"),
            MCQOption(id="1", text="4"),
            MCQOption(id="2", text="5"),
            MCQOption(id="3", text="6"),
        ],
        correct_answers=["1"],
        points=1.0
    )

    # Test answer validation
    assert mcq.validate_answer("1") is True
    assert mcq.validate_answer("0") is False
    assert mcq.validate_answer(["1"]) is True

    # Test Canvas format
    canvas_format = mcq.to_canvas_format()
    assert canvas_format["interaction_type_slug"] == "choice"
    assert len(canvas_format["interaction_data"]["choices"]) == 4
    assert canvas_format["scoring_data"]["value"] == "choice_1"

def test_true_false_question():
    """Test T/F question creation."""

    tf = TrueFalseQuestion(
        quiz_id=uuid.uuid4(),
        question_text="Python is a compiled language.",
        correct_answer=False,
        true_feedback="Incorrect. Python is interpreted.",
        false_feedback="Correct! Python is interpreted.",
    )

    # Test answer validation
    assert tf.validate_answer(False) is True
    assert tf.validate_answer(True) is False
    assert tf.validate_answer("false") is True
    assert tf.validate_answer("true") is False

    # Test Canvas format
    canvas_format = tf.to_canvas_format()
    assert canvas_format["interaction_type_slug"] == "true_false"
    assert canvas_format["scoring_data"]["value"] == "false"

def test_question_polymorphic_storage():
    """Test storing and retrieving typed questions."""

    # Create typed question
    original = MultipleChoiceQuestion(
        quiz_id=uuid.uuid4(),
        question_text="Test question",
        options=[
            MCQOption(id="0", text="Option A"),
            MCQOption(id="1", text="Option B"),
        ],
        correct_answers=["0"]
    )

    # Convert to storage
    storage = Question.from_typed(original)
    assert storage.question_type == QuestionType.MULTIPLE_CHOICE
    assert "options" in storage.question_data
    assert len(storage.question_data["options"]) == 2

    # Convert back to typed
    retrieved = storage.get_typed_instance()
    assert isinstance(retrieved, MultipleChoiceQuestion)
    assert retrieved.question_text == original.question_text
    assert len(retrieved.options) == 2

def test_matching_question():
    """Test matching question creation."""

    matching = MatchingQuestion(
        quiz_id=uuid.uuid4(),
        question_text="Match the programming languages to their creators.",
        pairs=[
            MatchingPair(
                left_id="1", left_text="Python",
                right_id="a", right_text="Guido van Rossum"
            ),
            MatchingPair(
                left_id="2", left_text="JavaScript",
                right_id="b", right_text="Brendan Eich"
            ),
            MatchingPair(
                left_id="3", left_text="Ruby",
                right_id="c", right_text="Yukihiro Matsumoto"
            ),
        ],
        instructions="Match each language to its creator"
    )

    # Test answer validation
    correct_answer = {"1": "a", "2": "b", "3": "c"}
    wrong_answer = {"1": "b", "2": "a", "3": "c"}

    assert matching.validate_answer(correct_answer) is True
    assert matching.validate_answer(wrong_answer) is False

    # Test Canvas format
    canvas_format = matching.to_canvas_format()
    assert canvas_format["interaction_type_slug"] == "matching"
    assert len(canvas_format["interaction_data"]["left_items"]) == 3
    assert len(canvas_format["interaction_data"]["right_items"]) == 3
```

### Provider Tests

```python
# File: app/tests/services/test_llm_providers.py
import pytest
from app.services.llm import OpenAIProvider, AnthropicProvider

@pytest.mark.asyncio
async def test_openai_provider(mock_openai_api):
    """Test OpenAI provider implementation."""

    provider = OpenAIProvider(api_key="test-key", model="gpt-4")

    # Test completion
    response = await provider.generate_completion(
        "Generate a question about Python",
        temperature=0.7
    )

    assert response.success is True
    assert response.provider == "openai"
    assert response.model == "gpt-4"
    assert response.content is not None

    # Test token counting
    count = provider.get_token_count("Hello, world!")
    assert count > 0

    # Test context length
    max_length = provider.get_max_context_length()
    assert max_length == 8192  # GPT-4 default

@pytest.mark.asyncio
async def test_provider_error_handling():
    """Test provider error handling."""

    provider = OpenAIProvider(api_key="invalid-key", model="gpt-4")

    response = await provider.generate_completion("Test prompt")

    assert response.success is False
    assert response.error is not None
    assert response.content is None
```

### Generation Tests

```python
# File: app/tests/services/test_question_generation.py
@pytest.mark.asyncio
async def test_multi_type_generation(mock_llm_providers):
    """Test generating multiple question types."""

    service = QuestionGenerationService()

    questions = await service.generate_questions(
        content="Python is a high-level programming language...",
        question_types=[
            QuestionType.MULTIPLE_CHOICE,
            QuestionType.TRUE_FALSE,
            QuestionType.MATCHING
        ],
        quiz_id=uuid.uuid4(),
        provider_name="openai",
        count_per_type=2
    )

    # Should generate 2 of each type = 6 total
    assert len(questions) == 6

    # Check type distribution
    type_counts = {}
    for q in questions:
        type_counts[q.question_type] = type_counts.get(q.question_type, 0) + 1

    assert type_counts[QuestionType.MULTIPLE_CHOICE] == 2
    assert type_counts[QuestionType.TRUE_FALSE] == 2
    assert type_counts[QuestionType.MATCHING] == 2

@pytest.mark.asyncio
async def test_provider_switching():
    """Test using different providers."""

    service = QuestionGenerationService()

    # Test with OpenAI
    openai_questions = await service.generate_questions(
        content="Test content",
        question_types=[QuestionType.MULTIPLE_CHOICE],
        quiz_id=uuid.uuid4(),
        provider_name="openai",
        count_per_type=1
    )

    # Test with Anthropic
    anthropic_questions = await service.generate_questions(
        content="Test content",
        question_types=[QuestionType.MULTIPLE_CHOICE],
        quiz_id=uuid.uuid4(),
        provider_name="anthropic",
        count_per_type=1
    )

    assert len(openai_questions) == 1
    assert len(anthropic_questions) == 1
```

## Migration Strategy

### Phase 1: Database Migration (Week 1)
1. Add new columns with defaults
2. Create migration script for existing data
3. Add indexes for performance
4. Test data integrity

### Phase 2: Core Abstractions (Week 2)
1. Implement question type hierarchy
2. Create LLM provider abstraction
3. Build provider implementations
4. Test each component

### Phase 3: Generation Service (Week 3)
1. Implement generation strategies
2. Build unified service
3. Update workflow for multi-type
4. Add configuration

### Phase 4: API Integration (Week 4)
1. Update API endpoints
2. Modify Canvas export
3. Update frontend models
4. Add UI for configuration

### Phase 5: Testing & Rollout (Week 5)
1. Comprehensive testing
2. Performance optimization
3. Documentation
4. Gradual feature rollout

### Rollback Plan

```python
# Feature flags for gradual rollout
if settings.ENABLE_MULTI_QUESTION_TYPES:
    # Use new polymorphic system
    from app.services.generation import QuestionGenerationService
    service = QuestionGenerationService()
else:
    # Use legacy MCQ-only system
    from app.services.mcq_generation import MCQGenerationService
    service = MCQGenerationService()

# Database compatibility mode
if settings.USE_LEGACY_QUESTION_SCHEMA:
    # Map new format to old columns for compatibility
    def map_to_legacy(question: Question):
        if question.question_type == QuestionType.MULTIPLE_CHOICE:
            options = question.question_data.get("options", [])
            return {
                "option_a": options[0]["text"] if len(options) > 0 else "",
                "option_b": options[1]["text"] if len(options) > 1 else "",
                "option_c": options[2]["text"] if len(options) > 2 else "",
                "option_d": options[3]["text"] if len(options) > 3 else "",
                "correct_answer": chr(65 + int(question.question_data["correct_answers"][0]))
            }
```

## Success Criteria

### Functional Requirements

- **Question Type Support**: 3+ types implemented
- **Provider Support**: 2+ LLM providers working
- **Backward Compatibility**: Existing MCQs continue working
- **Canvas Export**: All types export correctly
- **Performance**: No degradation vs current system

### Technical Metrics

- **Test Coverage**: >90% for new code
- **Type Coverage**: 100% for question models
- **Migration Success**: 100% of existing data migrated
- **API Compatibility**: No breaking changes

### Business Metrics

- **Question Variety**: 30%+ non-MCQ questions
- **Provider Flexibility**: Ability to switch providers
- **Cost Optimization**: Option to use cheaper models
- **User Satisfaction**: Improved quiz quality

## Monitoring

```python
# Prometheus metrics for monitoring
from prometheus_client import Counter, Histogram

question_generation_total = Counter(
    'question_generation_total',
    'Total questions generated',
    ['question_type', 'provider', 'model']
)

question_generation_errors = Counter(
    'question_generation_errors_total',
    'Question generation errors',
    ['question_type', 'provider', 'error_type']
)

llm_provider_latency = Histogram(
    'llm_provider_latency_seconds',
    'LLM provider response time',
    ['provider', 'model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

question_type_distribution = Histogram(
    'question_type_distribution',
    'Distribution of generated question types',
    ['quiz_id'],
    buckets=[0, 10, 25, 50, 75, 90, 100]  # Percentages
)
```

---
