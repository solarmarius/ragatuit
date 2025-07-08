# Question Generator Modularization Strategy

## Executive Summary

This document outlines a comprehensive strategy to refactor the current question generation system to support multiple question types (multiple choice, true/false, matching, etc.) and multiple LLM providers (OpenAI, Google, Anthropic). The proposed architecture introduces abstraction layers that enable extensibility while maintaining backward compatibility.

### Key Benefits
- **Extensibility**: Easy addition of new question types and LLM providers
- **Maintainability**: Clear separation of concerns and modular design
- **Flexibility**: Mix and match question types with different LLM providers
- **Type Safety**: Strong typing throughout with Pydantic models
- **Database Efficiency**: Polymorphic storage strategy for different question types
- **Backward Compatibility**: Existing MCQ functionality preserved

## Current State Analysis

### Limitations of Current Implementation
1. **Tightly Coupled to MCQ**: Fixed 4-option multiple choice structure
2. **Single Provider**: Hard-coded for OpenAI only
3. **Rigid Database Schema**: Fixed columns for options A-D
4. **Limited Canvas Export**: Only supports "choice" interaction type
5. **No Question Type Differentiation**: All questions are implicitly MCQ

## Proposed Architecture

### 1. Database Schema Evolution

#### Option A: Polymorphic Single Table (Recommended)

```sql
-- Migration: Add question type and flexible data storage
ALTER TABLE question ADD COLUMN question_type VARCHAR(50) NOT NULL DEFAULT 'multiple_choice';
ALTER TABLE question ADD COLUMN question_data JSONB;
ALTER TABLE question ADD COLUMN display_order INTEGER;

-- Indexes for performance
CREATE INDEX idx_question_type ON question(question_type);
CREATE INDEX idx_question_quiz_type ON question(quiz_id, question_type);

-- Migration to move existing data
UPDATE question
SET question_data = jsonb_build_object(
    'options', jsonb_build_array(
        jsonb_build_object('id', 'A', 'text', option_a),
        jsonb_build_object('id', 'B', 'text', option_b),
        jsonb_build_object('id', 'C', 'text', option_c),
        jsonb_build_object('id', 'D', 'text', option_d)
    ),
    'correct_answers', jsonb_build_array(correct_answer)
);

-- After migration, original columns can be dropped or kept for backward compatibility
```

#### Option B: Table Per Question Type
```sql
-- Base question table
CREATE TABLE question_base (
    id UUID PRIMARY KEY,
    quiz_id UUID REFERENCES quiz(id),
    question_type VARCHAR(50) NOT NULL,
    question_text TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    -- common fields
);

-- Type-specific tables
CREATE TABLE question_multiple_choice (
    question_id UUID PRIMARY KEY REFERENCES question_base(id),
    options JSONB NOT NULL,
    correct_answer VARCHAR(10) NOT NULL
);

CREATE TABLE question_true_false (
    question_id UUID PRIMARY KEY REFERENCES question_base(id),
    correct_answer BOOLEAN NOT NULL,
    explanation TEXT
);

CREATE TABLE question_matching (
    question_id UUID PRIMARY KEY REFERENCES question_base(id),
    pairs JSONB NOT NULL,
    instructions TEXT
);
```

### 2. Domain Models with Polymorphism

