# Quiz Orchestration Refactoring Documentation

## Overview

This document details the comprehensive refactoring of the Quiz module's orchestration layer to establish clear separation of concerns and eliminate circular dependencies between the Quiz, Canvas, and Content Extraction modules.

## Problem Statement

### Original Issues

The original architecture suffered from several critical problems:

1. **Circular Dependencies**: Quiz flows imported Canvas flows, which in turn imported Quiz services
2. **Mixed Responsibilities**: Canvas flows contained Quiz domain logic and database transactions
3. **Unclear Ownership**: No single component owned the complete quiz lifecycle orchestration
4. **Tight Coupling**: Direct imports between modules created hard-to-test, tightly coupled code
5. **Transaction Management**: Quiz entity transactions were scattered across multiple modules

### Architectural Smells

- Canvas flows manipulating Quiz database models directly
- Business orchestration mixed with HTTP routing logic
- Cross-domain concerns handled in multiple places
- No clear dependency direction between modules

## Solution Architecture

### Core Principles Applied

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Domain Ownership**: Quiz module owns quiz lifecycle, Canvas module owns Canvas API operations
3. **Functional Dependency Injection**: Clean boundaries through function parameter injection
4. **Transaction Ownership**: Database transactions managed within appropriate domain boundaries

### New Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Quiz Router   │    │  Quiz           │    │   Canvas        │
│   (HTTP Layer)  │───▶│  Orchestrator   │───▶│   Flows         │
│                 │    │  (Workflow)     │    │  (API Ops)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Content        │
                       │  Extraction     │
                       │  (Processing)   │
                       └─────────────────┘
```

## Implementation Details

### 1. Quiz Orchestrator (`quiz/orchestrator.py`)

**Purpose**: Owns the complete quiz lifecycle orchestration using functional composition and dependency injection.

**Key Functions**:

```python
async def orchestrate_quiz_content_extraction(
    quiz_id: UUID,
    course_id: int,
    module_ids: list[int],
    canvas_token: str,
    content_extractor: ContentExtractorFunc,  # ← Injected dependency
    content_summarizer: ContentSummaryFunc,  # ← Injected dependency
) -> None:
```

**Responsibilities**:
- Quiz lifecycle state management (content extraction → question generation → export)
- Cross-domain workflow coordination
- Quiz entity transaction management
- Background task orchestration
- Error handling and status updates

**Pattern Used**: Two-transaction pattern for reliable background processing:
1. **Transaction 1**: Reserve job (fast)
2. **I/O Operation**: External API calls (outside transaction)
3. **Transaction 2**: Save results (fast)

### 2. Canvas Flows Cleanup (`canvas/flows.py`)

**Before**: Mixed Quiz domain logic with Canvas API operations
**After**: Pure Canvas API operations only

**Removed**:
- All Quiz database model imports and manipulations
- Quiz status management logic
- Question persistence operations
- Cross-domain orchestration logic

**Kept**:
- Content extraction from Canvas modules
- Canvas quiz creation
- Canvas question export
- Content summarization utilities

### 3. Quiz Router Updates (`quiz/router.py`)

**Before**: Direct imports and calls to various flow functions
**After**: Dependency injection pattern with orchestrator functions

**Example Change**:

```python
# Before
from .flows import quiz_content_extraction_flow

background_tasks.add_task(
    quiz_content_extraction_flow,
    quiz_id,
    course_id,
    module_ids,
    canvas_token,
)

# After
from .orchestrator import orchestrate_quiz_content_extraction
from src.canvas.flows import extract_content_for_modules, get_content_summary

