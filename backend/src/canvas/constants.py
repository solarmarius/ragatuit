"""
Constants for Canvas module.
"""

# Content extraction limits
MAX_PAGE_CONTENT_SIZE = 1024 * 1024  # 1MB per page
SUPPORTED_FILE_TYPES = ["application/pdf", "pdf"]  # Supported file content types

# Canvas API constants
CANVAS_API_TIMEOUT = 30.0  # seconds
CANVAS_API_MAX_RETRIES = 3
CANVAS_API_RETRY_DELAY = 1.0  # seconds

# Module item types
MODULE_ITEM_TYPE_PAGE = "Page"
MODULE_ITEM_TYPE_FILE = "File"
MODULE_ITEM_TYPE_ASSIGNMENT = "Assignment"
MODULE_ITEM_TYPE_QUIZ = "Quiz"
MODULE_ITEM_TYPE_DISCUSSION = "Discussion"
MODULE_ITEM_TYPE_EXTERNAL_URL = "ExternalUrl"
MODULE_ITEM_TYPE_EXTERNAL_TOOL = "ExternalTool"

# Quiz settings
QUIZ_SHUFFLE_QUESTIONS = True
QUIZ_SHUFFLE_ANSWERS = True
QUIZ_POINTS_PER_QUESTION = 1

# Canvas quiz item types
CANVAS_QUIZ_ITEM_TYPE = "Question"
CANVAS_QUIZ_ENTRY_TYPE = "Item"
CANVAS_QUIZ_INTERACTION_TYPE = "choice"
CANVAS_QUIZ_SCORING_ALGORITHM = "Equivalence"
