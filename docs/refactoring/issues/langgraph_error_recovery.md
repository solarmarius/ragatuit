# 8. LangGraph Error Recovery and Resilience

## Priority: Medium

**Estimated Effort**: 3 days
**Python Version**: 3.10+
**Dependencies**: LangGraph, asyncio

## Problem Statement

### Current Situation

The LangGraph workflow implementation lacks proper error recovery mechanisms, workflow state persistence, and graceful degradation when LLM calls fail. When errors occur, the entire workflow fails without retry or recovery options.

### Why It's a Problem

- **Workflow Failures**: Single LLM failure causes entire generation to fail
- **No State Persistence**: Cannot resume interrupted workflows
- **Resource Waste**: Must restart from beginning after any failure
- **Poor User Experience**: Users see failed generations without explanation
- **Cost Impact**: Wasted LLM API calls when workflows fail
- **No Graceful Degradation**: Cannot fall back to simpler strategies

### Affected Modules

- `app/services/mcq_generation.py` - LangGraph workflow implementation
- All MCQ generation operations
- Background task reliability
- User workflow experience

### Technical Debt Assessment

- **Risk Level**: Medium - Affects reliability and user experience
- **Impact**: All question generation workflows
- **Cost of Delay**: Increases with LLM usage and user growth

## Current Implementation Analysis

```python
# File: app/services/mcq_generation.py (current problematic implementation)
from langgraph.graph import Graph, StateDict
from typing import Dict, Any

class MCQGenerationState(TypedDict):
    quiz_id: str
    content_chunks: list[str]
    current_chunk_index: int
    questions_generated: int
    target_question_count: int
    generated_questions: list[dict]
    error_message: str | None

class MCQGenerationService:
    def should_continue_generation(self, state: MCQGenerationState) -> str:
        # PROBLEM: Simple error handling - just stops on any error
        if state["error_message"] is not None:
            return "save_questions"  # Gives up immediately!

        if state["questions_generated"] >= state["target_question_count"]:
            return "save_questions"

        if state["current_chunk_index"] >= len(state["content_chunks"]):
            return "save_questions"

        return "generate_question"

    async def generate_question(self, state: MCQGenerationState) -> MCQGenerationState:
        """Generate a single MCQ from current content chunk."""
        try:
            # PROBLEM: No retry logic for LLM failures
            llm_response = await self._call_llm(
                state["content_chunks"][state["current_chunk_index"]]
            )
            # Process response...

        except Exception as e:
            # PROBLEM: Any error terminates the workflow
            logger.error(f"Question generation failed: {e}")
            state["error_message"] = str(e)
            return state

    async def _call_llm(self, content: str) -> str:
        # PROBLEM: No timeout, retry, or fallback mechanisms
        response = await self.llm_client.generate(content)
        return response
```

### Failure Scenarios

```python
# Current failure scenarios that cause complete workflow failure:
# 1. Rate limiting from OpenAI
# 2. Network timeouts
# 3. Invalid JSON responses from LLM
# 4. Content too long for token limits
# 5. Model availability issues
# 6. Database connection issues
# 7. Memory exhaustion
```

### Python Anti-patterns Identified

- **No Exception Hierarchy**: Generic exception handling
- **Missing Circuit Breaker**: No protection against cascading failures
- **No Retry Logic**: Single attempt for all operations
- **Global State Issues**: Workflow state not persisted
- **No Compensation**: Cannot undo partial work

## Proposed Solution

### Pythonic Approach

Implement comprehensive error recovery using async patterns, circuit breakers, retry decorators with exponential backoff, workflow state persistence, and graceful degradation strategies.

### Design Patterns

- **Circuit Breaker Pattern**: Prevent cascading failures
- **Retry Pattern**: Exponential backoff with jitter
- **Saga Pattern**: Compensating transactions for multi-step workflows
- **State Machine Pattern**: Explicit state management
- **Strategy Pattern**: Multiple fallback strategies

### Code Examples