background_tasks.add_task(
    orchestrate_quiz_content_extraction,
    quiz_id,
    course_id,
    module_ids,
    canvas_token,
    extract_content_for_modules,  # ← Injected dependency
    get_content_summary,          # ← Injected dependency
)
```

## What Has Changed

### File Structure Changes

| Status | File | Change Description |
|--------|------|-------------------|
| 🔄 **Modified** | `quiz/orchestrator.py` | **COMPLETED**: Refactored to improve separation of concerns |
| 🔄 **Modified** | `quiz/service.py` | **COMPLETED**: Added domain-specific status management functions |
| 🔄 **Modified** | `question/service.py` | **COMPLETED**: Added question export preparation functions |

### Actual Changes Implemented (December 2024)

#### 1. **Domain Service Extraction**

**Question Service Enhancements** (`question/service.py`):
- ✅ **Added** `prepare_questions_for_export(quiz_id)` - Moved question export logic from orchestrator
- ✅ **Added** `update_question_canvas_ids(session, question_data, export_results)` - Handles Canvas ID updates

**Quiz Service Enhancements** (`quiz/service.py`):
- ✅ **Added** `reserve_quiz_job(session, quiz_id, job_type)` - Centralized job reservation with row locking
- ✅ **Added** `update_quiz_status(session, quiz_id, status_type, status_value, **fields)` - Centralized status updates

#### 2. **Orchestrator Simplification** (`quiz/orchestrator.py`):

**Removed Complex Logic**:
- ✅ **Removed** `_load_and_extract_question_data()` function (moved to question service)
- ✅ **Removed** Direct Question model imports and manipulations
- ✅ **Removed** Manual transaction management for status updates

**Simplified Transaction Patterns**:
- ✅ **Updated** Content extraction to use `reserve_quiz_job()` and `update_quiz_status()`
- ✅ **Updated** Question generation to use domain service functions
- ✅ **Updated** Quiz export to use question service for data preparation

#### 3. **Clean Domain Boundaries**:

**Before Refactoring Issues**:
```python
# Quiz orchestrator directly importing Question models
from src.question.models import Question
from src.question.types import QuestionType, get_question_type_registry
from src.question.types.mcq import MultipleChoiceData

# Direct database manipulation across domains
question_obj = await session.get(Question, question_data["id"])
if question_obj:
    question_obj.canvas_item_id = item_result.get("item_id")
```

**After Refactoring**:
```python
# Clean service calls within domain boundaries
from src.question import service as question_service

# Question service handles all question-related operations
question_data = await question_service.prepare_questions_for_export(quiz_id)
await question_service.update_question_canvas_ids(session, question_data, export_results)
```

### Import Changes

**Old Pattern**:
```python
from src.quiz.flows import (
    quiz_content_extraction_flow,
    quiz_question_generation_flow,
    quiz_export_background_flow,
)
```

**New Pattern**:
```python
from src.quiz.orchestrator import (
    orchestrate_quiz_content_extraction,
    orchestrate_quiz_question_generation,
    orchestrate_quiz_export_to_canvas,
)
```

### Dependency Injection Pattern

**Before**: Direct coupling
```python
# Canvas flows directly imported Quiz services
from src.quiz.service import get_quiz_for_update
```

**After**: Functional injection
```python
# Canvas functions injected as parameters
async def orchestrate_quiz_export_to_canvas(
    quiz_id: UUID,
    canvas_token: str,
    quiz_creator: QuizCreatorFunc,      # ← Injected
    question_exporter: QuestionExporterFunc,  # ← Injected
) -> dict[str, Any]:
```

### Transaction Management Changes

**Before**: Quiz transactions scattered across Canvas flows
**After**: All Quiz transactions managed in Quiz orchestrator

```python
# Now in quiz/orchestrator.py
async def _save_export_results(session: Any, quiz_id: UUID) -> dict[str, Any]:
    """Save the export results to the quiz."""
    quiz = await get_quiz_for_update(session, quiz_id)
    if quiz:
        quiz.canvas_quiz_id = canvas_quiz["id"]
        quiz.export_status = "completed"
        quiz.exported_at = datetime.now(timezone.utc)
