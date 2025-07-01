"""
Canvas API routes.
"""

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from src.api.deps import CanvasToken
from src.auth.dependencies import CurrentUser
from src.config import settings
from src.logging_config import get_logger

from .schemas import CanvasCourse, CanvasModule
from .url_builder import CanvasURLBuilder

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

        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        # Call Canvas API to get courses
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url_builder.build_url("courses"),
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
                        detail="Canvas service is temporarily unavailable. Please try again later.",
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
    # Validate course_id parameter
    if course_id <= 0:
        logger.warning(
            "modules_fetch_invalid_course_id",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
        )
        raise HTTPException(
            status_code=400, detail="Course ID must be a positive integer"
        )

    logger.info(
        "modules_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        course_id=course_id,
    )

    try:
        # Canvas token is automatically refreshed by the CanvasToken dependency
        # if it's expiring within 5 minutes

        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        # Call Canvas API to get course modules
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url_builder.modules(course_id),
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
                        detail="Canvas service is temporarily unavailable. Please try again later.",
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


@router.get("/courses/{course_id}/modules/{module_id}/items")
async def get_module_items(
    course_id: int, module_id: int, current_user: CurrentUser, canvas_token: CanvasToken
) -> list[dict[str, Any]]:
    """
    Fetch items within a specific Canvas module.

    Returns a list of module items (pages, assignments, files, etc.) for content extraction.
    This endpoint fetches items to allow content processing for quiz generation.

    **Parameters:**
        course_id (int): The Canvas course ID
        module_id (int): The Canvas module ID to fetch items from

    **Returns:**
        List[dict]: List of module items with type, title, and Canvas metadata

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if Canvas token is invalid or expired
        HTTPException: 403 if user doesn't have access to the course/module
        HTTPException: 503 if unable to connect to Canvas
        HTTPException: 500 if Canvas API returns unexpected data

    **Example Response:**
        [
            {
                "id": 123456,
                "title": "Introduction to AI",
                "type": "Page",
                "html_url": "https://canvas.../pages/intro",
                "page_url": "intro",
                "url": "https://canvas.../api/v1/courses/123/pages/intro"
            }
        ]
    """
    # Validate parameters
    if course_id <= 0 or module_id <= 0:
        logger.warning(
            "module_items_fetch_invalid_parameters",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            module_id=module_id,
        )
        raise HTTPException(
            status_code=400, detail="Course ID and Module ID must be positive integers"
        )

    logger.info(
        "module_items_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        course_id=course_id,
        module_id=module_id,
    )

    try:
        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        # Call Canvas API to get module items
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url_builder.module_items(course_id, module_id),
                    headers={
                        "Authorization": f"Bearer {canvas_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                items_data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    "module_items_fetch_failed_canvas_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    module_id=module_id,
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
                        detail="You don't have access to this course or module.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas service is temporarily unavailable. Please try again later.",
                    )
            except httpx.RequestError as e:
                logger.error(
                    "module_items_fetch_failed_network_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    module_id=module_id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=503, detail="Failed to connect to Canvas API"
                )

        # Process and validate module items
        processed_items = []
        for item in items_data:
            try:
                # Validate item data structure
                if not isinstance(item, dict):
                    logger.warning(
                        "module_items_parse_error_invalid_item_type",
                        user_id=str(current_user.id),
                        course_id=course_id,
                        module_id=module_id,
                        item_type=type(item).__name__,
                    )
                    continue

                # Extract required fields
                item_id = item.get("id")
                item_title = item.get("title", "Untitled")
                item_type = item.get("type")

                if item_id is not None and item_type is not None:
                    # Convert item ID to int if needed
                    try:
                        item_id = int(item_id)
                    except (ValueError, TypeError):
                        logger.warning(
                            "module_items_parse_error_invalid_id",
                            user_id=str(current_user.id),
                            course_id=course_id,
                            module_id=module_id,
                            item_id=item_id,
                            item_title=item_title,
                        )
                        continue

                    # Create processed item with essential fields
                    processed_item = {
                        "id": item_id,
                        "title": str(item_title).strip(),
                        "type": str(item_type).strip(),
                        "html_url": item.get("html_url"),
                        "page_url": item.get("page_url"),
                        "url": item.get("url"),
                    }
                    processed_items.append(processed_item)

            except (KeyError, TypeError) as e:
                logger.warning(
                    "module_items_parse_error_skipping_item",
                    user_id=str(current_user.id),
                    course_id=course_id,
                    module_id=module_id,
                    item_id=item.get("id", "unknown"),
                    error=str(e),
                )
                continue

        logger.info(
            "module_items_fetch_completed",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            module_id=module_id,
            items_count=len(processed_items),
        )

        return processed_items

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "module_items_fetch_unexpected_error",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            module_id=module_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching module items"
        )


