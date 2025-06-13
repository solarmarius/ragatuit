MOCK_CANVAS_TOKEN_RESPONSE = {
    "access_token": "mock_access_token",
    "refresh_token": "mock_refresh_token",
    "expires_in": 3600,
    "token_type": "Bearer",
}

MOCK_CANVAS_USER_PROFILE = {
    "id": 1234,
    "name": "Test Teacher",
    "primary_email": "teacher@example.edu",
    "login_id": "teacher_login",
}

MOCK_CANVAS_COURSES = [
    {
        "id": 101,
        "name": "Introduction to Computer Science",
        "course_code": "CS101",
        "workflow_state": "available",
        "enrollments": [{"type": "student", "role": "StudentEnrollment"}],
    },
    {
        "id": 102,
        "name": "Advanced Mathematics",
        "course_code": "MATH201",
        "workflow_state": "available",
        "enrollments": [{"type": "teacher", "role": "TeacherEnrollment"}],
    },
]