```python
# models/questions/base.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, TypeVar, Generic
from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, SQLModel

class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    MATCHING = "matching"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"

class QuestionBase(SQLModel, ABC):
    """Abstract base for all question types"""
    id: UUID = SQLField(default_factory=uuid.uuid4, primary_key=True)
    quiz_id: UUID = SQLField(foreign_key="quiz.id", nullable=False)
    question_type: QuestionType
    question_text: str = SQLField(min_length=1, max_length=2000)
    is_approved: bool = SQLField(default=False)
    approved_at: datetime | None = None
    created_at: datetime | None = SQLField(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now()))
    updated_at: datetime | None = SQLField(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))
    canvas_item_id: str | None = None
    display_order: int | None = None

    @abstractmethod
    def to_canvas_format(self) -> dict[str, Any]:
        """Convert to Canvas quiz item format"""
        pass

    @abstractmethod
    def validate_answer(self, answer: Any) -> bool:
        """Validate if given answer is correct"""
        pass

    @abstractmethod
    def get_points(self) -> float:
        """Get points value for this question"""
        pass

# Concrete storage model
class Question(QuestionBase, table=True):
    """Polymorphic question storage"""
    question_data: dict[str, Any] = SQLField(default_factory=dict, sa_column=Column(JSONB))

    def get_typed_instance(self) -> QuestionBase:
        """Return properly typed question instance based on question_type"""
        question_classes = {
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceQuestion,
            QuestionType.TRUE_FALSE: TrueFalseQuestion,
            QuestionType.MATCHING: MatchingQuestion,
            # ... other types
        }

        question_class = question_classes.get(self.question_type)
        if not question_class:
            raise ValueError(f"Unknown question type: {self.question_type}")

        return question_class(**self.model_dump())
```

### 3. Question Type Implementations

```python
# models/questions/multiple_choice.py
class MCQOption(BaseModel):
    id: str
    text: str
    feedback: str | None = None

class MultipleChoiceData(BaseModel):
    options: list[MCQOption]
    correct_answers: list[str]  # Support multiple correct answers
    shuffle_options: bool = True

class MultipleChoiceQuestion(QuestionBase):
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE

    @property
    def data(self) -> MultipleChoiceData:
        return MultipleChoiceData(**self.question_data)

    def to_canvas_format(self) -> dict[str, Any]:
        choices = [
            {
                "id": f"choice_{i}",
                "position": i,
                "item_body": f"<p>{option.text}</p>",
            }
            for i, option in enumerate(self.data.options)
        ]

        # Handle single or multiple correct answers
        if len(self.data.correct_answers) == 1:
            scoring_data = {"value": f"choice_{self.data.correct_answers[0]}"}
        else:
            scoring_data = {"value": [f"choice_{ans}" for ans in self.data.correct_answers]}

        return {
            "interaction_type_slug": "choice",
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {"choices": choices},
            "scoring_algorithm": "Equivalence",
            "scoring_data": scoring_data,
        }

    def validate_answer(self, answer: str | list[str]) -> bool:
        if isinstance(answer, str):
            answer = [answer]
        return set(answer) == set(self.data.correct_answers)

    def get_points(self) -> float:
        return 1.0

# models/questions/true_false.py
class TrueFalseData(BaseModel):
    correct_answer: bool
    true_feedback: str | None = None
    false_feedback: str | None = None

class TrueFalseQuestion(QuestionBase):
    question_type: QuestionType = QuestionType.TRUE_FALSE

    @property
    def data(self) -> TrueFalseData:
        return TrueFalseData(**self.question_data)

    def to_canvas_format(self) -> dict[str, Any]:
        return {
            "interaction_type_slug": "true_false",
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {
                "true_choice": {"id": "true", "text": "True"},
                "false_choice": {"id": "false", "text": "False"},
            },
            "scoring_algorithm": "Equivalence",
            "scoring_data": {"value": str(self.data.correct_answer).lower()},
        }

    def validate_answer(self, answer: bool | str) -> bool:
        if isinstance(answer, str):
            answer = answer.lower() == "true"
        return answer == self.data.correct_answer

    def get_points(self) -> float:
        return 1.0

# models/questions/matching.py
class MatchingPair(BaseModel):
    left_id: str
    left_text: str
    right_id: str
    right_text: str

class MatchingData(BaseModel):
    pairs: list[MatchingPair]
    instructions: str | None = None
    shuffle_left: bool = True
    shuffle_right: bool = True

class MatchingQuestion(QuestionBase):
    question_type: QuestionType = QuestionType.MATCHING

    @property
    def data(self) -> MatchingData:
        return MatchingData(**self.question_data)

    def to_canvas_format(self) -> dict[str, Any]:
        return {
            "interaction_type_slug": "matching",
            "item_body": f"<p>{self.question_text}</p>",
            "interaction_data": {
                "left_items": [
                    {"id": pair.left_id, "text": pair.left_text}
                    for pair in self.data.pairs
                ],
                "right_items": [
                    {"id": pair.right_id, "text": pair.right_text}
                    for pair in self.data.pairs
                ],
                "instructions": self.data.instructions,
            },
            "scoring_algorithm": "Matching",
            "scoring_data": {
                "matches": [
                    {"left": pair.left_id, "right": pair.right_id}
                    for pair in self.data.pairs
                ]
            },
        }

    def validate_answer(self, answer: dict[str, str]) -> bool:
        correct_matches = {pair.left_id: pair.right_id for pair in self.data.pairs}
        return answer == correct_matches

    def get_points(self) -> float:
        return float(len(self.data.pairs))
```