```python
# File: app/core/resilience.py (NEW)
import asyncio
import random
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import TypeVar, Callable, Any, Optional, Dict
from functools import wraps
from dataclasses import dataclass, field

from app.core.logging_config import get_logger

logger = get_logger("resilience")

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: int = 60
    expected_exceptions: tuple = (Exception,)

class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker_half_open", function=func.__name__)
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is open for {func.__name__}"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exceptions as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return False

        time_since_failure = datetime.utcnow() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.config.timeout_seconds

    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("circuit_breaker_closed")

        if self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        self.success_count = 0

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.config.failure_threshold
            )

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)

def retry_with_backoff(config: RetryConfig):
    """
    Decorator for implementing retry logic with exponential backoff.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)

                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        # Last attempt, re-raise the exception
                        break

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=config.max_attempts,
                        delay=delay,
                        error=str(e)
                    )

                    await asyncio.sleep(delay)

            # Re-raise the last exception
            raise last_exception

        return wrapper
    return decorator

# File: app/services/mcq_generation_resilient.py (NEW)
from typing import Dict, Any, List, Optional, TypedDict
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import json
from uuid import UUID

from langgraph.graph import Graph, StateDict
from app.core.resilience import CircuitBreaker, CircuitBreakerConfig, retry_with_backoff, RetryConfig
from app.core.logging_config import get_logger
from app.models import Quiz, Question

logger = get_logger("mcq_generation_resilient")

class WorkflowState(str, Enum):
    INITIALIZING = "initializing"
    CONTENT_PROCESSING = "content_processing"
    GENERATING_QUESTIONS = "generating_questions"
    VALIDATION = "validation"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"

class ErrorType(str, Enum):
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    CONTENT_TOO_LONG = "content_too_long"
    MODEL_UNAVAILABLE = "model_unavailable"
    DATABASE_ERROR = "database_error"
    UNKNOWN = "unknown"

class MCQGenerationState(TypedDict):
    # Core workflow data
    quiz_id: str
    content_chunks: List[str]
    current_chunk_index: int
    questions_generated: int
    target_question_count: int
    generated_questions: List[Dict[str, Any]]

    # Error handling and recovery
    error_count: int
    max_errors: int
    current_error_type: Optional[str]
    last_error_time: Optional[str]
    retry_count: int
    max_retries_per_chunk: int

    # Workflow state management
    workflow_state: str
    checkpoint_data: Dict[str, Any]
    fallback_strategy: Optional[str]

    # Performance monitoring
    start_time: str
    chunk_processing_times: List[float]
    successful_chunks: List[int]
    failed_chunks: List[int]

class ResilientMCQGenerationService:
    """
    Resilient MCQ generation service with comprehensive error recovery.
    """

    def __init__(self):
        # Configure circuit breakers for different operations
        self.llm_circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout_seconds=120,
                expected_exceptions=(TimeoutError, Exception)
            )
        )

        self.db_circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=3,
                timeout_seconds=30
            )
        )

        # Configure retry policies
        self.llm_retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(TimeoutError, ConnectionError)
        )

        self.content_retry_config = RetryConfig(
            max_attempts=2,
            base_delay=1.0,
            max_delay=10.0
        )

        # Workflow configuration
        self.max_errors_per_workflow = 10
        self.max_retries_per_chunk = 3
        self.chunk_timeout_seconds = 300

    def build_resilient_workflow(self) -> Graph:
        """Build LangGraph workflow with error recovery."""

        workflow = Graph()

        # Add nodes with error recovery
        workflow.add_node("initialize", self.initialize_workflow)
        workflow.add_node("process_chunk", self.process_chunk_with_recovery)
        workflow.add_node("generate_question", self.generate_question_resilient)
        workflow.add_node("validate_question", self.validate_question)
        workflow.add_node("handle_error", self.handle_error)
        workflow.add_node("apply_fallback", self.apply_fallback_strategy)
        workflow.add_node("save_checkpoint", self.save_checkpoint)
        workflow.add_node("save_questions", self.save_questions_with_recovery)
        workflow.add_node("cleanup", self.cleanup_workflow)

        # Define workflow logic with error handling
        workflow.add_edge("initialize", "process_chunk")
        workflow.add_conditional_edges(
            "process_chunk",
            self.route_after_processing,
            {
                "generate": "generate_question",
                "error": "handle_error",
                "complete": "save_questions"
            }
        )
        workflow.add_conditional_edges(
            "generate_question",
            self.route_after_generation,
            {
                "validate": "validate_question",
                "error": "handle_error",
                "retry": "generate_question",
                "next_chunk": "process_chunk"
            }
        )
        workflow.add_conditional_edges(
            "validate_question",
            self.route_after_validation,
            {
                "save_checkpoint": "save_checkpoint",
                "continue": "process_chunk",
                "error": "handle_error"
            }
        )
        workflow.add_conditional_edges(
            "handle_error",
            self.route_after_error_handling,
            {
                "retry": "process_chunk",
                "fallback": "apply_fallback",
                "fail": "cleanup"
            }
        )
        workflow.add_edge("apply_fallback", "process_chunk")
        workflow.add_edge("save_checkpoint", "process_chunk")
        workflow.add_edge("save_questions", "cleanup")

        workflow.set_entry_point("initialize")

        return workflow

    async def initialize_workflow(self, state: MCQGenerationState) -> MCQGenerationState:
        """Initialize workflow with error recovery state."""

        logger.info(
            "workflow_initialization_started",
            quiz_id=state["quiz_id"],
            target_questions=state["target_question_count"]
        )

        # Initialize error recovery state
        state.update({
            "error_count": 0,
            "max_errors": self.max_errors_per_workflow,
            "current_error_type": None,
            "last_error_time": None,
            "retry_count": 0,
            "max_retries_per_chunk": self.max_retries_per_chunk,
            "workflow_state": WorkflowState.INITIALIZING.value,
            "checkpoint_data": {},
            "fallback_strategy": None,
            "start_time": datetime.utcnow().isoformat(),
            "chunk_processing_times": [],
            "successful_chunks": [],
            "failed_chunks": []
        })

        state["workflow_state"] = WorkflowState.CONTENT_PROCESSING.value
        return state

    async def process_chunk_with_recovery(self, state: MCQGenerationState) -> MCQGenerationState:
        """Process content chunk with error recovery."""

        if state["current_chunk_index"] >= len(state["content_chunks"]):
            state["workflow_state"] = WorkflowState.COMPLETED.value
            return state

        chunk_index = state["current_chunk_index"]
        chunk_content = state["content_chunks"][chunk_index]

        logger.info(
            "chunk_processing_started",
            quiz_id=state["quiz_id"],
            chunk_index=chunk_index,
            chunk_size=len(chunk_content)
        )

        try:
            # Check if chunk was previously processed successfully
            if chunk_index in state["successful_chunks"]:
                logger.info(
                    "chunk_already_processed",
                    chunk_index=chunk_index
                )
                state["current_chunk_index"] += 1
                return state

            # Apply circuit breaker and retry logic
            @retry_with_backoff(self.content_retry_config)
            async def process_chunk():
                return await self._process_content_chunk(chunk_content)

            chunk_start_time = time.time()
            processed_content = await self.llm_circuit_breaker.call(process_chunk)
            chunk_processing_time = time.time() - chunk_start_time

            # Update state with successful processing
            state["checkpoint_data"][f"chunk_{chunk_index}"] = processed_content
            state["chunk_processing_times"].append(chunk_processing_time)
            state["workflow_state"] = WorkflowState.GENERATING_QUESTIONS.value

            logger.info(
                "chunk_processing_completed",
                chunk_index=chunk_index,
                processing_time=chunk_processing_time
            )

            return state

        except Exception as e:
            error_type = self._classify_error(e)

            logger.error(
                "chunk_processing_failed",
                chunk_index=chunk_index,
                error_type=error_type,
                error=str(e)
            )

            state.update({
                "current_error_type": error_type,
                "last_error_time": datetime.utcnow().isoformat(),
                "error_count": state["error_count"] + 1
            })

            # Add to failed chunks
            if chunk_index not in state["failed_chunks"]:
                state["failed_chunks"].append(chunk_index)

            state["workflow_state"] = WorkflowState.RECOVERING.value
            return state

    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=1.0))
    async def generate_question_resilient(self, state: MCQGenerationState) -> MCQGenerationState:
        """Generate question with resilience patterns."""

        chunk_index = state["current_chunk_index"]

        try:
            # Get processed content from checkpoint
            content_key = f"chunk_{chunk_index}"
            if content_key not in state["checkpoint_data"]:
                raise ValueError(f"No processed content found for chunk {chunk_index}")

            processed_content = state["checkpoint_data"][content_key]

            # Generate question with circuit breaker protection
            @retry_with_backoff(self.llm_retry_config)
            async def generate_with_retry():
                return await self._generate_single_question(processed_content)

            question_data = await self.llm_circuit_breaker.call(generate_with_retry)

            # Add to generated questions
            state["generated_questions"].append(question_data)
            state["questions_generated"] = len(state["generated_questions"])

            # Mark chunk as successful
            if chunk_index not in state["successful_chunks"]:
                state["successful_chunks"].append(chunk_index)

            # Remove from failed chunks if it was there
            if chunk_index in state["failed_chunks"]:
                state["failed_chunks"].remove(chunk_index)

            # Reset retry count for this chunk
            state["retry_count"] = 0

            logger.info(
                "question_generated_successfully",
                quiz_id=state["quiz_id"],
                chunk_index=chunk_index,
                questions_count=state["questions_generated"]
            )

            # Move to next chunk
            state["current_chunk_index"] += 1
            state["workflow_state"] = WorkflowState.VALIDATION.value

            return state

        except Exception as e:
            error_type = self._classify_error(e)
            state["retry_count"] += 1

            logger.error(
                "question_generation_failed",
                chunk_index=chunk_index,
                retry_count=state["retry_count"],
                error_type=error_type,
                error=str(e)
            )

            state.update({
                "current_error_type": error_type,
                "last_error_time": datetime.utcnow().isoformat(),
                "error_count": state["error_count"] + 1
            })

            state["workflow_state"] = WorkflowState.RECOVERING.value
            return state

    async def handle_error(self, state: MCQGenerationState) -> MCQGenerationState:
        """Comprehensive error handling with recovery strategies."""

        error_type = state.get("current_error_type", ErrorType.UNKNOWN.value)
        error_count = state["error_count"]
        retry_count = state["retry_count"]

        logger.warning(
            "error_recovery_initiated",
            quiz_id=state["quiz_id"],
            error_type=error_type,
            error_count=error_count,
            retry_count=retry_count
        )

        # Check if we've exceeded maximum errors
        if error_count >= state["max_errors"]:
            logger.error(
                "workflow_failed_max_errors",
                quiz_id=state["quiz_id"],
                max_errors=state["max_errors"]
            )
            state["workflow_state"] = WorkflowState.FAILED.value
            return state

        # Apply recovery strategy based on error type
        recovery_strategy = self._get_recovery_strategy(error_type, retry_count)

        if recovery_strategy == "retry":
            if retry_count < state["max_retries_per_chunk"]:
                logger.info(
                    "applying_retry_strategy",
                    retry_count=retry_count,
                    max_retries=state["max_retries_per_chunk"]
                )

                # Apply backoff delay
                delay = min(2 ** retry_count, 60)  # Exponential backoff, max 60s
                await asyncio.sleep(delay)

                state["workflow_state"] = WorkflowState.CONTENT_PROCESSING.value
                return state
            else:
                # Exceeded retries for this chunk, skip it
                logger.warning(
                    "chunk_skipped_max_retries",
                    chunk_index=state["current_chunk_index"]
                )
                state["current_chunk_index"] += 1
                state["retry_count"] = 0
                state["workflow_state"] = WorkflowState.CONTENT_PROCESSING.value
                return state

        elif recovery_strategy == "fallback":
            logger.info("applying_fallback_strategy", error_type=error_type)
            state["fallback_strategy"] = self._select_fallback_strategy(error_type)
            state["workflow_state"] = WorkflowState.CONTENT_PROCESSING.value
            return state

        elif recovery_strategy == "skip_chunk":
            logger.warning(
                "skipping_problematic_chunk",
                chunk_index=state["current_chunk_index"]
            )
            state["current_chunk_index"] += 1
            state["retry_count"] = 0
            state["current_error_type"] = None
            state["workflow_state"] = WorkflowState.CONTENT_PROCESSING.value
            return state

        else:  # fail
            logger.error(
                "workflow_failed_unrecoverable",
                error_type=error_type
            )
            state["workflow_state"] = WorkflowState.FAILED.value
            return state

    def _classify_error(self, error: Exception) -> str:
        """Classify error for appropriate recovery strategy."""

        error_str = str(error).lower()

        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT.value
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT.value
        elif "json" in error_str or "invalid" in error_str:
            return ErrorType.INVALID_RESPONSE.value
        elif "token" in error_str or "too long" in error_str:
            return ErrorType.CONTENT_TOO_LONG.value
        elif "model" in error_str or "unavailable" in error_str:
            return ErrorType.MODEL_UNAVAILABLE.value
        elif "database" in error_str or "connection" in error_str:
            return ErrorType.DATABASE_ERROR.value
        else:
            return ErrorType.UNKNOWN.value

    def _get_recovery_strategy(self, error_type: str, retry_count: int) -> str:
        """Determine recovery strategy based on error type and retry count."""

        strategies = {
            ErrorType.RATE_LIMIT.value: "retry" if retry_count < 2 else "fallback",
            ErrorType.TIMEOUT.value: "retry" if retry_count < 3 else "skip_chunk",
            ErrorType.INVALID_RESPONSE.value: "retry" if retry_count < 2 else "fallback",
            ErrorType.CONTENT_TOO_LONG.value: "fallback",
            ErrorType.MODEL_UNAVAILABLE.value: "fallback",
            ErrorType.DATABASE_ERROR.value: "retry" if retry_count < 1 else "fail",
            ErrorType.UNKNOWN.value: "retry" if retry_count < 1 else "skip_chunk"
        }

        return strategies.get(error_type, "fail")

    def _select_fallback_strategy(self, error_type: str) -> str:
        """Select appropriate fallback strategy."""

        fallbacks = {
            ErrorType.RATE_LIMIT.value: "use_cached_model",
            ErrorType.CONTENT_TOO_LONG.value: "split_content",
            ErrorType.MODEL_UNAVAILABLE.value: "use_backup_model",
            ErrorType.INVALID_RESPONSE.value: "use_template_generation"
        }

        return fallbacks.get(error_type, "use_template_generation")

    async def apply_fallback_strategy(self, state: MCQGenerationState) -> MCQGenerationState:
        """Apply selected fallback strategy."""

        strategy = state.get("fallback_strategy")

        if strategy == "split_content":
            # Split current chunk into smaller pieces
            current_chunk = state["content_chunks"][state["current_chunk_index"]]
            smaller_chunks = self._split_content_chunk(current_chunk)

            # Replace current chunk with smaller chunks
            state["content_chunks"][state["current_chunk_index"]:state["current_chunk_index"]+1] = smaller_chunks

            logger.info(
                "content_split_applied",
                original_chunks=1,
                new_chunks=len(smaller_chunks)
            )

        elif strategy == "use_backup_model":
            # Switch to backup model (implementation specific)
            state["checkpoint_data"]["use_backup_model"] = True

        elif strategy == "use_template_generation":
            # Use template-based generation as fallback
            state["checkpoint_data"]["use_template"] = True

        # Reset error state and continue
        state["current_error_type"] = None
        state["retry_count"] = 0
        state["fallback_strategy"] = None

        return state

    def route_after_processing(self, state: MCQGenerationState) -> str:
        """Route workflow after chunk processing."""

        if state["workflow_state"] == WorkflowState.RECOVERING.value:
            return "error"
        elif state["current_chunk_index"] >= len(state["content_chunks"]):
            return "complete"
        else:
            return "generate"

    def route_after_generation(self, state: MCQGenerationState) -> str:
        """Route workflow after question generation."""

        if state["workflow_state"] == WorkflowState.RECOVERING.value:
            if state["retry_count"] < state["max_retries_per_chunk"]:
                return "retry"
            else:
                return "error"
        elif state["questions_generated"] >= state["target_question_count"]:
            return "validate"
        else:
            return "next_chunk"

    def route_after_validation(self, state: MCQGenerationState) -> str:
        """Route workflow after question validation."""

        if state["workflow_state"] == WorkflowState.RECOVERING.value:
            return "error"
        elif len(state["generated_questions"]) % 5 == 0:  # Checkpoint every 5 questions
            return "save_checkpoint"
        else:
            return "continue"

    def route_after_error_handling(self, state: MCQGenerationState) -> str:
        """Route workflow after error handling."""

        if state["workflow_state"] == WorkflowState.FAILED.value:
            return "fail"
        elif state.get("fallback_strategy"):
            return "fallback"
        else:
            return "retry"

# Usage example and integration
async def run_resilient_mcq_generation(
    quiz_id: UUID,
    content_chunks: List[str],
    target_count: int
) -> Dict[str, Any]:
    """Run resilient MCQ generation workflow."""

    service = ResilientMCQGenerationService()
    workflow = service.build_resilient_workflow()

    initial_state = MCQGenerationState(
        quiz_id=str(quiz_id),
        content_chunks=content_chunks,
        current_chunk_index=0,
        questions_generated=0,
        target_question_count=target_count,
        generated_questions=[]
    )

    try:
        final_state = await workflow.ainvoke(initial_state)

        return {
            "status": "completed" if final_state["workflow_state"] == WorkflowState.COMPLETED.value else "failed",
            "questions_generated": final_state["questions_generated"],
            "target_count": target_count,
            "successful_chunks": final_state["successful_chunks"],
            "failed_chunks": final_state["failed_chunks"],
            "total_errors": final_state["error_count"],
            "processing_time": final_state["chunk_processing_times"],
            "generated_questions": final_state["generated_questions"]
        }

    except Exception as e:
        logger.error(
            "workflow_execution_failed",
            quiz_id=str(quiz_id),
            error=str(e)
        )
        raise
```

