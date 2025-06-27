# Canvas Classic vs New Quizzes: API Analysis and Implementation Guide

## Executive Summary

Canvas LMS operates two distinct quiz systems: **Classic Quizzes** and **New Quizzes**. Each has separate API endpoints, different feature sets, and distinct integration patterns. This document analyzes both systems to inform implementation decisions for the Rag@UiT mock server.

## Key Findings

### 1. Two Separate Quiz Ecosystems

Canvas maintains two completely separate quiz systems:

- **Classic Quizzes**: The original quiz system using REST API endpoints under `/api/v1/courses/:course_id/quizzes`
- **New Quizzes**: The modern quiz system using REST API endpoints under `/api/quiz/v1/courses/:course_id/quizzes/:assignment_id`

### 2. Development Status

- **Classic Quizzes**: No longer receiving new functionality updates but still fully supported
- **New Quizzes**: Actively developed with new features being added regularly
- **Migration**: Classic → New is supported, but New → Classic is not possible

### 3. API Architecture Differences

The two systems have fundamentally different API designs:

#### Classic Quizzes API Structure
```
/api/v1/courses/:course_id/quizzes
├── GET    / (list quizzes)
├── POST   / (create quiz)
├── GET    /:id (get quiz)
├── PUT    /:id (update quiz)
└── DELETE /:id (delete quiz)

/api/v1/courses/:course_id/quizzes/:quiz_id/questions
├── GET    / (list questions)
├── POST   / (create question)
├── GET    /:id (get question)
├── PUT    /:id (update question)
└── DELETE /:id (delete question)
```

#### New Quizzes API Structure
```
/api/quiz/v1/courses/:course_id/quizzes
├── GET    / (list quizzes)
├── POST   / (create quiz)
├── GET    /:assignment_id (get quiz)
├── PATCH  /:assignment_id (update quiz)
└── DELETE /:assignment_id (delete quiz)

/api/quiz/v1/courses/:course_id/quizzes/:assignment_id/items
├── GET    / (list items)
├── POST   / (create item)
├── GET    /:item_id (get item)
├── PATCH  /:item_id (update item)
└── DELETE /:item_id (delete item)
```

## Detailed API Comparison

### Classic Quizzes API

#### Endpoints
- **Base URL**: `/api/v1/courses/:course_id/quizzes`
- **HTTP Methods**: GET, POST, PUT, DELETE
- **Identifier**: Uses `quiz_id` as primary identifier
- **Questions**: Separate `/questions` endpoint for quiz questions

#### Data Structure
```json
{
  "id": 12345,
  "title": "Sample Quiz",
  "description": "Quiz description",
  "quiz_type": "assignment",
  "assignment_id": 67890,
  "time_limit": 60,
  "shuffle_answers": true,
  "show_correct_answers": true,
  "scoring_policy": "keep_highest",
  "allowed_attempts": 1,
  "one_question_at_a_time": false,
  "cant_go_back": false,
  "access_code": null,
  "ip_filter": null,
  "due_at": "2024-12-31T23:59:59Z",
  "lock_at": null,
  "unlock_at": null,
  "published": false,
  "points_possible": 100
}
```

#### Question Structure
```json
{
  "id": 54321,
  "quiz_id": 12345,
  "question_name": "Question 1",
  "question_text": "What is reinforcement learning?",
  "question_type": "multiple_choice_question",
  "position": 1,
  "points_possible": 10,
  "answers": [
    {
      "id": 1,
      "text": "Learning from rewards and penalties",
      "weight": 100
    },
    {
      "id": 2,
      "text": "Supervised learning with labels",
      "weight": 0
    }
  ]
}
```

### New Quizzes API

#### Endpoints
- **Base URL**: `/api/quiz/v1/courses/:course_id/quizzes`
- **HTTP Methods**: GET, POST, PATCH, DELETE
- **Identifier**: Uses `assignment_id` as primary identifier
- **Items**: Separate `/items` endpoint for quiz items (questions)