### 4. LLM Provider Abstraction

```python
# services/llm/base.py
from abc import ABC, abstractmethod
from typing import Protocol, TypeVar, Generic

T = TypeVar('T', bound=QuestionBase)

class LLMResponse(BaseModel):
    success: bool
    content: Any
    error: str | None = None
    usage: dict[str, int] | None = None
    model: str

class LLMProvider(ABC):
    """Abstract base for LLM providers"""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: int | None = None
    ) -> LLMResponse:
        """Generate text completion"""
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Count tokens in text"""
        pass

    @abstractmethod
    def get_max_tokens(self) -> int:
        """Get maximum token limit"""
        pass

# services/llm/openai_provider.py
from langchain_openai import ChatOpenAI
import tiktoken

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
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
        max_tokens: int | None = None
    ) -> LLMResponse:
        try:
            response = await self.client.ainvoke(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return LLMResponse(
                success=True,
                content=response.content,
                usage={
                    "prompt_tokens": response.response_metadata.get("token_usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": response.response_metadata.get("token_usage", {}).get("completion_tokens", 0),
                },
                model=self.model
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                content=None,
                error=str(e),
                model=self.model
            )

    def get_token_count(self, text: str) -> int:
        if not self._tokenizer:
            self._tokenizer = tiktoken.encoding_for_model(self.model)
        return len(self._tokenizer.encode(text))

    def get_max_tokens(self) -> int:
        model_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-3.5-turbo": 4096,
            "gpt-4o": 128000,
        }
        return model_limits.get(self.model, 4096)

# services/llm/anthropic_provider.py
from anthropic import AsyncAnthropic

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-opus-20240229"):
        self.api_key = api_key
        self.model = model
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
        max_tokens: int | None = None
    ) -> LLMResponse:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            return LLMResponse(
                success=True,
                content=response.content[0].text,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                },
                model=self.model
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                content=None,
                error=str(e),
                model=self.model
            )

    def get_token_count(self, text: str) -> int:
        # Anthropic doesn't provide a tokenizer, estimate
        return len(text) // 4

    def get_max_tokens(self) -> int:
        return 200000  # Claude 3 context window

# services/llm/google_provider.py
import google.generativeai as genai

class GoogleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)
        self._client = None

    @property
    def client(self):
        if not self._client:
            self._client = genai.GenerativeModel(self.model)
        return self._client

    async def generate_completion(
        self,
        prompt: str,
        temperature: float = 1.0,
        max_tokens: int | None = None
    ) -> LLMResponse:
        try:
            response = await self.client.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            return LLMResponse(
                success=True,
                content=response.text,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                },
                model=self.model
            )
        except Exception as e:
            return LLMResponse(
                success=False,
                content=None,
                error=str(e),
                model=self.model
            )

    def get_token_count(self, text: str) -> int:
        return self.client.count_tokens(text).total_tokens

    def get_max_tokens(self) -> int:
        return 30720  # Gemini Pro limit
```

### 5. Question Generation Strategy Pattern