## Implementation Details

### Files to Modify

```
backend/
├── app/
│   ├── core/
│   │   └── resilience.py           # NEW: Resilience patterns
│   ├── services/
│   │   ├── mcq_generation.py       # UPDATE: Add error recovery
│   │   └── mcq_generation_resilient.py  # NEW: Resilient implementation
│   ├── models/
│   │   └── workflow_state.py       # NEW: Workflow state persistence
│   └── tests/
│       ├── services/
│       │   └── test_resilient_mcq.py  # NEW: Resilience tests
│       └── core/
│           └── test_resilience.py     # NEW: Pattern tests
```

### Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    # Resilience configuration
    MCQ_MAX_RETRIES: int = 3
    MCQ_CIRCUIT_BREAKER_THRESHOLD: int = 5
    MCQ_CIRCUIT_BREAKER_TIMEOUT: int = 120
    MCQ_CHUNK_TIMEOUT: int = 300
    MCQ_ENABLE_FALLBACK: bool = True
```

## Testing Requirements

### Unit Tests

```python
# File: app/tests/core/test_resilience.py
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

from app.core.resilience import CircuitBreaker, CircuitBreakerConfig, retry_with_backoff, RetryConfig

@pytest.mark.asyncio
async def test_circuit_breaker_open_after_failures():
    """Test circuit breaker opens after threshold failures."""

    config = CircuitBreakerConfig(failure_threshold=3)
    breaker = CircuitBreaker(config)

    async def failing_function():
        raise Exception("Test failure")

    # First 3 calls should fail normally
    for i in range(3):
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(failing_function)

    # 4th call should raise circuit breaker exception
    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(failing_function)

