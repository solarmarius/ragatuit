import httpx
from fastapi import APIRouter, HTTPException

from app.api.deps import CanvasToken, CurrentUser
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import CanvasCourse

router = APIRouter(prefix="/canvas", tags=["canvas"])
logger = get_logger("canvas")


@router.get("/courses", response_model=list[CanvasCourse])
async def get_courses(
    current_user: CurrentUser, canvas_token: CanvasToken
) -> list[CanvasCourse]:
    """
    Fetch Canvas courses where the current user has teacher enrollment.

    Returns a list of courses where the authenticated user is enrolled as a teacher.
    This endpoint filters courses to only include those where the user can create quizzes.

    **Returns:**
        List[CanvasCourse]: List of courses with id and name only

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if Canvas token is invalid or expired
        HTTPException: 503 if unable to connect to Canvas
        HTTPException: 500 if Canvas API returns unexpected data

    **Example Response:**
        [
            {"id": 37823, "name": "SB_ME_INF-0005 Praktisk kunstig intelligens"},
            {"id": 37824, "name": "SB_ME_INF-0006 Bruk av generativ KI"}
        ]
    """
    logger.info(
        "courses_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
    )

    try:
        # Canvas token is automatically refreshed by the CanvasToken dependency
        # if it's expiring within 5 minutes

        # Call Canvas API to get courses
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"http://canvas-mock:8001/api/v1/courses",
                    headers={
                        "Authorization": f"Bearer {canvas_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                courses_data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    "courses_fetch_failed_canvas_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                )

                if e.response.status_code == 401:
                    # This should not happen if CanvasToken dependency works correctly,
                    # but handle it gracefully just in case
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas access token invalid. Please re-login.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Canvas API error: {e.response.status_code}",
                    )
            except httpx.RequestError as e:
                logger.error(
                    "courses_fetch_failed_network_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=503, detail="Failed to connect to Canvas API"
                )

        # Filter courses where user has teacher enrollment
        teacher_courses = []
        for course in courses_data:
            try:
                # Check if course has enrollments and user is a teacher
                enrollments = course.get("enrollments", [])
                is_teacher = any(
                    enrollment.get("type") == "teacher" for enrollment in enrollments
                )

                if is_teacher and "id" in course and "name" in course:
                    teacher_courses.append(
                        CanvasCourse(id=course["id"], name=course["name"])
                    )

            except (KeyError, TypeError) as e:
                logger.warning(
                    "courses_parse_error_skipping_course",
                    user_id=str(current_user.id),
                    course_id=course.get("id", "unknown"),
                    error=str(e),
                )
                continue

        logger.info(
            "courses_fetch_completed",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            teacher_courses_count=len(teacher_courses),
        )

        return teacher_courses

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "courses_fetch_unexpected_error",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Unexpected error fetching courses")


# TODO: Add these endpoints in future features:
# @router.get("/courses/{course_id}/modules")
# async def get_course_modules(course_id: int, current_user: CurrentUser):
#     """Fetch modules for a specific course"""
#     pass
#
# @router.get("/courses/{course_id}/modules/{module_id}/items")
# async def get_module_items(course_id: int, module_id: int, current_user: CurrentUser):
#     """Fetch items/pages within a specific module"""
#     pass