```

## Developer Guidelines

### When Adding New Quiz Workflows

1. **Use the Orchestrator**: Add new workflow functions to `quiz/orchestrator.py`
2. **Follow Dependency Injection**: Accept external service functions as parameters
3. **Maintain Transaction Patterns**: Use the two-transaction pattern for reliability
4. **Single Responsibility**: Keep orchestrator focused on workflow coordination

**Example Template**:
```python
async def orchestrate_new_quiz_workflow(
    quiz_id: UUID,
    workflow_params: dict[str, Any],
    external_service_func: Callable,  # ← Always inject dependencies
) -> WorkflowResult:
    """
    Orchestrate a new quiz workflow.

    Args:
        quiz_id: UUID of the quiz
        workflow_params: Workflow-specific parameters
        external_service_func: Injected external service function
    """
    # 1. Reserve job transaction
    # 2. External operations (outside transaction)
    # 3. Save results transaction
```

### When Modifying Canvas Operations

1. **Keep Canvas Flows Pure**: No Quiz domain logic in Canvas flows
2. **Return Clean Data**: Canvas functions should return simple dicts or primitives
3. **No Database Transactions**: Canvas flows should not manage Quiz entity transactions
4. **Stateless Functions**: Canvas operations should be pure functions when possible

**Canvas Function Guidelines**:
```python
async def new_canvas_operation(
    canvas_token: str,
    canvas_params: dict[str, Any],
) -> dict[str, Any]:
    """
    Pure Canvas API operation.

    Should only:
    - Make Canvas API calls
    - Process Canvas responses
    - Return clean data

    Should NOT:
    - Import Quiz models
    - Manage Quiz transactions
    - Handle Quiz business logic
    """
```

### When Adding Background Tasks

1. **Use Orchestrator Functions**: Always call orchestrator functions from routers
2. **Inject Dependencies**: Pass required service functions as parameters
3. **Handle Errors Gracefully**: Orchestrator handles cross-domain error coordination

**Router Pattern**:
```python
@router.post("/new-operation")
async def new_operation_endpoint(
    quiz: QuizOwnership,
    background_tasks: BackgroundTasks,
):
    # Import dependencies for injection
    from src.external_service.flows import external_operation_func

    background_tasks.add_task(
        orchestrate_new_operation,
        quiz.id,
        external_operation_func,  # ← Always inject
    )
```

### Testing Considerations

1. **Mock Injected Functions**: Easy to test with dependency injection
2. **Test Orchestrator Logic**: Focus on workflow coordination
3. **Test Canvas Functions Separately**: Pure functions are easy to test
4. **Integration Tests**: Test full workflow with real dependencies

**Testing Example**:
```python
async def test_quiz_workflow():
    # Mock the injected dependencies
    mock_canvas_func = AsyncMock(return_value={"success": True})
    mock_content_func = AsyncMock(return_value={})

    # Test orchestrator with mocked dependencies
    result = await orchestrate_quiz_workflow(
        quiz_id=test_quiz_id,
        canvas_func=mock_canvas_func,  # ← Easily mocked
        content_func=mock_content_func,
    )

    # Verify orchestration logic
    assert mock_canvas_func.called
    assert result.success