@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    """Test retry decorator with exponential backoff."""

    call_count = 0

    @retry_with_backoff(RetryConfig(max_attempts=3, base_delay=0.01))
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "success"

    start_time = asyncio.get_event_loop().time()
    result = await flaky_function()
    end_time = asyncio.get_event_loop().time()

    assert result == "success"
    assert call_count == 3
    # Should have some delay due to backoff
    assert end_time - start_time > 0.01

# File: app/tests/services/test_resilient_mcq.py
@pytest.mark.asyncio
async def test_resilient_workflow_error_recovery():
    """Test workflow recovers from LLM failures."""

    service = ResilientMCQGenerationService()

    # Mock LLM calls to fail then succeed
    call_count = 0
    async def mock_llm_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("Rate limit exceeded")
        return {"question": "Test question", "answer": "Test answer"}

    service._generate_single_question = mock_llm_call

    initial_state = MCQGenerationState(
        quiz_id="test-quiz",
        content_chunks=["test content"],
        current_chunk_index=0,
        questions_generated=0,
        target_question_count=1,
        generated_questions=[]
    )

    # Should eventually succeed after retries
    result_state = await service.generate_question_resilient(initial_state)

    assert result_state["questions_generated"] == 1
    assert len(result_state["generated_questions"]) == 1
    assert call_count == 3  # Failed twice, succeeded on third

