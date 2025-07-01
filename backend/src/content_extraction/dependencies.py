"""Function composition and dependencies for content extraction."""

from collections.abc import Awaitable, Callable

from .models import ProcessedContent, RawContent
from .service import create_processor_selector, process_content_batch
from .validators import create_content_validator


def get_content_processor() -> (
    Callable[[list[RawContent]], Awaitable[list[ProcessedContent]]]
):
    """
    Create configured content processor function for batch processing.

    Returns:
        Async function that processes list[RawContent] -> list[ProcessedContent]

    Examples:
        >>> process_contents = get_content_processor()
        >>> results = await process_contents(raw_content_list)
    """
    processor_selector = create_processor_selector()
    validator = create_content_validator()

    async def process_contents(
        raw_contents: list[RawContent],
    ) -> list[ProcessedContent]:
        """
        Process a batch of raw content items.

        Args:
            raw_contents: List of content to process

        Returns:
            List of successfully processed content
        """
        return await process_content_batch(raw_contents, processor_selector, validator)

    return process_contents


def get_single_content_processor() -> (
    Callable[[RawContent], Awaitable[ProcessedContent | None]]
):
    """
    Create single content processor function.

    Returns:
        Async function that processes RawContent -> ProcessedContent | None

    Examples:
        >>> process_single = get_single_content_processor()
        >>> result = await process_single(raw_content)
    """
    processor_selector = create_processor_selector()
    validator = create_content_validator()

    async def process_single_content(
        raw_content: RawContent,
    ) -> ProcessedContent | None:
        """
        Process a single content item.

        Args:
            raw_content: Content to process

        Returns:
            Processed content or None if processing fails
        """
        from .service import process_content

        try:
            processor = processor_selector(raw_content.content_type)
            return await process_content(raw_content, processor, validator)
        except Exception:
            return None

    return process_single_content


def get_processor_for_type(
    content_type: str,
) -> Callable[[RawContent], ProcessedContent | None]:
    """
    Get processor function for specific content type.

    Args:
        content_type: Content type to get processor for

    Returns:
        Processor function for the content type

    Examples:
        >>> html_processor = get_processor_for_type("html")
        >>> result = html_processor(raw_content)
    """
    processor_selector = create_processor_selector()
    return processor_selector(content_type)


def create_configured_validator() -> Callable[[RawContent], bool]:
    """
    Create configured content validator.

    Returns:
        Validator function with all validation rules applied
    """
    return create_content_validator()
