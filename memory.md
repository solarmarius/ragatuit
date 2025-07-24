# Memory File: Partial Failure Saving Implementation

**Date**: July 24, 2025
**Project**: Rag@UiT - Canvas LMS Quiz Generator
**Feature**: Batch-Level Question Generation with Partial Success Support

## Conversation Overview

### Main Objectives
Implementing a comprehensive feature to handle partial failures in quiz question generation by transitioning from an "all-or-nothing" approach to batch-level success tracking. The goal is to save successfully generated questions even when some batches fail, allowing users to review partial results and retry only failed portions.

### Key Problem Statement
- **Current Issue**: If 190/200 questions generate successfully but 10 fail validation, the entire quiz is marked as FAILED and ALL 190 questions are lost
- **Bug**: Failed generations still save questions to database, causing duplicate generation on retry
- **Solution**: Implement batch-level tracking where each batch (module + question_type + count) is evaluated independently

## User Context & Requirements

### Technical Background
- User is working on a FastAPI + React application with PostgreSQL database
- System uses SQLModel, TypeScript, Docker Compose development environment
- Existing consolidated quiz status system with 7 states
- Current 80% success threshold system needs replacement with 100% batch success requirement

### Specific Requirements Clarified
1. **Success Criteria**: At least ONE batch with 100% validation success → `READY_FOR_REVIEW_PARTIAL`
2. **Batch Definition**: module_id + question_type + target_count
3. **Retry Behavior**: Only retry batches that didn't meet their target question count
4. **Data Preservation**: NEVER delete existing validated questions
5. **Progress Display**: Show "X questions generated successfully (Y remaining)"
6. **API Design**: Extend existing `/generate-questions` endpoint with retry logic

## Implementation Plan Structure

### Phase-Based Approach with Quality Gates
Each phase requires: Backend (lint.sh + test.sh + commit) | Frontend (npx tsc --noEmit + commit)

**8 Phases Total:**
1. ✅ Backend schema updates (READY_FOR_REVIEW_PARTIAL status)
2. ✅ Orchestrator logic for batch-level tracking
3. ✅ Batch workflow 100% success requirement
4. 🔄 Generation service selective retry enhancement (IN PROGRESS)
5. ⏳ Router partial state support
6. ⏳ Frontend constants update
7. ⏳ Frontend component updates
8. ⏳ Integration testing

## Work Completed

### Phase 1: Schema Updates ✅
**File**: `backend/src/quiz/schemas.py`
**Changes**: Added `READY_FOR_REVIEW_PARTIAL = "ready_for_review_partial"` to QuizStatus enum
**Commit**: `213fe97` - "feat: add READY_FOR_REVIEW_PARTIAL status for batch-level success tracking"

### Phase 2: Orchestrator Logic ✅
**File**: `backend/src/quiz/orchestrator.py`
**Key Changes**:
- Replaced `_execute_generation_workflow()` with batch-level tracking logic
- Added `_store_generation_metadata()` function for comprehensive batch tracking
- Updated `_save_generation_result()` to handle `partial_success` status
- Changed success criteria from 80% overall threshold to batch-level 100% requirement

**Critical Implementation Details**:
```python
# New workflow calls:
batch_results = await generation_service.generate_questions_for_quiz_with_batch_tracking(...)

# Batch analysis logic:
for module_id, module_info in quiz.selected_modules.items():
    batch_key = f"{module_id}_{question_type.value}_{expected_count}"
    if actual_count == expected_count:  # 100% success required
        successful_batches.append(...)
    else:
        failed_batches.append(...)

# Status determination:
if len(successful_batches) == 0: return "failed"
elif len(failed_batches) == 0: return "completed"
else: return "partial_success"
```

**Metadata Structure**:
```json
{
  "generation_attempts": [
    {
      "attempt_number": 1,
      "timestamp": "2024-07-24T12:00:00Z",
      "overall_status": "partial_success",
      "batch_results": {
        "module_123_multiple_choice_15": {
          "batch_key": "module_123_multiple_choice_15",
          "module_id": "123",
          "question_type": "multiple_choice",
          "target_count": 15,
          "generated_count": 15,
          "status": "success"
        }
      }
    }
  ],
  "failed_batches": ["module_456_multiple_choice_10"],
  "successful_batches": ["module_123_multiple_choice_15"],
  "total_questions_saved": 15,
  "total_questions_target": 25
}
```

**Commit**: `e963215` - "feat: implement batch-level success tracking in orchestrator"

### Phase 3: Batch Workflow Modification ✅
**File**: `backend/src/question/workflows/module_batch_workflow.py`
**Key Changes**:
- Modified `save_questions()` method to enforce 100% success requirement
- Added success rate calculation: `success_rate = total_questions / target_question_count`
- Only save if `success_rate >= 0.99` (allowing for floating point errors)
- Don't modify question_data field (user requirement)
- Enhanced logging for partial success scenarios

**Critical Logic**:
```python
# Only save if we achieved 100% success
if success_rate < 0.99:
    logger.warning("module_batch_not_saving_partial_success", ...)
    state.error_message = f"Batch incomplete: {total_questions}/{target_questions} questions generated"
    return state  # Don't save questions
```

**Commit**: `0de3540` - "feat: enforce 100% success requirement for batch saving"

## Current Status (Phase 4 - IN PROGRESS)

### What's Being Implemented
**File**: `backend/src/question/services/generation_service.py`
**Missing Method**: `generate_questions_for_quiz_with_batch_tracking()`