#### Data Structure
```json
{
  "id": "quiz_12345",
  "assignment_id": "assign_67890",
  "course_id": 37823,
  "title": "Sample Quiz",
  "instructions": "Complete all questions",
  "points_possible": 100,
  "quiz_type": "assignment",
  "published": false,
  "due_at": "2024-12-31T23:59:59Z",
  "lock_at": null,
  "unlock_at": null,
  "quiz_settings": {
    "calculator_type": "none",
    "filter_ip_addresses": false,
    "shuffle_questions": true,
    "shuffle_answers": true,
    "one_question_at_a_time": false,
    "cant_go_back": false,
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
  }
}
```

#### Item Structure
```json
{
  "id": "item_54321",
  "entry_type": "Item",
  "position": 1,
  "item_type": "Question",
  "interaction_type_slug": "choice",
  "item_body": "<p>What is reinforcement learning?</p>",
  "points_possible": 10,
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
      }
    ],
    "scoring_data": {
      "value": "choice_1"
    }
  }
}
```

## Assignment Integration

### Classic Quizzes
- Creates an assignment automatically when quiz is published
- Assignment contains `quiz_id` field linking back to the quiz
- Assignment `submission_types` includes `"online_quiz"`
- Quiz ID and Assignment ID are separate entities

### New Quizzes
- Uses `assignment_id` as the primary identifier for the quiz
- Quiz and assignment are more tightly integrated
- Assignment creation is implicit in quiz creation
- `assignment_id` serves as the main reference point

## Feature Comparison

| Feature | Classic Quizzes | New Quizzes |
|---------|----------------|-------------|
| **Question Types** | Multiple choice, True/false, Fill-in-blank, Essay, Matching, Numerical, Formula, File upload | All classic types + Categorization, Ordering, Hot Spot, Stimulus |
| **Question Groups** | Supported | Not supported (use Stimulus instead) |
| **Item Banks** | Basic question banks | Advanced item banks with cross-course sharing |
| **Accessibility** | Basic | Enhanced with accessibility checker |
| **Anonymous Grading** | Not supported | Supported |
| **Global Accommodations** | Per-quiz settings | Global settings across all quizzes |
| **Rich Content Editor** | Basic | Enhanced with math editor, apps support |
| **Text Blocks** | Not supported | Supported for additional context |
| **API Complexity** | Simple REST | More complex REST with nested resources |
| **Development Status** | Maintenance only | Active development |

## Implementation Recommendations

### For Mock Server Implementation

#### Option 1: Classic Quizzes (Recommended for MVP)
**Pros:**
- Simpler API structure
- Well-documented and stable
- Easier to implement and test
- Sufficient for basic quiz functionality

**Cons:**
- Limited future development
- Fewer advanced features
- May need migration path later

**Implementation Priority:**
1. Quiz CRUD operations
2. Question CRUD operations
3. Basic quiz settings
4. Assignment integration

#### Option 2: New Quizzes (Recommended for Long-term)
**Pros:**
- Future-proof implementation
- Advanced features and question types
- Better integration with Canvas roadmap
- More flexible item system

**Cons:**
- More complex API structure
- Still in active development (potential changes)
- Requires more implementation effort
- Complex item interaction data

**Implementation Priority:**
1. Quiz CRUD operations
2. Item CRUD operations
3. Advanced quiz settings
4. Item bank integration

#### Option 3: Hybrid Approach (Recommended for Production)
**Implementation Strategy:**
1. **Phase 1**: Implement Classic Quizzes for immediate functionality
2. **Phase 2**: Add New Quizzes API endpoints
3. **Phase 3**: Provide migration utilities
4. **Phase 4**: Deprecate Classic implementation

## Backend Integration Patterns

