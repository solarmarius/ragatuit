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
| ✅ **Created** | `quiz/orchestrator.py` | New orchestration layer with functional dependency injection |
| 🔄 **Modified** | `quiz/router.py` | Updated to use orchestrator with dependency injection |
| 🔄 **Modified** | `canvas/flows.py` | Cleaned to contain only Canvas API operations |
| 🔄 **Modified** | `quiz/__init__.py` | Updated exports to use orchestrator functions |
| 🔄 **Modified** | `canvas/__init__.py` | Removed obsolete export references |
| ❌ **Deleted** | `quiz/flows.py` | Completely removed (no backward compatibility) |

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
2. **Eliminated Circular Dependencies**: Clean dependency direction
3. **Improved Testability**: Easy mocking with dependency injection
4. **Better Error Handling**: Centralized cross-domain error coordination
5. **Maintainable Code**: Clear ownership and boundaries

### Development Benefits

1. **Easier Debugging**: Clear workflow ownership in orchestrator
2. **Safer Refactoring**: Functional boundaries reduce coupling
3. **Cleaner Code Reviews**: Obvious violations of separation of concerns
4. **Better Documentation**: Self-documenting dependency injection
5. **Reduced Cognitive Load**: Clear module responsibilities

### Future Scalability

1. **Easy Feature Addition**: Clear patterns for new workflows
2. **Service Extraction**: Canvas flows ready for microservice extraction
3. **Alternative Implementations**: Easy to swap Canvas for other LMS systems
4. **Parallel Development**: Teams can work on different modules independently

## Conclusion

This refactoring successfully transformed a tightly-coupled, circular dependency architecture into a clean, maintainable system following Domain-Driven Design principles. The functional dependency injection pattern provides the benefits of clean architecture while keeping the implementation simple and testable.

The new architecture supports future growth and makes the codebase significantly more maintainable for developers while eliminating the original architectural smells.