```python
# services/generation/strategies/base.py
from abc import ABC, abstractmethod

class QuestionGenerationStrategy(ABC, Generic[T]):
    """Abstract strategy for generating specific question types"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the prompt template for this question type"""
        pass

    @abstractmethod
    def parse_response(self, response: str) -> T:
        """Parse LLM response into question object"""
        pass

    @abstractmethod
    def validate_response(self, response: str) -> bool:
        """Validate if response is properly formatted"""
        pass

    async def generate_question(
        self,
        content: str,
        temperature: float = 1.0,
        **kwargs
    ) -> T:
        """Generate a question from content"""
        prompt = self.get_prompt_template().format(content=content, **kwargs)

        llm_response = await self.provider.generate_completion(
            prompt,
            temperature=temperature
        )

        if not llm_response.success:
            raise ValueError(f"LLM generation failed: {llm_response.error}")

        if not self.validate_response(llm_response.content):
            raise ValueError("Invalid response format from LLM")

        return self.parse_response(llm_response.content)

# services/generation/strategies/multiple_choice.py
class MultipleChoiceStrategy(QuestionGenerationStrategy[MultipleChoiceQuestion]):
    def get_prompt_template(self) -> str:
        return """You are an expert educator creating multiple-choice questions.

Based on the following content, generate ONE high-quality multiple-choice question.

Content:
{content}

Requirements:
- Create exactly {num_options} options
- Make all options plausible but only {num_correct} correct
- Options should be similar in length
- Test understanding, not memorization
- Use clear, concise language

Return your response as valid JSON:
{{
    "question_text": "Your question here",
    "options": [
        {{"id": "0", "text": "First option"}},
        {{"id": "1", "text": "Second option"}},
        ...
    ],
    "correct_answers": ["0"],  // Array of correct option IDs
    "explanation": "Brief explanation of the answer"
}}
"""

    def parse_response(self, response: str) -> MultipleChoiceQuestion:
        # Clean and parse JSON response
        json_text = self._extract_json(response)
        data = json.loads(json_text)

        return MultipleChoiceQuestion(
            question_text=data["question_text"],
            question_data={
                "options": data["options"],
                "correct_answers": data["correct_answers"],
            }
        )

    def validate_response(self, response: str) -> bool:
        try:
            json_text = self._extract_json(response)
            data = json.loads(json_text)

            required_fields = ["question_text", "options", "correct_answers"]
            return all(field in data for field in required_fields)
        except:
            return False

# services/generation/strategies/true_false.py
class TrueFalseStrategy(QuestionGenerationStrategy[TrueFalseQuestion]):
    def get_prompt_template(self) -> str:
        return """You are an expert educator creating true/false questions.

Based on the following content, generate ONE true/false question.

Content:
{content}

Requirements:
- The statement should be clearly true or false
- Avoid ambiguous or trick questions
- Test a single concept
- Include an explanation

Return your response as valid JSON:
{{
    "question_text": "Statement to evaluate",
    "correct_answer": true,  // or false
    "explanation": "Why this is true/false",
    "true_feedback": "Feedback if student answers true",
    "false_feedback": "Feedback if student answers false"
}}
"""

    def parse_response(self, response: str) -> TrueFalseQuestion:
        json_text = self._extract_json(response)
        data = json.loads(json_text)

        return TrueFalseQuestion(
            question_text=data["question_text"],
            question_data={
                "correct_answer": data["correct_answer"],
                "true_feedback": data.get("true_feedback"),
                "false_feedback": data.get("false_feedback"),
            }
        )

# services/generation/strategies/matching.py
class MatchingStrategy(QuestionGenerationStrategy[MatchingQuestion]):
    def get_prompt_template(self) -> str:
        return """You are an expert educator creating matching questions.

Based on the following content, generate ONE matching question with {num_pairs} pairs.

Content:
{content}

Requirements:
- Create exactly {num_pairs} matching pairs
- Each left item should have exactly one right match
- Items should be concise (1-3 words ideal)
- Test relationships or associations
- Avoid obvious matches

Return your response as valid JSON:
{{
    "question_text": "Match the following items",
    "instructions": "Optional specific instructions",
    "pairs": [
        {{
            "left_id": "1",
            "left_text": "Term or concept",
            "right_id": "a",
            "right_text": "Definition or match"
        }},
        ...
    ]
}}
"""

    def parse_response(self, response: str) -> MatchingQuestion:
        json_text = self._extract_json(response)
        data = json.loads(json_text)

        return MatchingQuestion(
            question_text=data["question_text"],
            question_data={
                "pairs": data["pairs"],
                "instructions": data.get("instructions"),
            }
        )
```

