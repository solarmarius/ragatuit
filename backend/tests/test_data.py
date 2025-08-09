"""Centralized test data constants and configurations.

This module contains standard test data used across multiple test files
to eliminate hardcoded values and ensure consistency.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

# User Test Data
DEFAULT_USER_DATA = {
    "canvas_id": 12345,
    "name": "Test User",
    "access_token": "test_access_token",
    "refresh_token": "test_refresh_token",
    "token_type": "Bearer",
    "onboarding_completed": False,
}

ADMIN_USER_DATA = {
    "canvas_id": 1,
    "name": "Admin User",
    "access_token": "admin_access_token",
    "refresh_token": "admin_refresh_token",
    "token_type": "Bearer",
    "onboarding_completed": True,
}

EXPIRED_USER_DATA = {
    "canvas_id": 99999,
    "name": "Expired User",
    "access_token": "expired_access_token",
    "refresh_token": "expired_refresh_token",
    "token_type": "Bearer",
    "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
    "onboarding_completed": False,
}

# Canvas Course Test Data
DEFAULT_CANVAS_COURSE = {
    "id": 123,
    "name": "Introduction to Computer Science",
    "course_code": "CS101",
    "enrollment_term_id": 1,
    "workflow_state": "available",
    "start_at": "2024-01-15T00:00:00Z",
    "end_at": "2024-05-15T00:00:00Z",
}

SECONDARY_CANVAS_COURSE = {
    "id": 456,
    "name": "Advanced Programming",
    "course_code": "CS201",
    "enrollment_term_id": 1,
    "workflow_state": "available",
}

# Canvas Module Test Data
DEFAULT_CANVAS_MODULES = [
    {
        "id": 456,
        "name": "Introduction to Programming",
        "position": 1,
        "workflow_state": "active",
        "items_count": 8,
    },
    {
        "id": 457,
        "name": "Data Structures and Algorithms",
        "position": 2,
        "workflow_state": "active",
        "items_count": 12,
    },
]

SINGLE_CANVAS_MODULE = {
    "id": 789,
    "name": "Test Module",
    "position": 1,
    "workflow_state": "active",
    "items_count": 5,
}

# Canvas Module Items Test Data
DEFAULT_MODULE_ITEMS = [
    {"id": 123, "title": "Test Item 1", "type": "Page", "url": "test-page-1"},
    {"id": 124, "title": "Test Item 2", "type": "File", "url": "test-file-1"},
    {"id": 125, "title": "Test Item 3", "type": "Page", "url": "test-page-2"},
]

# Canvas Page Content Test Data
DEFAULT_PAGE_CONTENT = {
    "title": "Test Page",
    "body": "<p>This is comprehensive test page content about programming concepts.</p>",
    "url": "test-page",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}

# Canvas File Test Data
DEFAULT_FILE_INFO = {
    "id": 789,
    "display_name": "test_document.pdf",
    "filename": "test_document.pdf",
    "content-type": "application/pdf",
    "size": 12345,
    "url": "https://canvas.example.com/files/789/download",
    "created_at": "2024-01-01T00:00:00Z",
}

DEFAULT_FILE_CONTENT = b"%PDF-1.4\nTest PDF content for extraction testing"

# Quiz Configuration Test Data
DEFAULT_QUIZ_CONFIG = {
    "canvas_course_id": 123,
    "canvas_course_name": "Introduction to Computer Science",
    "title": "Test Quiz",
    "llm_model": "gpt-5-mini-2025-08-07",
    "llm_temperature": 1.0,
}

CUSTOM_QUIZ_CONFIG = {
    "canvas_course_id": 456,
    "canvas_course_name": "Advanced Programming",
    "title": "Advanced Quiz",
    "llm_model": "o3-2025-04-16",
    "llm_temperature": 0.7,
}

# Quiz Module Selection Test Data
DEFAULT_SELECTED_MODULES = {
    "456": {
        "name": "Introduction to Programming",
        "source_type": "canvas",
        "question_batches": [
            {
                "question_type": "multiple_choice",
                "count": 10,
                "difficulty": "medium",
            }
        ],
    },
    "457": {
        "name": "Data Structures and Algorithms",
        "source_type": "canvas",
        "question_batches": [
            {
                "question_type": "multiple_choice",
                "count": 15,
                "difficulty": "medium",
            }
        ],
    },
}

MIXED_QUESTION_TYPES_MODULES = {
    "456": {
        "name": "Mixed Module",
        "source_type": "canvas",
        "question_batches": [
            {
                "question_type": "multiple_choice",
                "count": 10,
                "difficulty": "medium",
            },
            {
                "question_type": "fill_in_blank",
                "count": 5,
                "difficulty": "hard",
            },
            {
                "question_type": "true_false",
                "count": 3,
                "difficulty": "easy",
            },
        ],
    },
}

MANUAL_MODULE_DATA = {
    "manual_test123": {
        "name": "Manual Test Module",
        "source_type": "manual",
        "content": "This is manual content for testing question generation.",
        "word_count": 10,
        "content_type": "text",
        "processing_metadata": {"source": "manual_text"},
        "question_batches": [
            {
                "question_type": "multiple_choice",
                "count": 5,
                "difficulty": "medium",
            }
        ],
    },
}

# Content Extraction Test Data
DEFAULT_EXTRACTED_CONTENT = {
    "modules": [
        {
            "id": "456",
            "name": "Introduction to Programming",
            "content": "Programming is the process of creating a set of instructions that tell a computer how to perform a task...",
            "content_length": 1500,
            "source_type": "canvas",
        },
        {
            "id": "457",
            "name": "Data Structures and Algorithms",
            "content": "Data structures are ways of organizing and storing data so that they can be accessed and worked with efficiently...",
            "content_length": 2000,
            "source_type": "canvas",
        },
    ],
    "total_content_length": 3500,
    "extraction_metadata": {
        "extraction_method": "canvas_api",
        "modules_processed": 2,
        "extraction_time": "2024-01-01T12:00:00Z",
    },
}

MANUAL_EXTRACTED_CONTENT = {
    "modules": [
        {
            "id": "manual_test123",
            "name": "Manual Test Module",
            "content": "This is manual content for testing question generation.",
            "content_length": 100,
            "source_type": "manual",
        },
    ],
    "total_content_length": 100,
    "extraction_metadata": {
        "extraction_method": "manual_input",
        "modules_processed": 1,
        "extraction_time": "2024-01-01T12:00:00Z",
    },
}

# Question Test Data
DEFAULT_MCQ_DATA = {
    "question_text": "What is the capital of France?",
    "option_a": "London",
    "option_b": "Paris",
    "option_c": "Berlin",
    "option_d": "Madrid",
    "correct_answer": "B",
    "explanation": "Paris is the capital and largest city of France.",
}

DEFAULT_FILL_IN_BLANK_DATA = {
    "question_text": "The capital of France is [blank_1].",
    "blanks": [
        {
            "position": 1,
            "correct_answer": "Paris",
            "answer_variations": ["paris", "PARIS"],
            "case_sensitive": False,
        }
    ],
    "explanation": "Paris is the capital of France.",
}

DEFAULT_TRUE_FALSE_DATA = {
    "question_text": "Python is a programming language.",
    "correct_answer": True,
    "explanation": "Python is indeed a popular programming language.",
}

SAMPLE_QUESTIONS_BATCH = [
    {
        "question_text": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "correct_answer": "B",
        "explanation": "Basic arithmetic: 2+2=4",
    },
    {
        "question_text": "What is the capital of Norway?",
        "option_a": "Bergen",
        "option_b": "Trondheim",
        "option_c": "Oslo",
        "option_d": "Stavanger",
        "correct_answer": "C",
        "explanation": "Oslo is the capital of Norway.",
    },
]

# OpenAI Response Test Data
DEFAULT_OPENAI_RESPONSE = {
    "content": '{"questions": [{"question_text": "What is Python?", "options": [{"text": "A programming language", "is_correct": true}, {"text": "A snake", "is_correct": false}], "explanation": "Python is a programming language."}]}',
    "usage": {
        "prompt_tokens": 20,
        "completion_tokens": 50,
        "total_tokens": 70,
    },
}

NORWEGIAN_OPENAI_RESPONSE = {
    "content": '{"questions": [{"question_text": "Hva er Python?", "options": [{"text": "Et programmeringsspråk", "is_correct": true}, {"text": "En slange", "is_correct": false}], "explanation": "Python er et programmeringsspråk."}]}',
    "usage": {
        "prompt_tokens": 25,
        "completion_tokens": 55,
        "total_tokens": 80,
    },
}

# Canvas Quiz Export Test Data
DEFAULT_CANVAS_QUIZ_RESPONSE = {
    "id": "quiz_123",
    "title": "Test Quiz",
    "quiz_type": "assignment",
    "points_possible": 100,
    "assignment_id": "assignment_456",
}

DEFAULT_QUIZ_ITEMS_RESPONSE = [
    {"success": True, "canvas_id": 8001, "question_id": "q1"},
    {"success": True, "canvas_id": 8002, "question_id": "q2"},
    {"success": True, "canvas_id": 8003, "question_id": "q3"},
]

FAILED_QUIZ_ITEMS_RESPONSE = [
    {"success": True, "canvas_id": 8001, "question_id": "q1"},
    {
        "success": False,
        "canvas_id": None,
        "question_id": "q2",
        "error": "Export failed",
    },
    {"success": True, "canvas_id": 8003, "question_id": "q3"},
]

# Language and Tone Test Data
ENGLISH_QUIZ_CONFIG = {
    **DEFAULT_QUIZ_CONFIG,
    "language": "en",
    "tone": "academic",
}

NORWEGIAN_QUIZ_CONFIG = {
    **DEFAULT_QUIZ_CONFIG,
    "canvas_course_name": "Norsk Kurs",
    "title": "Norsk Quiz",
    "language": "no",
    "tone": "casual",
}

# Difficulty Test Data
MIXED_DIFFICULTY_MODULES = {
    "456": {
        "name": "Mixed Difficulty Module",
        "source_type": "canvas",
        "question_batches": [
            {
                "question_type": "multiple_choice",
                "count": 8,
                "difficulty": "easy",
            },
            {
                "question_type": "multiple_choice",
                "count": 6,
                "difficulty": "medium",
            },
            {
                "question_type": "multiple_choice",
                "count": 4,
                "difficulty": "hard",
            },
        ],
    },
}

# Error Scenarios Test Data
NETWORK_ERROR_CONFIG = {
    "should_fail": True,
    "status_code": 500,
    "error_message": "Network connection failed",
}

AUTH_ERROR_CONFIG = {
    "should_fail": True,
    "status_code": 401,
    "error_message": "Authentication failed",
}

RATE_LIMIT_ERROR_CONFIG = {
    "should_fail": True,
    "status_code": 429,
    "error_message": "Rate limit exceeded",
}

# Workflow Test Data
COMPLETE_WORKFLOW_DATA = {
    "user": DEFAULT_USER_DATA,
    "course": DEFAULT_CANVAS_COURSE,
    "modules": DEFAULT_CANVAS_MODULES,
    "quiz_config": DEFAULT_QUIZ_CONFIG,
    "selected_modules": DEFAULT_SELECTED_MODULES,
    "extracted_content": DEFAULT_EXTRACTED_CONTENT,
    "questions": SAMPLE_QUESTIONS_BATCH,
    "canvas_response": DEFAULT_CANVAS_QUIZ_RESPONSE,
}

# Test Constants
TEST_TIMEOUT = 30.0
TEST_MAX_TOKENS = 2000
TEST_TEMPERATURE = 0.7
DEFAULT_POINTS_PER_QUESTION = 1
TEST_FILE_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB


# Helper Functions
def get_unique_user_data(canvas_id: int = None) -> Dict[str, Any]:
    """Generate unique user data for tests that need isolation."""
    if canvas_id is None:
        canvas_id = 10000 + abs(hash(str(uuid.uuid4())) % 90000)

    return {
        **DEFAULT_USER_DATA,
        "canvas_id": canvas_id,
        "name": f"Test User {canvas_id}",
        "access_token": f"test_access_token_{canvas_id}",
        "refresh_token": f"test_refresh_token_{canvas_id}",
    }


def get_unique_course_data(course_id: int = None) -> Dict[str, Any]:
    """Generate unique course data for tests that need isolation."""
    if course_id is None:
        course_id = 1000 + abs(hash(str(uuid.uuid4())) % 9000)

    return {
        **DEFAULT_CANVAS_COURSE,
        "id": course_id,
        "name": f"Test Course {course_id}",
        "course_code": f"TEST{course_id}",
    }


def get_unique_quiz_config(course_id: int = None, title: str = None) -> Dict[str, Any]:
    """Generate unique quiz config for tests that need isolation."""
    if course_id is None:
        course_id = 2000 + abs(hash(str(uuid.uuid4())) % 8000)

    if title is None:
        title = f"Test Quiz {course_id}"

    return {
        **DEFAULT_QUIZ_CONFIG,
        "canvas_course_id": course_id,
        "title": title,
    }


def get_sample_module_content(module_suffix="", large_content=False):
    """Generate sample module content for testing.

    Args:
        module_suffix: Suffix to add to module names
        large_content: Whether to generate large content sections

    Returns:
        Dict containing sample module content structure
    """
    if large_content:
        return {
            f"module_large{module_suffix}": [
                {
                    "id": "page_large",
                    "title": "Large Content",
                    "content": "This is a large content section. "
                    * 200,  # About 6600 characters
                    "url": "large-content",
                }
            ]
        }

    return {
        f"module_1{module_suffix}": [
            {
                "id": "page_1",
                "title": "Introduction to Python",
                "content": (
                    "Python is a high-level programming language. " * 10 + "\n\n"
                ),
                "url": "intro-python",
            },
            {
                "id": "page_2",
                "title": "Variables and Data Types",
                "content": (
                    "Python has several built-in data types including integers, floats, strings, and booleans. "
                    * 5
                    + "\n\n"
                ),
                "url": "variables-data-types",
            },
        ],
        f"module_2{module_suffix}": [
            {
                "id": "page_3",
                "title": "Control Structures",
                "content": (
                    "Control structures in Python include if statements, loops, and exception handling. "
                    * 8
                ),
                "url": "control-structures",
            }
        ],
    }
