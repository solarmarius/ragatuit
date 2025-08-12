# Question Approval Rollback on Canvas Export Error - Implementation Guide

## Overview

This document outlines the implementation of automatic question approval rollback when Canvas export fails with specific error conditions. This feature ensures data consistency between question approval states and actual Canvas export status.

## Problem Statement

Previously, when questions failed to export to Canvas during the quiz export process, the questions remained in an "approved" state despite not being successfully exported. This created inconsistency and prevented users from identifying and correcting problematic questions.

From production logs, we observed scenarios where 19 out of 80 questions failed with 502 Bad Gateway errors, indicating content-related issues that required user attention:

```
Export failed: 19 out of 80 questions failed to export. Quiz will be removed from Canvas.
canvas_quiz_item_creation_failed: status_code=502, response_text={"message":"Bad Gateway"}
```

## Solution Architecture

### Core Components

1. **Single Question Unapproval Function**
2. **502-Specific Error Handling in Canvas Export**
3. **Database Session Integration in Export Workflow**
4. **Comprehensive Test Coverage**

### Key Design Decisions

- **502-Only Rollback**: Only 502 Bad Gateway errors trigger unapproval (content issues)
- **Immediate Rollback**: Questions are unapproved instantly when the error occurs
- **Selective Processing**: Only failed questions are affected, successful ones remain approved
- **No Schema Changes**: Utilizes existing `is_approved` and `approved_at` fields
- **Internal-Only**: No new API endpoints, purely internal functionality

## Implementation Details

### 1. Question Service Enhancement

**File:** `backend/src/question/service.py`

Added `unapprove_question()` function:

```python
async def unapprove_question(session: AsyncSession, question_id: UUID) -> bool:
    """
    Revert approval status for a single question by its ID.

    This function is used when a question fails during Canvas export with a 502 error,
    indicating an issue with the question content that requires user review.
    """
```

**Features:**
- Reverts `is_approved` to `False` and `approved_at` to `None`
- Returns `True` if successful, `False` if question not found or already unapproved
- Comprehensive logging for audit trail
- Handles edge cases (non-existent questions, soft-deleted questions)

### 2. Canvas Export Error Handling

**File:** `backend/src/canvas/service.py`

Enhanced `create_canvas_quiz_items()` function:

```python
# Unapprove question only on 502 errors (question content issues)
if e.response.status_code == 502:
    from src.question.service import unapprove_question
    try:
        unapproval_success = await unapprove_question(session, question["id"])
        if unapproval_success:
            logger.info("question_unapproved_due_to_502_error", ...)
    except Exception as unapproval_error:
        logger.error("question_unapproval_exception_502_error", ...)
```

**Key Features:**
- **Selective Error Handling**: Only 502 errors trigger unapproval
- **Graceful Degradation**: Export continues even if unapproval fails
- **Detailed Logging**: Comprehensive logging for troubleshooting
- **Session Integration**: Database session passed for immediate rollback

### 3. Export Orchestration Updates

**File:** `backend/src/quiz/orchestrator/export.py`

Modified export workflow to provide database session context:

```python
# Create session for question unapproval during Canvas operations
from src.database import get_async_session

try:
    async with get_async_session() as session:
        workflow_result = await _execute_export_workflow(
            quiz_id, canvas_token, quiz_creator, question_exporter, export_data, session
        )
```

**Changes:**
- Added session parameter to `_execute_export_workflow()`
- Updated `QuestionExporterFunc` type signature
- Ensured session availability for question operations

### 4. Canvas Flow Integration

**File:** `backend/src/canvas/flows.py`

Updated `export_questions_batch_flow()` signature:

```python
async def export_questions_batch_flow(
    canvas_token: str,
    course_id: int,
    quiz_id: str,
    questions: list[dict[str, Any]],
    session: AsyncSession  # NEW PARAMETER
) -> list[dict[str, Any]]:
```

## Error Handling Strategy

### 502 Bad Gateway Errors
- **Trigger**: Content-related issues with question data
- **Action**: Immediate question unapproval
- **Logging**: Detailed error and rollback logging
- **User Impact**: Question requires re-approval after fixing content issues

### Other HTTP Errors (429, 401, etc.)
- **Trigger**: Rate limiting, authentication, temporary server issues
- **Action**: No question unapproval
- **Logging**: Standard error logging
- **User Impact**: Questions remain approved for retry