### 6. Unified Question Generation Service

```python
# services/generation/service.py
from typing import Type

class QuestionGenerationService:
    """Unified service for generating questions of any type with any provider"""

    def __init__(self):
        self._providers: dict[str, Type[LLMProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
            "google": GoogleProvider,
        }

        self._strategies: dict[QuestionType, Type[QuestionGenerationStrategy]] = {
            QuestionType.MULTIPLE_CHOICE: MultipleChoiceStrategy,
            QuestionType.TRUE_FALSE: TrueFalseStrategy,
            QuestionType.MATCHING: MatchingStrategy,
        }

    def get_provider(self, provider_name: str, **kwargs) -> LLMProvider:
        """Get LLM provider instance"""
        provider_class = self._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}")

        # Get API key from settings based on provider
        api_key = getattr(settings, f"{provider_name.upper()}_API_KEY", None)
        if not api_key:
            raise ValueError(f"No API key configured for {provider_name}")

        return provider_class(api_key=api_key, **kwargs)

    def get_strategy(
        self,
        question_type: QuestionType,
        provider: LLMProvider
    ) -> QuestionGenerationStrategy:
        """Get generation strategy for question type"""
        strategy_class = self._strategies.get(question_type)
        if not strategy_class:
            raise ValueError(f"No strategy for question type: {question_type}")

        return strategy_class(provider)

    async def generate_questions(
        self,
        content: str,
        question_types: list[QuestionType],
        provider_name: str = "openai",
        model: str | None = None,
        temperature: float = 1.0,
        count_per_type: int = 1,
        **kwargs
    ) -> list[QuestionBase]:
        """Generate questions of multiple types"""

        # Get provider
        provider_kwargs = {"model": model} if model else {}
        provider = self.get_provider(provider_name, **provider_kwargs)

        generated_questions = []

        for question_type in question_types:
            strategy = self.get_strategy(question_type, provider)

            for _ in range(count_per_type):
                try:
                    question = await strategy.generate_question(
                        content,
                        temperature=temperature,
                        **kwargs
                    )
                    question.question_type = question_type
                    generated_questions.append(question)
                except Exception as e:
                    logger.error(
                        "question_generation_failed",
                        question_type=question_type,
                        provider=provider_name,
                        error=str(e)
                    )
                    continue

        return generated_questions
```

### 7. Updated LangGraph Workflow