@pytest.mark.asyncio
async def test_workflow_fallback_strategy():
    """Test workflow applies fallback strategies."""

    service = ResilientMCQGenerationService()

    # Test content splitting fallback
    state = MCQGenerationState(
        quiz_id="test-quiz",
        content_chunks=["very long content that exceeds token limits"],
        current_chunk_index=0,
        questions_generated=0,
        target_question_count=1,
        generated_questions=[],
        fallback_strategy="split_content"
    )

    result_state = await service.apply_fallback_strategy(state)

    # Should have split the content into multiple chunks
    assert len(result_state["content_chunks"]) > 1
    assert result_state["fallback_strategy"] is None  # Reset after application

@pytest.mark.asyncio
async def test_workflow_checkpoint_recovery():
    """Test workflow can resume from checkpoints."""

    service = ResilientMCQGenerationService()

    # Simulate partial workflow completion
    state = MCQGenerationState(
        quiz_id="test-quiz",
        content_chunks=["chunk1", "chunk2", "chunk3"],
        current_chunk_index=1,
        questions_generated=2,
        target_question_count=5,
        generated_questions=[
            {"question": "Q1", "answer": "A1"},
            {"question": "Q2", "answer": "A2"}
        ],
        checkpoint_data={
            "chunk_0": "processed content 0",
            "chunk_1": "processed content 1"
        },
        successful_chunks=[0, 1],
        failed_chunks=[]
    )

    # Should resume from where it left off
    assert state["current_chunk_index"] == 1
    assert state["questions_generated"] == 2
    assert len(state["successful_chunks"]) == 2