### General Exceptions
- **Trigger**: Network timeouts, connection issues
- **Action**: No question unapproval
- **Logging**: Exception details logged
- **User Impact**: Questions remain approved for retry

## Testing Strategy

### Unit Tests (`tests/question/test_question_service.py`)

1. **test_unapprove_approved_question_success**: Basic unapproval functionality
2. **test_unapprove_already_unapproved_question**: Idempotent behavior
3. **test_unapprove_nonexistent_question**: Error handling
4. **test_unapprove_soft_deleted_question**: Edge case handling
5. **test_unapprove_question_updates_timestamp**: Audit trail verification

### Integration Tests (`tests/canvas/test_canvas_service.py`)

1. **test_create_canvas_quiz_items_502_error_triggers_unapproval**: 502-specific rollback
2. **test_create_canvas_quiz_items_non_502_error_no_unapproval**: Selective behavior
3. **test_create_canvas_quiz_items_general_exception_no_unapproval**: Exception handling
4. **test_create_canvas_quiz_items_502_unapproval_db_error_graceful**: Fault tolerance

## Logging and Observability

### New Log Events

- `question_unapproval_started`: Debug-level start of unapproval process
- `question_unapproved_successfully`: Info-level successful unapproval
- `question_not_found_for_unapproval`: Warning-level missing question
- `question_already_unapproved`: Debug-level idempotent operation
- `question_unapproved_due_to_502_error`: Info-level 502-triggered rollback
- `question_unapproval_failed_502_error`: Warning-level rollback failure
- `question_unapproval_exception_502_error`: Error-level rollback exception

### Log Structure

All logs follow structured logging format with:
- `question_id`: UUID of affected question
- `canvas_quiz_id`: Canvas quiz identifier
- `position`: Question position in export sequence
- `error`: Error details where applicable

## User Workflow Impact

### Before Implementation
1. Quiz export fails with 502 errors
2. Questions remain approved despite export failure
3. Users cannot identify problematic questions
4. Re-export attempts continue to fail with same questions

### After Implementation
1. Quiz export fails with 502 errors
2. Failed questions are automatically unapproved
3. Users can identify unapproved questions for review
4. Users must fix and re-approve questions before retry
5. Only corrected questions are included in subsequent exports

## Performance Considerations

- **Database Operations**: Single UPDATE query per failed question
- **Memory Impact**: Minimal - no additional data structures
- **Network Impact**: None - purely internal database operations
- **Export Time**: Negligible overhead - rollback occurs during error handling

## Backward Compatibility

- **API Compatibility**: No changes to public APIs
- **Database Schema**: No schema modifications required
- **Frontend Impact**: No frontend changes needed
- **Deployment**: Can be deployed without migration or configuration changes

## Future Enhancements

### Potential Improvements

1. **Enhanced Error Categorization**:
   - Specific rollback rules for different 502 error types
   - Question-type-specific error handling

2. **Batch Rollback Optimization**:
   - Single database transaction for multiple failed questions
   - Reduced database round trips

3. **User Notification**:
   - Frontend notifications about automatic rollbacks
   - Detailed error messages for question fixes

4. **Analytics Integration**:
   - Metrics on question failure rates
   - Content quality insights

### Configuration Options

Future versions could include:
- Configurable error codes that trigger rollback
- Optional rollback behavior (enable/disable)
- Rollback notification settings

## Monitoring and Alerts

### Key Metrics to Monitor

- **Question Rollback Rate**: Frequency of 502-triggered rollbacks
- **Export Success Rate**: Overall export success after implementation
- **Question Re-approval Rate**: User response to rollbacks
- **Error Distribution**: 502 vs other error types

### Recommended Alerts

- High rollback rates indicating systematic content issues
- Rollback failures indicating database problems
- Unusual 502 error patterns indicating Canvas API issues

## Conclusion

This implementation provides a robust, targeted solution for maintaining data consistency between question approval states and Canvas export status. The selective approach ensures that only questions with content issues are affected, while maintaining system stability and providing clear feedback to users about problematic content.

The feature is designed to be:
- **Reliable**: Comprehensive error handling and fault tolerance
- **Selective**: Only affects questions with specific content issues
- **Transparent**: Detailed logging for troubleshooting and audit
- **Maintainable**: Clean integration with existing architecture
- **Testable**: Full test coverage for all scenarios

---

**Implementation Date**: August 2025
**Status**: Complete
**Branch**: 149-feature-question-approve-rollback-on-export-error