```

### Common Pitfalls to Avoid

1. **Don't Add Quiz Logic to Canvas**: Keep Canvas flows pure
2. **Don't Skip Dependency Injection**: Always inject external service functions
3. **Don't Mix Transaction Boundaries**: Keep Quiz transactions in Quiz orchestrator
4. **Don't Import Across Domain Boundaries**: Use dependency injection instead
5. **Don't Bypass the Orchestrator**: Router should always use orchestrator functions

### Migration Checklist for New Features

- [ ] Workflow logic added to `quiz/orchestrator.py`
- [ ] External services injected as function parameters
- [ ] Transaction management kept within appropriate domain
- [ ] Router endpoints use orchestrator with dependency injection
- [ ] No cross-domain imports (Quiz ↔ Canvas)
- [ ] Functions remain testable with mocking
- [ ] Error handling follows established patterns

## Benefits Achieved

### Architectural Benefits

1. **Clear Separation of Concerns**: Each module has single responsibility
   - ✅ **Quiz service** owns all quiz-related database operations
   - ✅ **Question service** owns all question-related database operations
   - ✅ **Orchestrator** focuses only on workflow coordination

2. **Eliminated Cross-Domain Dependencies**: Clean domain boundaries
   - ✅ **Removed** direct Question model imports from Quiz orchestrator
   - ✅ **Established** clear service interfaces between domains
   - ✅ **Eliminated** transaction management across domain boundaries

3. **Improved Testability**: Domain services can be easily mocked
   - ✅ **Service functions** have clear interfaces
   - ✅ **Database operations** isolated within domain services
   - ✅ **Orchestrator logic** can be tested with mocked services

4. **Better Error Handling**: Domain-specific error management
   - ✅ **Quiz service** handles quiz-related errors
   - ✅ **Question service** handles question-related errors
   - ✅ **Orchestrator** coordinates cross-domain error flows

5. **Maintainable Code**: Clear ownership and boundaries
   - ✅ **Single Responsibility Principle** enforced
   - ✅ **Domain-Driven Design** principles applied
   - ✅ **Clean interfaces** between components

### Development Benefits

1. **Easier Debugging**: Clear ownership of operations
   - ✅ **Quiz issues** → Check quiz service
   - ✅ **Question issues** → Check question service
   - ✅ **Workflow issues** → Check orchestrator

2. **Safer Refactoring**: Reduced coupling between components
   - ✅ **Service interfaces** provide stable contracts
   - ✅ **Domain boundaries** prevent cascading changes
   - ✅ **Clear dependencies** make impact analysis easier

3. **Cleaner Code Reviews**: Obvious violations are easy to spot
   - ✅ **Domain violations** immediately visible
   - ✅ **SRP violations** stand out clearly
   - ✅ **Proper abstractions** enforced

4. **Reduced Cognitive Load**: Clear module responsibilities
   - ✅ **Developers** know where to make changes
   - ✅ **Code organization** follows business domains
   - ✅ **Function names** clearly indicate purpose

### Actual Improvements Measured

**Code Quality Metrics**:
- ✅ **Linting**: All ruff and mypy checks pass
- ✅ **Type Safety**: Proper type annotations maintained
- ✅ **Import Hygiene**: No circular or cross-domain imports

**Complexity Reduction**:
- ✅ **Orchestrator**: Reduced from complex database operations to simple service calls
- ✅ **Transaction Management**: Centralized within appropriate domains
- ✅ **Function Length**: Long orchestrator functions broken into focused service functions

**Maintainability**:
- ✅ **Clear Interfaces**: Service functions have obvious contracts
- ✅ **Single Responsibility**: Each function has one clear purpose
- ✅ **Domain Ownership**: Clear data ownership boundaries

## Conclusion

### December 2024 Refactoring Summary

This focused refactoring successfully addressed the core separation of concerns issues in the quiz orchestrator with **minimal architectural changes**. The approach prioritized:

**✅ Completed Objectives**:
1. **Moved domain logic to appropriate services** - Question export logic → Question service, Quiz status management → Quiz service
2. **Simplified orchestrator responsibilities** - Now focuses only on workflow coordination
3. **Eliminated cross-domain database operations** - Each service owns its domain's data
4. **Maintained existing functionality** - No breaking changes to API or workflows
5. **Improved code quality** - All linting and type checking passes

**🎯 Key Success Factors**:
- **Simple approach** - Enhanced existing files rather than major architectural overhaul
- **Domain-driven** - Clear boundaries between Quiz and Question domains
- **Backward compatible** - No changes to external interfaces
- **Testable** - Service functions can be easily mocked and tested
- **Maintainable** - Clear ownership and single responsibility

**📈 Impact**:
- **Developers** can now easily identify where to make Quiz vs Question changes
- **Code reviews** will catch domain boundary violations more easily
- **Testing** is simpler with clear service interfaces
- **Future features** have clear patterns to follow

This pragmatic refactoring demonstrates that significant architectural improvements can be achieved through focused, incremental changes that respect existing system boundaries while establishing cleaner separation of concerns.
