import httpx
from fastapi import APIRouter, HTTPException

from app.api.deps import CanvasToken, CurrentUser
from app.core.logging_config import get_logger
from app.models import CanvasCourse, CanvasModule

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
                    "http://canvas-mock:8001/api/v1/courses",
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
                # Validate course data structure
                if not isinstance(course, dict):
                    logger.warning(
                        "courses_parse_error_invalid_course_type",
                        user_id=str(current_user.id),
                        course_type=type(course).__name__,
                    )
                    continue

                # Check if course has enrollments and user is a teacher
                enrollments = course.get("enrollments", [])
                is_teacher = any(
                    enrollment.get("type") == "teacher" for enrollment in enrollments
                )

                # Validate required fields and data types
                course_id = course.get("id")
                course_name = course.get("name")

                if (
                    is_teacher
                    and course_id is not None
                    and course_name is not None
                    and isinstance(course_id, int | str)
                    and isinstance(course_name, str)
                ):
                    # Convert string IDs to int if needed
                    try:
                        course_id = int(course_id)
                    except (ValueError, TypeError):
                        logger.warning(
                            "courses_parse_error_invalid_id",
                            user_id=str(current_user.id),
                            course_id=course_id,
                            course_name=course_name,
                        )
                        continue

                    teacher_courses.append(
                        CanvasCourse(id=course_id, name=course_name.strip())
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


@router.get("/courses/{course_id}/modules", response_model=list[CanvasModule])
async def get_course_modules(
    course_id: int, current_user: CurrentUser, canvas_token: CanvasToken
) -> list[CanvasModule]:
    """
    Fetch Canvas modules for a specific course.

    Returns a list of modules where the authenticated user has access.
    This endpoint fetches modules to allow teachers to select content for quiz generation.

    **Parameters:**
        course_id (int): The Canvas course ID to fetch modules from

    **Returns:**
        List[CanvasModule]: List of modules with id and name only

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if Canvas token is invalid or expired
        HTTPException: 403 if user doesn't have access to the course
        HTTPException: 503 if unable to connect to Canvas
        HTTPException: 500 if Canvas API returns unexpected data

    **Example Response:**
        [
            {"id": 173467, "name": "Templates"},
            {"id": 173468, "name": "Ressurssider for studenter"}
        ]
    """
    logger.info(
        "modules_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        course_id=course_id,
    )

    try:
        # Canvas token is automatically refreshed by the CanvasToken dependency
        # if it's expiring within 5 minutes

        # Call Canvas API to get course modules
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"http://canvas-mock:8001/api/v1/courses/{course_id}/modules",
                    headers={
                        "Authorization": f"Bearer {canvas_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                modules_data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    "modules_fetch_failed_canvas_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                )

                if e.response.status_code == 401:
                    raise HTTPException(
                        status_code=401,
                        detail="Canvas access token invalid. Please re-login.",
                    )
                elif e.response.status_code == 403:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have access to this course.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail=f"Canvas API error: {e.response.status_code}",
                    )
            except httpx.RequestError as e:
                logger.error(
                    "modules_fetch_failed_network_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=503, detail="Failed to connect to Canvas API"
                )

        # Process modules and map to our simplified CanvasModule model
        course_modules = []
        for module in modules_data:
            try:
                # Validate module data structure
                if not isinstance(module, dict):
                    logger.warning(
                        "modules_parse_error_invalid_module_type",
                        user_id=str(current_user.id),
                        course_id=course_id,
                        module_type=type(module).__name__,
                    )
                    continue

                # Validate required fields and data types
                module_id = module.get("id")
                module_name = module.get("name")

                if (
                    module_id is not None
                    and module_name is not None
                    and isinstance(module_id, int | str)
                    and isinstance(module_name, str)
                ):
                    # Convert string IDs to int if needed
                    try:
                        module_id = int(module_id)
                    except (ValueError, TypeError):
                        logger.warning(
                            "modules_parse_error_invalid_id",
                            user_id=str(current_user.id),
                            course_id=course_id,
                            module_id=module_id,
                            module_name=module_name,
                        )
                        continue

                    course_modules.append(
                        CanvasModule(id=module_id, name=module_name.strip())
                    )

            except (KeyError, TypeError) as e:
                logger.warning(
                    "modules_parse_error_skipping_module",
                    user_id=str(current_user.id),
                    course_id=course_id,
                    module_id=module.get("id", "unknown"),
                    error=str(e),
                )
                continue

        logger.info(
            "modules_fetch_completed",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            modules_count=len(course_modules),
        )

        return course_modules

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "modules_fetch_unexpected_error",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Unexpected error fetching modules")


# TODO: Add these endpoints in future features:
# @router.get("/courses/{course_id}/modules/{module_id}/items")
# async def get_module_items(course_id: int, module_id: int, current_user: CurrentUser):
#     """Fetch items/pages within a specific module"""
#     pass
