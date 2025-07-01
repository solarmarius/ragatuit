"""Constants for content extraction domain."""

# Supported content types
SUPPORTED_CONTENT_TYPES = ["text/html", "application/pdf", "text/plain"]


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

# Size limits (duplicated from config for easy access)
MAX_PAGE_CONTENT_SIZE = 1024 * 1024  # 1MB
MAX_TOTAL_CONTENT_SIZE = 50 * 1024 * 1024  # 50MB

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
