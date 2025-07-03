"""Constants for content extraction domain."""

# Content extraction size and processing limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_TOTAL_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB total per quiz
MAX_PAGES_PER_MODULE = 100  # Maximum pages per module
MAX_CONTENT_LENGTH = 500_000  # Maximum content length per page
MIN_CONTENT_LENGTH = 50  # Minimum content length
MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB per item (for validation)

# Processing configuration
PROCESSING_TIMEOUT = 30  # seconds
MAX_WORDS_PER_CONTENT = 10000  # Max words in single content item
MIN_WORDS_PER_CONTENT = 10  # Min words in single content item

# Supported content types
SUPPORTED_CONTENT_TYPES = ["text/html", "application/pdf", "text/plain"]
SUPPORTED_FORMATS = ["html", "pdf", "text"]


# Processing status
class ProcessingStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# Content type mappings for normalization
CONTENT_TYPE_MAPPINGS = {
    "text/html": "html",
    "application/pdf": "pdf",
    "text/plain": "text",
    "pdf": "pdf",  # Alternative format
    "html": "html",  # Direct format
    "text": "text",  # Direct format
}

# Legacy constant for backwards compatibility
MAX_PAGE_CONTENT_SIZE = MAX_CONTENT_SIZE  # Alias for MAX_CONTENT_SIZE

# Supported file extensions for PDF
SUPPORTED_PDF_EXTENSIONS = [".pdf"]

# Canvas-specific HTML selectors to remove
CANVAS_UI_SELECTORS = [
    # Canvas UI elements
    ".ic-app-header",
    ".ic-app-nav-toggle-and-crumbs",
    ".ic-app-crumbs",
    ".breadcrumbs",
    ".course-title",
    ".right-side-wrapper",
    # Canvas page elements
    ".page-toolbar",
    ".show-content",
    ".user_content_iframe",
    ".canvas_user_content",
    ".mce-content-body",
    # Navigation and UI
    '[role="navigation"]',
    '[data-component="Navigation"]',
    ".ui-widget",
    ".ui-state-default",
]

# HTML elements to remove completely
HTML_ELEMENTS_TO_REMOVE = ["script", "style", "nav", "header", "footer"]
