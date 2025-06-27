# Canvas Quiz Endpoints Implementation Guide

## Overview

This document describes the implementation of Canvas New Quizzes API endpoints in the mock server for the Rag@UiT application. The mock server simulates Canvas LMS behavior to enable local development and testing of quiz creation functionality.

## Table of Contents

1. [Canvas New Quizzes API Overview](#canvas-new-quizzes-api-overview)
2. [Mock Server Implementation](#mock-server-implementation)
3. [Backend API Flow](#backend-api-flow)
4. [Data Structures](#data-structures)
5. [Implementation Examples](#implementation-examples)
6. [Testing Considerations](#testing-considerations)

## Canvas New Quizzes API Overview

Canvas provides two main APIs for quiz management:

1. **New Quiz API** - Manages quiz configuration, settings, and metadata
2. **New Quiz Items API** - Manages individual questions within a quiz

### Key Characteristics

- Quizzes are associated with course assignments
- Each quiz has a unique `assignment_id`
- Quiz items (questions) belong to a specific quiz
- Authentication uses Bearer tokens
- All endpoints follow RESTful conventions

## Mock Server Implementation

### Required Endpoints

#### 1. Quiz Management Endpoints

**Create Quiz**
```
POST /api/quiz/v1/courses/{course_id}/quizzes
```
- Creates a new quiz in the specified course
- Returns the created quiz object with generated `assignment_id`
- Status: 201 Created

**List Quizzes**
```
GET /api/quiz/v1/courses/{course_id}/quizzes
```
- Returns array of all quizzes for the course
- Status: 200 OK

**Get Single Quiz**
```
GET /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}
```
- Returns detailed information about a specific quiz
- Status: 200 OK or 404 Not Found

**Update Quiz**
```
PATCH /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}
```
- Updates quiz properties
- Returns updated quiz object
- Status: 200 OK

**Delete Quiz**
```
DELETE /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}
```
- Removes quiz and all associated items
- Status: 204 No Content

#### 2. Quiz Items Management Endpoints

**Create Quiz Item**
```
POST /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items
```
- Adds a new question to the quiz
- Returns created item with generated `item_id`
- Status: 201 Created

**List Quiz Items**
```
GET /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items
```
- Returns array of all items in the quiz
- Status: 200 OK

**Get Single Item**
```
GET /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}
```
- Returns specific quiz item details
- Status: 200 OK or 404 Not Found

**Update Item**
```
PATCH /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}
```
- Updates quiz item properties
- Returns updated item
- Status: 200 OK

**Delete Item**
```
DELETE /api/quiz/v1/courses/{course_id}/quizzes/{assignment_id}/items/{item_id}
```
- Removes item from quiz
- Status: 204 No Content

### Implementation in oauth_mock_server.py

Add the following data structures after the existing mock data:

```python
# Mock quiz storage
mock_quizzes = {}  # Key: assignment_id, Value: quiz object
mock_quiz_items = {}  # Key: assignment_id, Value: list of items

# Counter for generating IDs
quiz_id_counter = 1000
item_id_counter = 5000
```

## Backend API Flow

### Complete Quiz Creation Flow

The backend application follows this sequence when creating a quiz with questions:

#### Step 1: Authenticate User
```
POST /api/v1/auth/canvas/callback
Body: { "code": "auth_code_from_canvas" }
Response: { "access_token": "...", "user": {...} }
```

#### Step 2: Create Quiz in Backend
```
POST /api/v1/quiz
Body: {
  "title": "AI Methods Quiz",
  "course_id": 37823,
  "module_ids": [173577],
  "llm_settings": {
    "model": "gpt-4",
    "temperature": 0.7,
    "num_questions": 10
  }
}
Response: { "id": 123, "status": "generating", ... }
```

#### Step 3: Backend Generates Questions
The backend:
1. Fetches module content from Canvas
2. Processes content (PDFs, pages)
3. Sends to LLM for question generation
4. Stores generated questions

#### Step 4: User Reviews Questions
```
GET /api/v1/quiz/{quiz_id}/questions
Response: [
  {
    "id": 456,
    "question_text": "What is reinforcement learning?",
    "choices": [...],
    "status": "pending"
  }
]
```

#### Step 5: User Approves Questions
```
PATCH /api/v1/questions/{question_id}
Body: { "status": "approved" }
```

#### Step 6: Export to Canvas
```
POST /api/v1/quiz/{quiz_id}/export
```

This triggers the following Canvas API calls:

##### 6.1: Create Quiz in Canvas
```
POST /api/quiz/v1/courses/37823/quizzes
Headers: { "Authorization": "Bearer {canvas_token}" }
Body: {
  "title": "AI Methods Quiz",
  "points_possible": 100,
  "quiz_settings": {
    "calculator_type": "none",
    "filter_ip_addresses": false,
    "shuffle_questions": true,
    "shuffle_answers": true,
    "one_question_at_a_time": false,
    "cant_go_back": false,
    "time_limit": 60,
    "multiple_attempts": false,
    "scoring_policy": "keep_highest"
  }
}
Response: {
  "id": "quiz_123",
  "assignment_id": "assign_456",
  "title": "AI Methods Quiz",
  ...
}
```

##### 6.2: Add Questions to Quiz
For each approved question:
```
POST /api/quiz/v1/courses/37823/quizzes/assign_456/items
Headers: { "Authorization": "Bearer {canvas_token}" }
Body: {
  "entry_type": "Item",
  "interaction_type_slug": "choice",
  "interaction_data": {
    "choices": [
      {
        "id": "choice_1",
        "position": 1,
        "item_body": "<p>Learning from rewards and penalties</p>"
      },
      {
        "id": "choice_2",
        "position": 2,
        "item_body": "<p>Supervised learning with labels</p>"
      },
      {
        "id": "choice_3",
        "position": 3,
        "item_body": "<p>Clustering without labels</p>"
      },
      {
        "id": "choice_4",
        "position": 4,
        "item_body": "<p>Rule-based decision making</p>"
      }
    ],
    "scoring_data": {
      "value": "choice_1"
    }
  },
  "item_body": "<p>What is reinforcement learning?</p>",
  "points_possible": 10
}
Response: {
  "id": "item_789",
  "entry_type": "Item",
  ...
}
```

## Data Structures

### Quiz Object

```python
{
    "id": "quiz_123",
    "assignment_id": "assign_456",  # Unique identifier
    "course_id": 37823,
    "title": "AI Methods Quiz",
    "points_possible": 100,
    "due_at": "2024-12-31T23:59:59Z",
    "lock_at": null,
    "unlock_at": null,
    "published": false,
    "quiz_type": "assignment",
    "allowed_attempts": 1,
    "scoring_policy": "keep_highest",
    "quiz_settings": {
        "calculator_type": "none",
        "filter_ip_addresses": false,
        "shuffle_questions": true,
        "shuffle_answers": true,
        "require_lockdown_browser": false,
        "require_lockdown_browser_for_results": false,
        "one_question_at_a_time": false,
        "cant_go_back": false,
        "show_correct_answers": true,
        "show_correct_answers_at": null,
        "hide_correct_answers_at": null,
        "time_limit": 60,
        "multiple_attempts": false,
        "scoring_policy": "keep_highest",
        "result_view_settings": {
            "result_view_restricted": true,
            "display_points_awarded": true,
            "display_points_possible": true,
            "display_items": true,
            "display_item_response": true,
            "display_item_response_correctness": true,
            "display_item_correct_answer": true,
            "display_item_feedback": true
        }
    },
    "created_at": "2024-11-01T10:00:00Z",
    "updated_at": "2024-11-01T10:00:00Z"
}
```

### Quiz Item Object (Multiple Choice)

```python
{
    "id": "item_789",
    "entry_type": "Item",
    "entry_id": "item_789",
    "position": 1,
    "item_type": "Question",
    "interaction_type_slug": "choice",  # Multiple choice
    "item_body": "<p>What is reinforcement learning?</p>",
    "calculator_type": null,
    "properties": {
        "shuffle_answers": true
    },
    "interaction_data": {
        "choices": [
            {
                "id": "choice_1",
                "position": 1,
                "item_body": "<p>Learning from rewards and penalties</p>"
            },
            {
                "id": "choice_2",
                "position": 2,
                "item_body": "<p>Supervised learning with labels</p>"
            },
            {
                "id": "choice_3",
                "position": 3,
                "item_body": "<p>Clustering without labels</p>"
            },
            {
                "id": "choice_4",
                "position": 4,
                "item_body": "<p>Rule-based decision making</p>"
            }
        ],
        "scoring_algorithm": "exact_match",
        "scoring_data": {
            "value": "choice_1"  # Correct answer
        }
    },
    "points_possible": 10,
    "neutral_comments": "<p>Reinforcement learning is a type of machine learning where agents learn through interaction with an environment.</p>",
    "created_at": "2024-11-01T10:05:00Z",
    "updated_at": "2024-11-01T10:05:00Z"
}
```

## Implementation Examples

### Mock Server Endpoint Implementation

Here's an example implementation for the create quiz endpoint:

```python
@app.post("/api/quiz/v1/courses/{course_id}/quizzes")
async def create_quiz(
    course_id: int,
    authorization: str = Header(None),
    quiz_data: dict = Body(...)
):
    """Create a new quiz in Canvas"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    validate_token(authorization)

    # Validate course access
    if course_id != 37823:
        raise HTTPException(status_code=403, detail="Unauthorized access to course")

    # Generate IDs
    global quiz_id_counter
    quiz_id = f"quiz_{quiz_id_counter}"
    assignment_id = f"assign_{quiz_id_counter}"
    quiz_id_counter += 1

    # Create quiz object
    new_quiz = {
        "id": quiz_id,
        "assignment_id": assignment_id,
        "course_id": course_id,
        "title": quiz_data.get("title", "Untitled Quiz"),
        "points_possible": quiz_data.get("points_possible", 0),
        "due_at": quiz_data.get("due_at"),
        "lock_at": quiz_data.get("lock_at"),
        "unlock_at": quiz_data.get("unlock_at"),
        "published": False,
        "quiz_type": "assignment",
        "quiz_settings": quiz_data.get("quiz_settings", {
            "shuffle_questions": True,
            "shuffle_answers": True,
            "time_limit": None,
            "multiple_attempts": False,
            "scoring_policy": "keep_highest"
        }),
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z"
    }

    # Store quiz
    mock_quizzes[assignment_id] = new_quiz
    mock_quiz_items[assignment_id] = []

    return JSONResponse(content=new_quiz, status_code=201)
```

### Backend Service Call Example

```python
async def export_quiz_to_canvas(quiz_id: int, canvas_token: str):
    """Export approved quiz questions to Canvas"""

    # 1. Get quiz details from database
    quiz = await get_quiz(quiz_id)
    approved_questions = await get_approved_questions(quiz_id)

    # 2. Create quiz in Canvas
    canvas_quiz_data = {
        "title": quiz.title,
        "points_possible": len(approved_questions) * 10,
        "quiz_settings": {
            "shuffle_questions": True,
            "shuffle_answers": True,
            "time_limit": 60,
            "multiple_attempts": False,
            "scoring_policy": "keep_highest"
        }
    }

    async with httpx.AsyncClient() as client:
        # Create quiz
        response = await client.post(
            f"{CANVAS_BASE_URL}/api/quiz/v1/courses/{quiz.course_id}/quizzes",
            headers={"Authorization": f"Bearer {canvas_token}"},
            json=canvas_quiz_data
        )
        canvas_quiz = response.json()
        assignment_id = canvas_quiz["assignment_id"]

        # 3. Add questions to quiz
        for question in approved_questions:
            item_data = {
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

            await client.post(
                f"{CANVAS_BASE_URL}/api/quiz/v1/courses/{quiz.course_id}/quizzes/{assignment_id}/items",
                headers={"Authorization": f"Bearer {canvas_token}"},
                json=item_data
            )

    return canvas_quiz
```

## Testing Considerations

### Manual Testing Steps

1. **Authentication Flow**
   - Start mock server on port 8001
   - Test OAuth login flow
   - Verify token generation

2. **Quiz Creation**
   - Create quiz via POST request
   - Verify quiz is stored in mock data
   - Check response format matches Canvas

3. **Quiz Items**
   - Add multiple choice questions
   - Verify item structure
   - Test update and delete operations

4. **Integration Testing**
   - Test complete flow from backend
   - Verify all API calls succeed
   - Check data consistency

### Automated Testing

```python
def test_create_quiz():
    """Test quiz creation in mock server"""
    # Setup
    token = get_test_token()

    # Create quiz
    response = client.post(
        "/api/quiz/v1/courses/37823/quizzes",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test Quiz",
            "points_possible": 100,
            "quiz_settings": {
                "time_limit": 60
            }
        }
    )

    assert response.status_code == 201
    quiz = response.json()
    assert quiz["title"] == "Test Quiz"
    assert "assignment_id" in quiz

    # Verify quiz can be retrieved
    get_response = client.get(
        f"/api/quiz/v1/courses/37823/quizzes/{quiz['assignment_id']}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 200
```

## Error Handling

All endpoints should handle common errors:

- **401 Unauthorized**: Missing or invalid token
- **403 Forbidden**: User lacks access to resource
- **404 Not Found**: Quiz or item doesn't exist
- **400 Bad Request**: Invalid request data
- **422 Unprocessable Entity**: Validation errors

Example error response:
```json
{
    "errors": [
        {
            "message": "Invalid quiz settings",
            "error_code": "invalid_parameters"
        }
    ]
}
```

## Security Considerations

1. **Authentication**: All endpoints require valid Bearer token
2. **Authorization**: Verify user has access to course
3. **Input Validation**: Validate all input data
4. **Rate Limiting**: Consider adding rate limits for production
5. **Data Sanitization**: Sanitize HTML content in quiz items

## Future Enhancements

1. **Additional Question Types**
   - True/False
   - Essay
   - Fill in the blank
   - Matching

2. **Advanced Features**
   - Question banks
   - Random question selection
   - Conditional release
   - Quiz statistics

3. **Bulk Operations**
   - Import/export quiz data
   - Batch question creation
   - Copy quizzes between courses

## References

- [Canvas New Quizzes API Documentation](https://canvas.instructure.com/doc/api/new_quizzes.html)
- [Canvas New Quiz Items API Documentation](https://canvas.instructure.com/doc/api/new_quiz_items.html)
- [Canvas OAuth2 Documentation](https://canvas.instructure.com/doc/api/file.oauth.html)