@router.get("/courses/{course_id}/pages/{page_url}")
async def get_page_content(
    course_id: int, page_url: str, current_user: CurrentUser, canvas_token: CanvasToken
) -> dict[str, Any]:
    """
    Fetch content of a specific Canvas page.

    Returns the full HTML content of a Canvas page for content extraction and processing.
    This endpoint is used to get the actual page content for quiz question generation.

    **Parameters:**
        course_id (int): The Canvas course ID
        page_url (str): The Canvas page URL slug (e.g., "introduction-to-ai")

    **Returns:**
        dict: Page content with title, body, and metadata

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if Canvas token is invalid or expired
        HTTPException: 403 if user doesn't have access to the course/page
        HTTPException: 404 if page not found
        HTTPException: 503 if unable to connect to Canvas
        HTTPException: 500 if Canvas API returns unexpected data

    **Example Response:**
        {
            "title": "Introduction to AI",
            "body": "<h1>Introduction</h1><p>Artificial Intelligence is...</p>",
            "url": "introduction-to-ai",
            "created_at": "2023-01-01T12:00:00Z",
            "updated_at": "2023-01-02T12:00:00Z"
        }
    """
    # Validate parameters
    if course_id <= 0:
        logger.warning(
            "page_content_fetch_invalid_course_id",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            page_url=page_url,
        )
        raise HTTPException(
            status_code=400, detail="Course ID must be a positive integer"
        )

    if not page_url or not page_url.strip():
        logger.warning(
            "page_content_fetch_invalid_page_url",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            page_url=page_url,
        )
        raise HTTPException(status_code=400, detail="Page URL cannot be empty")

    logger.info(
        "page_content_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        course_id=course_id,
        page_url=page_url,
    )

    try:
        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        # Call Canvas API to get page content
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url_builder.pages(course_id, page_url),
                    headers={
                        "Authorization": f"Bearer {canvas_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                page_data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    "page_content_fetch_failed_canvas_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    page_url=page_url,
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
                        detail="You don't have access to this course or page.",
                    )
                elif e.response.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail="Page not found in this course.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas service is temporarily unavailable. Please try again later.",
                    )
            except httpx.RequestError as e:
                logger.error(
                    "page_content_fetch_failed_network_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    page_url=page_url,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=503, detail="Failed to connect to Canvas API"
                )

        # Validate and process page data
        if not isinstance(page_data, dict):
            logger.error(
                "page_content_parse_error_invalid_response_type",
                user_id=str(current_user.id),
                course_id=course_id,
                page_url=page_url,
                response_type=type(page_data).__name__,
            )
            raise HTTPException(
                status_code=500, detail="Invalid response format from Canvas"
            )

        # Extract and validate essential fields
        processed_page = {
            "title": page_data.get("title", "Untitled Page"),
            "body": page_data.get("body", ""),
            "url": page_data.get("url", page_url),
            "created_at": page_data.get("created_at"),
            "updated_at": page_data.get("updated_at"),
        }

        # Ensure body is a string
        body_content = processed_page.get("body")
        if body_content is None:
            processed_page["body"] = ""
        else:
            processed_page["body"] = str(body_content)

        # Ensure title is a string
        processed_page["title"] = str(processed_page["title"]).strip()

        logger.info(
            "page_content_fetch_completed",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            page_url=page_url,
            content_length=len(processed_page["body"]),
            page_title=processed_page["title"],
        )

        return processed_page

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "page_content_fetch_unexpected_error",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            page_url=page_url,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching page content"
        )


