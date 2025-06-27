# Feature Request: Implement Canvas Quiz Export Functionality

## Feature Description

Implement the complete Canvas quiz export functionality in the Rag@UiT backend to enable users to export their approved AI-generated questions directly to Canvas as new quizzes. This includes creating the quiz in Canvas and adding all approved questions as quiz items using the Canvas New Quizzes API.

## Background

The Rag@UiT application generates AI-powered multiple-choice questions from Canvas course content. Users can review and approve these questions, but currently there is no implementation to export the approved questions back to Canvas as a complete quiz. The backend needs to integrate with Canvas New Quizzes API to create quizzes and populate them with the approved questions.

### Current State

The backend currently supports:
- ✅ Quiz creation and management in the database
- ✅ Question generation from course content
- ✅ Question review and approval workflow
- ✅ Canvas OAuth authentication and token management

### Missing Implementation

The backend lacks:
- ❌ Canvas quiz creation API integration
- ❌ Canvas quiz item creation API integration
- ❌ Complete quiz export workflow
- ❌ Error handling for Canvas API failures
- ❌ Export status tracking and feedback

## Why?

### Core Application Feature
- **Primary Use Case**: The main value proposition of Rag@UiT is generating questions AND exporting them to Canvas
- **User Workflow Completion**: Users expect to go from content → questions → Canvas quiz in one flow
- **Competitive Advantage**: Seamless Canvas integration differentiates from manual quiz creation

### User Experience
- **Efficiency**: Eliminates manual copy-paste of questions into Canvas
- **Error Reduction**: Automated export reduces human errors in quiz creation
- **Time Savings**: Bulk question export saves significant instructor time

### Canvas Integration Value
- **Native Integration**: Questions appear as proper Canvas quizzes with all settings
- **Canvas Features**: Users can leverage Canvas quiz features (timer, shuffle, etc.)
- **Gradebook Integration**: Exported quizzes integrate with Canvas gradebook

## Constraints and Assumptions

### Technical Constraints
- **Canvas API Limits**: Respect Canvas API rate limits and quotas
- **Canvas Token Management**: Use existing OAuth token refresh mechanism
- **Async Operations**: Quiz export may take time, requires proper async handling
- **Error Recovery**: Handle Canvas API failures gracefully

### Business Constraints
- **Canvas Permissions**: Users must have instructor/teacher role in target course
- **Course Access**: Only export to courses user has access to
- **Question Approval**: Only export approved questions
- **One-Time Export**: Once exported, quiz management happens in Canvas

### Assumptions
- **Question Format**: Focus on multiple-choice questions initially
- **Canvas Version**: Target Canvas New Quizzes API (not legacy quizzes)
- **Single Course Export**: Export quiz to the same course where content was sourced
- **Canvas Account**: All users have Canvas accounts with appropriate permissions

## Design Changes

### 1. New Backend Service

**File**: `backend/app/services/canvas_quiz_export.service.py`

**Core Functions:**
- `export_quiz_to_canvas(quiz_id: int, user_token: str) -> dict`
- `create_canvas_quiz(quiz_data: dict, course_id: int, token: str) -> dict`
- `add_questions_to_canvas_quiz(quiz_id: str, questions: list, token: str) -> list`

### 2. New API Endpoint

**File**: `backend/app/api/routes/quiz.py`

**New Endpoint:**
```python
@router.post("/quiz/{quiz_id}/export")
async def export_quiz_to_canvas(
    quiz_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
) -> dict
```

### 3. Database Schema Updates

**Quiz Model Updates** (`backend/app/models.py`):
- Add `canvas_quiz_id` field to track exported quiz
- Add `export_status` field (pending, exporting, completed, failed)
- Add `exported_at` timestamp

**Question Model Updates**:
- Add `canvas_item_id` field to track exported questions

### 4. Canvas API Integration

**Quiz Creation Request:**
```python
POST /api/quiz/v1/courses/{course_id}/quizzes
{
    "title": quiz.title,
    "points_possible": total_points,
    "quiz_settings": {
        "shuffle_questions": True,
        "shuffle_answers": True,
        "time_limit": 60,
        "multiple_attempts": False,
        "scoring_policy": "keep_highest"
    }
}
```

**Quiz Item Creation Request:**
```python
POST /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items
{
    "entry_type": "Item",
    "interaction_type_slug": "choice",
    "item_body": f"<p>{question.question_text}</p>",
    "points_possible": 10,
    "interaction_data": {
        "choices": [
            {
                "id": f"choice_{i}",
                "position": i + 1,
                "item_body": f"<p>{choice.text}</p>"
            }
            for i, choice in enumerate(question.choices)
        ],
        "scoring_data": {
            "value": f"choice_{question.correct_answer_index}"
        }
    }
}
```

## Acceptance Criteria

### 1. Quiz Export API Endpoint