The orchestrator is calling this method but it doesn't exist yet. Need to implement:

1. **Selective Generation**: Only generate questions for batches that haven't already succeeded
2. **Metadata Awareness**: Read quiz metadata to understand which batches succeeded/failed
3. **Retry Support**: Skip successful batches, only process failed ones

### Required Implementation
```python
async def generate_questions_for_quiz_with_batch_tracking(
    self,
    quiz_id: UUID,
    extracted_content: dict[str, str],
    provider_name: str = "openai",
) -> dict[str, list[Any]]:
    # 1. Check quiz.generation_metadata for successful_batches
    # 2. Skip modules with successful batch_keys
    # 3. Only process modules that need generation
    # 4. Return results for batch analysis
```

Also need:
```python
async def get_failed_batches_for_retry(self, quiz_id: UUID) -> list[dict[str, Any]]:
    # Return detailed info about failed batches for retry scenarios
```

## Remaining Phases

### Phase 5: Router Updates
**File**: `backend/src/quiz/router.py`
**Tasks**:
- Modify `trigger_question_generation()` to support retry from `READY_FOR_REVIEW_PARTIAL`
- Add `validate_question_generation_ready_with_partial_support()` function
- Update success messages for retry scenarios

### Phase 6: Frontend Constants
**File**: `frontend/src/lib/constants.ts`
**Task**: Add `READY_FOR_REVIEW_PARTIAL: "ready_for_review_partial"` to QUIZ_STATUS

### Phase 7: Frontend Component
**File**: `frontend/src/components/Questions/QuestionGenerationTrigger.tsx`
**Major Changes**:
- Support partial success UI states
- Progress visualization with batch/question counts
- Different button text: "Retry Failed Batches" vs "Retry Question Generation"
- Progress bars and detailed statistics display

### Phase 8: Integration Testing
- End-to-end testing of partial success flow
- Verify no existing functionality broken
- Test various success/failure scenarios

## Technical Architecture

### Key Components
1. **Quiz.generation_metadata** (JSONB field) - Stores batch tracking data
2. **QuizStatus.READY_FOR_REVIEW_PARTIAL** - New status for partial success
3. **Batch Key Format**: `{module_id}_{question_type}_{target_count}`
4. **100% Success Requirement** - Per batch, not overall percentage

### Data Flow
```
1. User triggers generation
2. Orchestrator calls generation_service.generate_questions_for_quiz_with_batch_tracking()
3. Service checks existing metadata, skips successful batches
4. Batch workflow enforces 100% success before saving
5. Orchestrator analyzes results, stores metadata
6. Status set to: completed | partial_success | failed
7. Frontend shows appropriate UI based on status
```

## File Locations & Structure

### Project Structure
```
/Users/mariussolaas/ragatuit/
├── backend/src/
│   ├── quiz/
│   │   ├── schemas.py ✅
│   │   ├── orchestrator.py ✅
│   │   └── router.py ⏳
│   └── question/
│       ├── services/generation_service.py 🔄
│       └── workflows/module_batch_workflow.py ✅
└── frontend/src/
    ├── lib/constants.ts ⏳
    └── components/Questions/QuestionGenerationTrigger.tsx ⏳
```

### Development Commands
```bash
# Backend Quality Gates
cd backend && source .venv/bin/activate && bash scripts/lint.sh
cd backend && source .venv/bin/activate && bash scripts/test.sh

# Frontend Quality Gates
cd frontend && npx tsc --noEmit

# Commits with consistent format
git commit -m "feat: [description]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Critical Implementation Notes

### User Preferences/Constraints
1. **No backwards compatibility needed** - application not deployed yet
2. **Don't modify question_data field** - keep existing structure
3. **Use existing database schema** - leverage generation_metadata JSONB field
4. **Quality gates mandatory** - lint/test must pass before each commit
5. **Comprehensive documentation** - created detailed implementation guide at `/docs/partial-failure-saving-implementation-guide.md`

### Error Handling Strategy
- **Complete Failure**: No batches succeed → FAILED status
- **Partial Success**: Some batches succeed → READY_FOR_REVIEW_PARTIAL status
- **Complete Success**: All batches succeed → READY_FOR_REVIEW status
- **Retry Logic**: Only regenerate failed batches, preserve successful ones

## Next Immediate Steps

1. **Complete Phase 4**: Implement the two missing methods in generation_service.py
2. **Run Quality Gates**: lint.sh + test.sh
3. **Commit Phase 4**: Follow established commit message format
4. **Continue with Phase 5**: Router updates for partial state support

## Communication Style Notes

- User prefers direct, efficient communication
- Appreciates step-by-step progress tracking with TodoWrite tool
- Values thorough testing and quality assurance
- Expects complete, runnable code examples
- Prefers seeing actual implementation over theoretical discussion

## Git Branch & History

**Current Branch**: `99-feature-partial-failure-saving-question`
**Recent Commits**:
- `0de3540`: Phase 3 - Batch workflow 100% success requirement
- `e963215`: Phase 2 - Orchestrator batch-level tracking
- `213fe97`: Phase 1 - Schema updates with new status

**Main Branch**: `main` (for eventual PR creation)

## Documentation Created

**Comprehensive Guide**: `/docs/partial-failure-saving-implementation-guide.md`
- Complete implementation details with code examples
- Testing strategies and deployment instructions
- Monitoring and maintenance guidance
- 1700+ lines of detailed technical documentation