```

### Integration Tests

```python
# File: app/tests/integration/test_mcq_resilience.py
@pytest.mark.asyncio
async def test_full_resilient_workflow(db_session, test_quiz):
    """Test complete resilient workflow end-to-end."""

    # Create content chunks
    content_chunks = [
        "This is test content for question generation.",
        "Another chunk of content for testing.",
        "Final chunk with some educational material."
    ]

    # Run resilient workflow
    result = await run_resilient_mcq_generation(
        quiz_id=test_quiz.id,
        content_chunks=content_chunks,
        target_count=3
    )

    assert result["status"] == "completed"
    assert result["questions_generated"] >= 1
    assert len(result["generated_questions"]) >= 1

@pytest.mark.asyncio
async def test_workflow_with_simulated_failures():
    """Test workflow handles various failure scenarios."""

    # Test with different failure types
    failure_scenarios = [
        "rate_limit_error",
        "timeout_error",
        "invalid_json_error",
        "content_too_long_error"
    ]

    for scenario in failure_scenarios:
        with patch('app.services.mcq_generation_resilient.ResilientMCQGenerationService._generate_single_question') as mock_generate:
            # Configure mock to simulate specific failure
            if scenario == "rate_limit_error":
                mock_generate.side_effect = [
                    Exception("Rate limit exceeded"),
                    Exception("Rate limit exceeded"),
                    {"question": "Test", "answer": "Answer"}
                ]

            # Run workflow and verify it recovers
            result = await run_resilient_mcq_generation(
                quiz_id=uuid.uuid4(),
                content_chunks=["test content"],
                target_count=1
            )

            assert result["status"] == "completed"