@router.get("/courses/{course_id}/files/{file_id}")
async def get_file_info(
    course_id: int, file_id: int, current_user: CurrentUser, canvas_token: CanvasToken
) -> dict[str, Any]:
    """
    Fetch metadata and download URL for a specific Canvas file.

    Returns file information including the download URL needed to retrieve file content.
    This endpoint is used to get file metadata before downloading for content extraction.

    **Parameters:**
        course_id (int): The Canvas course ID
        file_id (int): The Canvas file ID

    **Returns:**
        dict: File metadata including download URL, size, content-type, etc.

    **Authentication:**
        Requires valid JWT token in Authorization header

    **Raises:**
        HTTPException: 401 if Canvas token is invalid or expired
        HTTPException: 403 if user doesn't have access to the file
        HTTPException: 404 if file not found
        HTTPException: 503 if unable to connect to Canvas
        HTTPException: 500 if Canvas API returns unexpected data

    **Example Response:**
        {
            "id": 3611093,
            "display_name": "linear_algebra_in_4_pages.pdf",
            "filename": "linear_algebra_in_4_pages.pdf",
            "content-type": "application/pdf",
            "url": "https://canvas.../files/3611093/download?download_frd=1&verifier=...",
            "size": 258646,
            "created_at": "2025-06-25T06:24:29Z",
            "updated_at": "2025-06-25T06:24:29Z"
        }
    """
    # Validate parameters
    if course_id <= 0 or file_id <= 0:
        logger.warning(
            "file_info_fetch_invalid_parameters",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            file_id=file_id,
        )
        raise HTTPException(
            status_code=400, detail="Course ID and File ID must be positive integers"
        )

    logger.info(
        "file_info_fetch_initiated",
        user_id=str(current_user.id),
        canvas_id=current_user.canvas_id,
        course_id=course_id,
        file_id=file_id,
    )

    try:
        # Initialize URL builder
        base_url = str(settings.CANVAS_BASE_URL)
        if settings.USE_CANVAS_MOCK and settings.CANVAS_MOCK_URL:
            base_url = str(settings.CANVAS_MOCK_URL)
        url_builder = CanvasURLBuilder(base_url, settings.CANVAS_API_VERSION)

        # Call Canvas API to get file info
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url_builder.files(course_id, file_id),
                    headers={
                        "Authorization": f"Bearer {canvas_token}",
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                file_data = response.json()

            except httpx.HTTPStatusError as e:
                logger.error(
                    "file_info_fetch_failed_canvas_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    file_id=file_id,
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
                        detail="You don't have access to this file.",
                    )
                elif e.response.status_code == 404:
                    raise HTTPException(
                        status_code=404,
                        detail="File not found in this course.",
                    )
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Canvas service is temporarily unavailable. Please try again later.",
                    )
            except httpx.RequestError as e:
                logger.error(
                    "file_info_fetch_failed_network_error",
                    user_id=str(current_user.id),
                    canvas_id=current_user.canvas_id,
                    course_id=course_id,
                    file_id=file_id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=503, detail="Failed to connect to Canvas API"
                )

        # Validate and process file data
        if not isinstance(file_data, dict):
            logger.error(
                "file_info_parse_error_invalid_response_type",
                user_id=str(current_user.id),
                course_id=course_id,
                file_id=file_id,
                response_type=type(file_data).__name__,
            )
            raise HTTPException(
                status_code=500, detail="Invalid response format from Canvas"
            )

        # Extract essential file information
        processed_file = {
            "id": file_data.get("id"),
            "display_name": file_data.get("display_name", ""),
            "filename": file_data.get("filename", ""),
            "content-type": file_data.get("content-type", ""),
            "url": file_data.get("url", ""),  # Download URL with verifier
            "size": file_data.get("size", 0),
            "created_at": file_data.get("created_at"),
            "updated_at": file_data.get("updated_at"),
            "mime_class": file_data.get("mime_class", ""),
        }

        logger.info(
            "file_info_fetch_completed",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            file_id=file_id,
            file_name=processed_file["display_name"],
            file_size=processed_file["size"],
            content_type=processed_file["content-type"],
        )

        return processed_file

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(
            "file_info_fetch_unexpected_error",
            user_id=str(current_user.id),
            canvas_id=current_user.canvas_id,
            course_id=course_id,
            file_id=file_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching file info"
        )