```python
# services/generation/workflow.py
from langgraph.graph import StateGraph, START, END

class QuestionGenerationState(TypedDict):
    quiz_id: UUID
    content_chunks: list[str]
    target_counts: dict[QuestionType, int]  # e.g., {MULTIPLE_CHOICE: 20, TRUE_FALSE: 10}
    provider_config: dict[str, Any]  # provider name, model, etc.
    generated_questions: list[QuestionBase]
    current_chunk_index: int
    error_message: str | None
    temperature: float

class EnhancedQuestionGenerationWorkflow:
    def __init__(self, generation_service: QuestionGenerationService):
        self.generation_service = generation_service
        self.workflow = None

    async def generate_questions_for_chunk(
        self,
        state: QuestionGenerationState
    ) -> QuestionGenerationState:
        """Generate questions from current content chunk"""

        chunk_index = state["current_chunk_index"]
        if chunk_index >= len(state["content_chunks"]):
            return state

        content = state["content_chunks"][chunk_index]

        # Calculate how many of each type to generate for this chunk
        total_chunks = len(state["content_chunks"])
        questions_per_chunk = {}

        for q_type, total_count in state["target_counts"].items():
            per_chunk = total_count // total_chunks
            remainder = total_count % total_chunks

            # Distribute remainder across first chunks
            if chunk_index < remainder:
                per_chunk += 1

            questions_per_chunk[q_type] = per_chunk

        # Generate questions
        try:
            questions = await self.generation_service.generate_questions(
                content=content,
                question_types=list(questions_per_chunk.keys()),
                provider_name=state["provider_config"]["provider"],
                model=state["provider_config"].get("model"),
                temperature=state["temperature"],
                count_per_type=1,  # Generate one at a time for better control
            )

            state["generated_questions"].extend(questions)
            state["current_chunk_index"] += 1

        except Exception as e:
            logger.error(
                "chunk_generation_failed",
                chunk_index=chunk_index,
                error=str(e)
            )
            state["current_chunk_index"] += 1  # Skip failed chunk

        return state

    def should_continue_generation(self, state: QuestionGenerationState) -> str:
        """Determine if generation should continue"""

        # Check if we have enough questions of each type
        generated_by_type = {}
        for question in state["generated_questions"]:
            q_type = question.question_type
            generated_by_type[q_type] = generated_by_type.get(q_type, 0) + 1

        # Continue if we need more of any type
        for q_type, target in state["target_counts"].items():
            if generated_by_type.get(q_type, 0) < target:
                if state["current_chunk_index"] < len(state["content_chunks"]):
                    return "generate"

        return "save"

    async def save_questions(
        self,
        state: QuestionGenerationState
    ) -> QuestionGenerationState:
        """Save generated questions to database"""

        quiz_id = state["quiz_id"]

        with Session(engine) as session:
            for i, question in enumerate(state["generated_questions"]):
                db_question = Question(
                    quiz_id=quiz_id,
                    question_type=question.question_type,
                    question_text=question.question_text,
                    question_data=question.question_data,
                    display_order=i,
                    is_approved=False,
                )
                session.add(db_question)

            session.commit()

        return state

    def build_workflow(self) -> StateGraph:
        """Build the enhanced workflow"""
        workflow = StateGraph(QuestionGenerationState)

        workflow.add_node("generate", self.generate_questions_for_chunk)
        workflow.add_node("save", self.save_questions)

        workflow.add_edge(START, "generate")
        workflow.add_conditional_edges(
            "generate",
            self.should_continue_generation,
            {
                "generate": "generate",
                "save": "save",
            }
        )
        workflow.add_edge("save", END)

        return workflow
```

### 8. API Updates

```python
# models.py - Updated quiz creation
class QuizCreate(SQLModel):
    canvas_course_id: int
    canvas_course_name: str
    selected_modules: dict[int, str]
    title: str = Field(min_length=1, max_length=255)

    # Question generation settings
    question_distribution: dict[QuestionType, int] = Field(
        default_factory=lambda: {QuestionType.MULTIPLE_CHOICE: 100}
    )

    # LLM settings
    llm_provider: str = Field(default="openai")
    llm_model: str = Field(default="gpt-4")
    llm_temperature: float = Field(default=1, ge=0.0, le=2.0)

# api/routes/quiz.py - Updated endpoint
@router.post("/", response_model=Quiz)
async def create_new_quiz(
    quiz_data: QuizCreate,
    current_user: CurrentUser,
    session: SessionDep,
    canvas_token: CanvasToken,
    background_tasks: BackgroundTasks,
) -> Quiz:
    # Validate question distribution
    total_questions = sum(quiz_data.question_distribution.values())
    if total_questions < 1 or total_questions > 200:
        raise HTTPException(
            status_code=400,
            detail="Total questions must be between 1 and 200"
        )

    # Store question distribution in quiz
    quiz = create_quiz(session, quiz_data, current_user.id)
    # ... rest of implementation
```

### 9. Repository Pattern for Questions