```

## Code Quality Improvements

### Monitoring and Observability

```python
# Add comprehensive monitoring
from prometheus_client import Counter, Histogram, Gauge

workflow_errors = Counter('mcq_workflow_errors_total', 'MCQ workflow errors', ['error_type'])
workflow_duration = Histogram('mcq_workflow_duration_seconds', 'MCQ workflow duration')
active_workflows = Gauge('mcq_active_workflows', 'Currently active workflows')
circuit_breaker_state = Gauge('circuit_breaker_state', 'Circuit breaker state', ['service'])
```

### Health Checks

```python
# File: app/api/routes/health.py
@router.get("/mcq-generation")
async def check_mcq_generation_health():
    """Check MCQ generation service health."""

    service = ResilientMCQGenerationService()

    # Test circuit breaker states
    llm_breaker_healthy = service.llm_circuit_breaker.state != CircuitState.OPEN
    db_breaker_healthy = service.db_circuit_breaker.state != CircuitState.OPEN

    return {
        "status": "healthy" if llm_breaker_healthy and db_breaker_healthy else "degraded",
        "llm_circuit_breaker": service.llm_circuit_breaker.state.value,
        "db_circuit_breaker": service.db_circuit_breaker.state.value,
        "details": {
            "llm_failures": service.llm_circuit_breaker.failure_count,
            "db_failures": service.db_circuit_breaker.failure_count
        }
    }