### Classic Quizzes Flow
```
1. POST /api/v1/courses/37823/quizzes
   → Creates quiz, returns quiz_id

2. POST /api/v1/courses/37823/quizzes/{quiz_id}/questions
   → Add questions one by one

3. PUT /api/v1/courses/37823/quizzes/{quiz_id}
   → Publish quiz (creates assignment)
```

### New Quizzes Flow
```
1. POST /api/quiz/v1/courses/37823/quizzes
   → Creates quiz with assignment_id

2. POST /api/quiz/v1/courses/37823/quizzes/{assignment_id}/items
   → Add items (questions) one by one

3. PATCH /api/quiz/v1/courses/37823/quizzes/{assignment_id}
   → Publish quiz
```

## Security Considerations

Both systems require:
- **Authentication**: Bearer token in Authorization header
- **Authorization**: User must have appropriate permissions for the course
- **Input Validation**: All quiz and question data must be validated
- **HTML Sanitization**: Question content may contain HTML

### Classic Quizzes Permissions
- Teachers can create, edit, and delete quizzes
- Students can only view published quizzes and submit responses

### New Quizzes Permissions
- Teachers and TAs can create quizzes
- Course Designers cannot create New Quizzes (different from Classic)
- More granular permission controls available

## Testing Strategy

### Classic Quizzes Testing
```python
def test_classic_quiz_creation():
    # Create quiz
    quiz_response = client.post("/api/v1/courses/37823/quizzes", json={
        "quiz": {
            "title": "Test Quiz",
            "quiz_type": "assignment",
            "time_limit": 60
        }
    })

    quiz_id = quiz_response.json()["id"]

    # Add question
    question_response = client.post(f"/api/v1/courses/37823/quizzes/{quiz_id}/questions", json={
        "question": {
            "question_name": "Q1",
            "question_text": "Sample question?",
            "question_type": "multiple_choice_question",
            "answers": [
                {"text": "Answer A", "weight": 100},
                {"text": "Answer B", "weight": 0}
            ]
        }
    })
```

### New Quizzes Testing
```python
def test_new_quiz_creation():
    # Create quiz
    quiz_response = client.post("/api/quiz/v1/courses/37823/quizzes", json={
        "title": "Test Quiz",
        "quiz_settings": {
            "time_limit": 60,
            "shuffle_answers": True
        }
    })

    assignment_id = quiz_response.json()["assignment_id"]

    # Add item
    item_response = client.post(f"/api/quiz/v1/courses/37823/quizzes/{assignment_id}/items", json={
        "entry_type": "Item",
        "interaction_type_slug": "choice",
        "item_body": "<p>Sample question?</p>",
        "interaction_data": {
            "choices": [
                {"id": "choice_1", "item_body": "<p>Answer A</p>"},
                {"id": "choice_2", "item_body": "<p>Answer B</p>"}
            ],
            "scoring_data": {"value": "choice_1"}
        }
    })
```

## Migration Considerations

### From Classic to New Quizzes
- Canvas provides built-in migration tools
- Most features translate directly
- Some advanced Classic features may not have New Quiz equivalents
- Question groups become Stimulus items

### Implementation Migration Strategy
1. **Dual Support**: Run both APIs simultaneously
2. **Data Mapping**: Create translation layer between formats
3. **Feature Parity**: Ensure core functionality works in both
4. **Gradual Transition**: Move users from Classic to New over time

## Conclusion

Both Classic and New Quizzes serve different needs:

- **Classic Quizzes** are ideal for immediate implementation needs with simpler, well-established APIs
- **New Quizzes** are better for long-term strategy with advanced features and active development

For the Rag@UiT mock server, I recommend:

1. **Start with Classic Quizzes** for rapid prototyping and immediate functionality
2. **Plan for New Quizzes** implementation as a future enhancement
3. **Design the backend** to abstract quiz operations so switching between systems is possible
4. **Consider the end-user needs** - if advanced question types are required, prioritize New Quizzes

The choice ultimately depends on the specific requirements of the Rag@UiT application and the timeline for implementation.