```python
# repositories/question.py
class QuestionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_type(
        self,
        quiz_id: UUID,
        question_type: QuestionType
    ) -> list[Question]:
        """Get all questions of a specific type for a quiz"""
        stmt = (
            select(Question)
            .where(Question.quiz_id == quiz_id)
            .where(Question.question_type == question_type)
            .order_by(Question.display_order)
        )
        return list(self.session.exec(stmt).all())

    def get_typed_questions(self, quiz_id: UUID) -> list[QuestionBase]:
        """Get all questions with proper type instances"""
        questions = self.get_all(quiz_id)
        return [q.get_typed_instance() for q in questions]

    def bulk_create_typed(self, questions: list[QuestionBase]) -> list[Question]:
        """Create multiple questions of different types"""
        db_questions = []

        for i, question in enumerate(questions):
            db_question = Question(
                quiz_id=question.quiz_id,
                question_type=question.question_type,
                question_text=question.question_text,
                question_data=question.model_dump(exclude={"id", "quiz_id", "question_text", "question_type"}),
                display_order=i,
            )
            db_questions.append(db_question)

        self.session.add_all(db_questions)
        self.session.commit()

        return db_questions
```

### 10. Canvas Export Updates

```python
# services/canvas_quiz_export.py
class EnhancedCanvasQuizExportService(CanvasQuizExportService):

    def _convert_question_to_canvas_item(
        self,
        question: Question,
        position: int
    ) -> dict[str, Any]:
        """Convert any question type to Canvas format"""

        # Get typed instance
        typed_question = question.get_typed_instance()

        # Let each question type handle its own conversion
        canvas_data = typed_question.to_canvas_format()

        return {
            "item": {
                "id": f"item_{question.id}",
                "entry_type": "Item",
                "entry_id": f"item_{question.id}",
                "position": position,
                "item_type": "Question",
                "properties": {"shuffle_answers": True},
                "points_possible": typed_question.get_points(),
                "entry": {
                    **canvas_data,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        }
```

## Migration Strategy

### Phase 1: Database Migration (Week 1)
1. Add new columns (`question_type`, `question_data`, `display_order`)
2. Migrate existing MCQ data to new structure
3. Create indexes for performance
4. Update models with backward compatibility

### Phase 2: Core Abstractions (Week 2)
1. Implement base question classes
2. Create question type implementations
3. Build LLM provider abstraction
4. Implement provider adapters

### Phase 3: Generation Service (Week 3)
1. Create question generation strategies
2. Build unified generation service
3. Update LangGraph workflow
4. Add provider configuration

### Phase 4: API & Integration (Week 4)
1. Update API endpoints
2. Modify Canvas export service
3. Update frontend models
4. Add configuration UI

### Phase 5: Testing & Deployment (Week 5)
1. Comprehensive testing
2. Performance optimization
3. Documentation
4. Gradual rollout

## Configuration

```python
# settings.py additions
OPENAI_API_KEY: str | None = None
ANTHROPIC_API_KEY: str | None = None
GOOGLE_API_KEY: str | None = None

# Default provider settings
DEFAULT_LLM_PROVIDER: str = "openai"
DEFAULT_LLM_MODEL: str = "gpt-4"

# Provider-specific model mappings
LLM_MODELS = {
    "openai": ["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
    "google": ["gemini-pro", "gemini-1.5-pro"],
}

# Question type limits
MAX_QUESTIONS_PER_TYPE = 100
SUPPORTED_QUESTION_TYPES = [
    QuestionType.MULTIPLE_CHOICE,
    QuestionType.TRUE_FALSE,
    QuestionType.MATCHING,
]
```

## Benefits & Trade-offs

### Benefits
1. **Extensibility**: New question types and providers can be added without modifying existing code
2. **Flexibility**: Any question type can be generated with any LLM provider
3. **Type Safety**: Strong typing throughout with proper polymorphism
4. **Performance**: JSONB storage allows efficient queries while maintaining flexibility
5. **Backward Compatibility**: Existing MCQ functionality preserved

### Trade-offs
1. **Complexity**: More abstraction layers increase initial complexity
2. **Database Changes**: Requires careful migration of existing data
3. **Testing**: More combinations to test (types × providers)
4. **Frontend Updates**: Requires significant frontend changes

## Conclusion

This modular architecture provides a solid foundation for supporting multiple question types and LLM providers. The strategy pattern for question generation combined with provider abstraction enables maximum flexibility while maintaining clean separation of concerns. The polymorphic database design allows efficient storage and retrieval of heterogeneous question types without sacrificing query performance.
