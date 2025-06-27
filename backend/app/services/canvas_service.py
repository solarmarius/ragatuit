import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CanvasService:
    """
    Service for interacting with the Canvas API.
    """

    def __init__(self, canvas_token: str):
        self.canvas_token = canvas_token
        self.base_url = settings.CANVAS_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.canvas_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, endpoint: str, json_data: dict | None = None
    ) -> dict:
        """Helper method to make HTTP requests to Canvas API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method, f"{self.base_url}{endpoint}", headers=self.headers, json=json_data
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "canvas_api_http_error",
                    method=method,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                    request_data=json_data,
                )
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Canvas API error: {e.response.text}",
                )
            except httpx.RequestError as e:
                logger.error(
                    "canvas_api_request_error",
                    method=method,
                    endpoint=endpoint,
                    error=str(e),
                    request_data=json_data,
                )
                raise HTTPException(
                    status_code=503,  # Service Unavailable
                    detail=f"Error connecting to Canvas API: {str(e)}",
                )

    async def create_canvas_quiz(
        self, course_id: int, title: str, points_possible: int, settings_sub_dict: dict | None = None
    ) -> dict:
        """
        Creates a new quiz in Canvas.

        Args:
            course_id: The ID of the course in Canvas.
            title: The title of the quiz.
            points_possible: The total points possible for the quiz.
            settings_sub_dict: A dictionary for the 'quiz_settings' field in the payload.
                               Refer to Canvas New Quizzes API documentation for details.

        Returns:
            A dictionary representing the created quiz object from Canvas.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes"
        payload = {
            "title": title,
            "points_possible": points_possible,
        }
        if settings_sub_dict is not None:
            payload["quiz_settings"] = settings_sub_dict
        else:
            # Provide default empty settings if none passed, or handle as error if required
            payload["quiz_settings"] = {}


        logger.info(
            "creating_canvas_quiz",
            course_id=course_id,
            title=title,
            points_possible=points_possible,
            settings=settings_sub_dict,
        )
        response_data = await self._request("POST", endpoint, json_data=payload)
        logger.info(
            "canvas_quiz_created",
            course_id=course_id,
            canvas_quiz_id=response_data.get("id"), # This is likely the Canvas internal ID for the quiz resource itself
            assignment_id=response_data.get("assignment_id"), # This is the one we usually store
        )
        return response_data

    async def add_question_to_canvas_quiz(
        self, course_id: int, canvas_assignment_id: str, question_data: dict
    ) -> dict:
        """
        Adds a single question to an existing Canvas quiz.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            question_data: A dictionary representing the question to be added.
                           Refer to Canvas New Quiz Items API documentation for structure.
                           Example for MCQ:
                           {
                               "entry_type": "Item",
                               "interaction_type_slug": "choice",
                               "item_body": "<p>What is the capital of France?</p>",
                               "points_possible": 1,
                               "interaction_data": {
                                   "choices": [
                                       {"id": "choice_1", "position": 1, "item_body": "<p>Berlin</p>"},
                                       {"id": "choice_2", "position": 2, "item_body": "<p>Paris</p>"},
                                       {"id": "choice_3", "position": 3, "item_body": "<p>London</p>"},
                                       {"id": "choice_4", "position": 4, "item_body": "<p>Madrid</p>"}
                                   ],
                                   "scoring_data": {"value": "choice_2"} // ID of the correct choice
                               }
                           }

        Returns:
            A dictionary representing the created quiz item object from Canvas.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items"
        logger.info(
            "adding_question_to_canvas_quiz",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            question_text=question_data.get("item_body"),
        )
        response_data = await self._request("POST", endpoint, json_data=question_data)
        logger.info(
            "question_added_to_canvas_quiz",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            canvas_item_id=response_data.get("id"),
        )
        return response_data

    async def get_canvas_quiz_details(self, course_id: int, canvas_assignment_id: str) -> dict:
        """
        Retrieves details for a specific quiz from Canvas.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.

        Returns:
            A dictionary representing the quiz details from Canvas.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}"
        logger.info(
            "getting_canvas_quiz_details",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        response_data = await self._request("GET", endpoint)
        logger.info(
            "canvas_quiz_details_retrieved",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        return response_data

    async def update_canvas_quiz(
        self, course_id: int, canvas_assignment_id: str, quiz_data: dict
    ) -> dict:
        """
        Updates an existing quiz in Canvas.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            quiz_data: A dictionary containing the quiz properties to update.

        Returns:
            A dictionary representing the updated quiz object from Canvas.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}"
        logger.info(
            "updating_canvas_quiz",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            update_data=quiz_data,
        )
        response_data = await self._request("PATCH", endpoint, json_data=quiz_data)
        logger.info(
            "canvas_quiz_updated",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        return response_data

    async def publish_canvas_quiz(
        self, course_id: int, canvas_assignment_id: str, published: bool = True
    ) -> dict:
        """
        Publishes or unpublishes a quiz in Canvas.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            published: Boolean indicating whether to publish (True) or unpublish (False).

        Returns:
            A dictionary representing the updated quiz object from Canvas.
        """
        # Publishing is done by updating the quiz with 'published': True
        quiz_data = {"published": published}
        logger.info(
            "publishing_canvas_quiz" if published else "unpublishing_canvas_quiz",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        return await self.update_canvas_quiz(course_id, canvas_assignment_id, quiz_data)

    async def delete_canvas_quiz(self, course_id: int, canvas_assignment_id: str) -> None:
        """
        Deletes a quiz from Canvas.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}"
        logger.info(
            "deleting_canvas_quiz",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        await self._request("DELETE", endpoint)
        logger.info(
            "canvas_quiz_deleted",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )

    # Methods for Quiz Items (beyond just adding)

    async def list_canvas_quiz_items(self, course_id: int, canvas_assignment_id: str) -> list[dict]:
        """
        Lists all items (questions) in a specific Canvas quiz.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.

        Returns:
            A list of dictionaries, each representing a quiz item.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items"
        logger.info(
            "listing_canvas_quiz_items",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
        )
        response_data = await self._request("GET", endpoint)
        # The API returns a dict with a key like "quiz_items" containing the list
        # Adjust this based on the actual API response structure if needed.
        # Assuming the response is directly a list of items or items are under a known key.
        items = response_data.get("quiz_items", response_data) if isinstance(response_data, dict) else response_data
        if not isinstance(items, list):
             logger.warning("unexpected_quiz_items_format", response=response_data)
             return []

        logger.info(
            "canvas_quiz_items_listed",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_count=len(items)
        )
        return items

    async def get_canvas_quiz_item_details(
        self, course_id: int, canvas_assignment_id: str, item_id: str
    ) -> dict:
        """
        Retrieves details for a specific item (question) in a Canvas quiz.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            item_id: The ID of the quiz item.

        Returns:
            A dictionary representing the quiz item details.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items/{item_id}"
        logger.info(
            "getting_canvas_quiz_item_details",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
        )
        response_data = await self._request("GET", endpoint)
        logger.info(
            "canvas_quiz_item_details_retrieved",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
        )
        return response_data

    async def update_canvas_quiz_item(
        self, course_id: int, canvas_assignment_id: str, item_id: str, item_data: dict
    ) -> dict:
        """
        Updates an existing item (question) in a Canvas quiz.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            item_id: The ID of the quiz item to update.
            item_data: A dictionary containing the item properties to update.

        Returns:
            A dictionary representing the updated quiz item object.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items/{item_id}"
        logger.info(
            "updating_canvas_quiz_item",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
            update_data=item_data,
        )
        response_data = await self._request("PATCH", endpoint, json_data=item_data)
        logger.info(
            "canvas_quiz_item_updated",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
        )
        return response_data

    async def delete_canvas_quiz_item(
        self, course_id: int, canvas_assignment_id: str, item_id: str
    ) -> None:
        """
        Deletes an item (question) from a Canvas quiz.

        Args:
            course_id: The ID of the course in Canvas.
            canvas_assignment_id: The assignment ID of the quiz in Canvas.
            item_id: The ID of the quiz item to delete.
        """
        endpoint = f"/api/quiz/v1/courses/{course_id}/quizzes/{canvas_assignment_id}/items/{item_id}"
        logger.info(
            "deleting_canvas_quiz_item",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
        )
        await self._request("DELETE", endpoint)
        logger.info(
            "canvas_quiz_item_deleted",
            course_id=course_id,
            assignment_id=canvas_assignment_id,
            item_id=item_id,
        )

# Example usage (for illustration, not part of the service class itself):
# async def main():
#     # This requires settings.CANVAS_API_URL and a valid CANVAS_USER_TOKEN to be set
#     # For testing, these might come from environment variables or a .env file
#     if not settings.CANVAS_API_URL or not settings.CANVAS_USER_TOKEN:
#         print("CANVAS_API_URL and CANVAS_USER_TOKEN must be set in settings for this example.")
#         return
#
#     service = CanvasService(canvas_token=settings.CANVAS_USER_TOKEN)
#     test_course_id = 37823 # Example course ID from docs, replace with a real one for testing
#
#     try:
#         # 1. Create a quiz
#         new_quiz_settings = {
#             "title": "My New API Quiz",
#             "points_possible": 20,
#             "quiz_settings": {
#                 "shuffle_questions": True,
#                 "shuffle_answers": True,
#                 "time_limit": 60, # minutes
#                 "allowed_attempts": 1,
#                 "scoring_policy": "keep_highest"
#             }
#         }
#         created_quiz = await service.create_canvas_quiz(test_course_id, "My Test Quiz via API", new_quiz_settings)
#         print(f"Created quiz: {created_quiz}")
#         canvas_assignment_id = created_quiz["assignment_id"]
#
#         # 2. Add a question
#         question_mcq = {
#             "entry_type": "Item",
#             "interaction_type_slug": "choice",
#             "item_body": "<p>What is 2 + 2?</p>",
#             "points_possible": 10,
#             "interaction_data": {
#                 "choices": [
#                     {"id": "choice_a", "position": 1, "item_body": "<p>3</p>"},
#                     {"id": "choice_b", "position": 2, "item_body": "<p>4</p>"},
#                     {"id": "choice_c", "position": 3, "item_body": "<p>5</p>"},
#                 ],
#                 "scoring_data": {"value": "choice_b"}
#             }
#         }
#         added_question = await service.add_question_to_canvas_quiz(test_course_id, canvas_assignment_id, question_mcq)
#         print(f"Added question: {added_question}")
#         item_id = added_question["id"]
#
#         # 3. List items
#         items = await service.list_canvas_quiz_items(test_course_id, canvas_assignment_id)
#         print(f"Quiz items: {items}")
#
#         # 4. Get quiz details
#         quiz_details = await service.get_canvas_quiz_details(test_course_id, canvas_assignment_id)
#         print(f"Quiz details: {quiz_details}")
#
#         # 5. Update quiz (e.g., change title)
#         updated_quiz = await service.update_canvas_quiz(test_course_id, canvas_assignment_id, {"title": "Updated API Quiz Title"})
#         print(f"Updated quiz: {updated_quiz}")
#
#         # 6. Publish quiz
#         published_quiz = await service.publish_canvas_quiz(test_course_id, canvas_assignment_id, True)
#         print(f"Published quiz: {published_quiz}")
#
#     except HTTPException as e:
#         print(f"HTTP Exception: {e.status_code} - {e.detail}")
#     except Exception as e:
#         print(f"An unexpected error occurred: {str(e)}")
#     finally:
#         # Clean up: Delete the quiz (optional, for testing)
#         # try:
#         #     if 'canvas_assignment_id' in locals():
#         #         await service.delete_canvas_quiz(test_course_id, canvas_assignment_id)
#         #         print(f"Deleted quiz {canvas_assignment_id}")
#         # except Exception as e:
#         #     print(f"Error deleting quiz: {str(e)}")
#
# if __name__ == "__main__":
#     import asyncio
#     # This part is for standalone testing of the service.
#     # Ensure your .env file or environment variables are set up for CANVAS_API_URL and CANVAS_USER_TOKEN.
#     # Example:
#     # CANVAS_API_URL=http://localhost:8001 (if using the mock server from docs)
#     # CANVAS_USER_TOKEN=your_mock_token (if using the mock server)
#     asyncio.run(main())