**Endpoint**: `POST /api/v1/quiz/{quiz_id}/export`

**Requirements:**
- ✅ Validate user has access to quiz
- ✅ Validate quiz has approved questions
- ✅ Get user's Canvas token from database
- ✅ Create quiz in Canvas via API
- ✅ Add all approved questions as quiz items
- ✅ Update database with Canvas quiz ID and export status
- ✅ Return export status and Canvas quiz information

**Request:**
- Path parameter: `quiz_id` (integer)
- Authentication: JWT token

**Response:**
```json
{
    "success": true,
    "canvas_quiz_id": "assign_1234",
    "canvas_quiz_url": "https://canvas.uit.no/courses/37823/quizzes/1234",
    "exported_questions": 10,
    "message": "Quiz successfully exported to Canvas"
}
```

### 2. Canvas Quiz Creation

**Requirements:**
- ✅ Use Canvas New Quizzes API
- ✅ Set quiz title from database quiz
- ✅ Calculate total points from approved questions
- ✅ Apply default quiz settings (shuffle, time limit, etc.)
- ✅ Handle Canvas API errors gracefully
- ✅ Return Canvas quiz object with assignment_id

### 3. Canvas Quiz Items Creation

**Requirements:**
- ✅ Convert database questions to Canvas quiz item format
- ✅ Support multiple-choice questions with 2-4 options
- ✅ Set correct answer based on database correct_answer_index
- ✅ Set points per question (default: 10 points)
- ✅ Handle individual item creation failures
- ✅ Track Canvas item IDs in database

### 4. Error Handling

**Canvas API Errors:**
- **401 Unauthorized**: Token expired or invalid - trigger token refresh
- **403 Forbidden**: User lacks Canvas permissions - return clear error
- **404 Not Found**: Course not found - validate course access
- **429 Rate Limited**: Implement retry with backoff
- **500 Server Error**: Log error and return user-friendly message

**Application Errors:**
- **Quiz Not Found**: Return 404 with clear message
- **No Approved Questions**: Return 400 with guidance
- **Already Exported**: Return 409 with Canvas quiz link
- **Token Missing**: Return 401 with re-auth instructions

### 5. Database Updates

**Quiz Table:**
- Add `canvas_quiz_id` (string, nullable)
- Add `export_status` (enum: pending, exporting, completed, failed)
- Add `exported_at` (timestamp, nullable)

**Question Table:**
- Add `canvas_item_id` (string, nullable)

### 6. Frontend Integration

**Quiz Detail Page:**
- Show "Export to Canvas" button when quiz has approved questions
- Disable button during export process
- Show export status and Canvas quiz link after successful export
- Display error messages for failed exports

## Implementation Steps

### Phase 1: Database Schema (1 day)
1. Add migration for new quiz and question fields
2. Update SQLModel classes
3. Test migration on development database

### Phase 2: Canvas API Service (2-3 days)
1. Create `canvas_quiz_export.service.py`
2. Implement Canvas quiz creation function
3. Implement Canvas quiz items creation function
4. Add comprehensive error handling and logging

### Phase 3: Export API Endpoint (2 days)
1. Add export endpoint to quiz routes
2. Implement quiz validation and permission checks
3. Integrate with Canvas API service
4. Add database updates for export tracking

### Phase 4: Frontend Integration (2 days)
1. Add export button to quiz detail page
2. Implement export status display
3. Add error handling and user feedback
4. Test complete user workflow

### Phase 5: Testing & Documentation (2-3 days)
1. Write comprehensive unit tests
2. Test with mock Canvas server
3. Integration testing with real Canvas instance
4. Update API documentation

## Relevant Resources

### Canvas API Documentation
- [Canvas New Quizzes API](https://canvas.instructure.com/doc/api/new_quizzes.html)
- [Canvas New Quiz Items API](https://canvas.instructure.com/doc/api/new_quiz_items.html)
- [Canvas API Rate Limiting](https://canvas.instructure.com/doc/api/file.throttling.html)

### Project Files
- Canvas Quiz Implementation Guide: `docs/canvas-quiz-endpoints-implementation.md`
- Quiz Models: `backend/app/models.py`
- Quiz Routes: `backend/app/api/routes/quiz.py`
- Canvas Auth: `backend/app/api/routes/canvas.py`

### Development Tools
- Mock Canvas Server: `mocks/oauth_mock_server.py`
- Canvas API Testing: Can test against mock server during development

## Success Metrics

- **Functional**: Users can successfully export approved questions to Canvas
- **Reliability**: 95%+ success rate for quiz exports
- **Performance**: Quiz export completes within 30 seconds for 50 questions
- **User Experience**: Clear feedback throughout export process
- **Integration**: Exported quizzes work properly in Canvas with all features

## Priority

**HIGH** - This is a core feature that completes the primary user workflow of the application. Without quiz export, users cannot realize the full value of the AI-generated questions.