```

## Migration Strategy

### Phase 1: Add Resilience Infrastructure (Day 1)

1. Implement core resilience patterns (circuit breaker, retry)
2. Add comprehensive error classification
3. Create test infrastructure

### Phase 2: Build Resilient Workflow (Day 2)

1. Implement resilient LangGraph workflow
2. Add state persistence and checkpointing
3. Implement fallback strategies

### Phase 3: Integration and Testing (Day 3)

1. Integrate with existing MCQ generation service
2. Add monitoring and health checks
3. Comprehensive testing and validation

### Feature Flag Migration

```python
# app/core/config.py
ENABLE_RESILIENT_MCQ_GENERATION: bool = False

# Usage in service
if settings.ENABLE_RESILIENT_MCQ_GENERATION:
    return await run_resilient_mcq_generation(...)
else:
    return await run_legacy_mcq_generation(...)
```

## Success Criteria

### Reliability Metrics

- **Workflow Success Rate**: >95% even with individual component failures
- **Error Recovery Time**: <60s for most error types
- **Circuit Breaker Effectiveness**: Prevents cascading failures
- **Fallback Success Rate**: >80% when primary methods fail

### Performance Metrics

- **No significant performance regression** in happy path
- **Faster recovery** from failures than manual intervention
- **Resource efficiency** through proper timeout and retry policies

### Monitoring Alerts

```python
# Alert conditions
workflow_failure_rate > 10%  # Overall failure rate too high
circuit_breaker_open > 5min  # Circuit breaker stuck open
error_rate_spike > 50/min    # Sudden error spike
workflow_duration > 600s     # Workflows taking too long
```

---
