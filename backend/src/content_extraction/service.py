"""Main service functions for content extraction."""

import time
from collections.abc import Callable

from src.logging_config import get_logger

from .exceptions import UnsupportedFormatError
from .models import ProcessedContent, ProcessingSummary, RawContent
from .processors import CONTENT_PROCESSORS

logger = get_logger("content_extraction_service")

# Type aliases for cleaner signatures
ProcessorFunc = Callable[[RawContent], ProcessedContent | None]
ValidatorFunc = Callable[[RawContent], bool]


async def process_content(
    raw_content: RawContent,
    processor_func: ProcessorFunc,
    validator_func: ValidatorFunc | None = None,
) -> ProcessedContent | None:
    """
    Process a single content item using provided functions.

    Pure function: same input always produces same output.

    Args:
        raw_content: Content to process
        processor_func: Function to process the content
        validator_func: Optional validation function

    Returns:
        ProcessedContent or None if processing fails

    Examples:
        >>> processor = get_processor("html")
        >>> validator = create_content_validator()
        >>> result = await process_content(raw_content, processor, validator)
    """
    # Optional validation
    if validator_func and not validator_func(raw_content):
        logger.info(
            "content_validation_failed",
            content_type=raw_content.content_type,
            title=raw_content.title,
        )
        return None

    # Process content
    try:
        processed = processor_func(raw_content)

        if processed:
            logger.info(
                "content_processing_success",
                content_type=raw_content.content_type,
                title=processed.title,
                word_count=processed.word_count,
            )
        else:
            logger.info(
                "content_processing_failed",
                content_type=raw_content.content_type,
                title=raw_content.title,
                reason="processor_returned_none",
            )

        return processed

    except Exception as e:
        logger.error(
            "content_processing_error",
            content_type=raw_content.content_type,
            title=raw_content.title,
            error=str(e),
            exc_info=True,
        )
        return None


async def process_content_batch(
    raw_contents: list[RawContent],
    get_processor: Callable[[str], ProcessorFunc],
    validator_func: ValidatorFunc | None = None,
) -> list[ProcessedContent]:
    """
    Process multiple content items using appropriate processors.

    Args:
        raw_contents: List of content to process
        get_processor: Function that returns processor for content type
        validator_func: Optional validation function

    Returns:
        List of successfully processed content

    Examples:
        >>> processor_selector = create_processor_selector()
        >>> validator = create_content_validator()
        >>> results = await process_content_batch(contents, processor_selector, validator)
    """
    start_time = time.time()
    results = []

    logger.info(
        "batch_processing_started",
        total_items=len(raw_contents),
        content_types=[item.content_type for item in raw_contents],
    )

    for i, raw_content in enumerate(raw_contents):
        try:
            processor = get_processor(raw_content.content_type)
            processed = await process_content(raw_content, processor, validator_func)

            if processed:
                results.append(processed)

        except UnsupportedFormatError as e:
            logger.warning(
                "unsupported_content_type",
                content_type=raw_content.content_type,
                title=raw_content.title,
                error=str(e),
            )
            continue
        except Exception as e:
            logger.error(
                "batch_processing_item_error",
                item_index=i,
                content_type=raw_content.content_type,
                title=raw_content.title,
                error=str(e),
                exc_info=True,
            )
            continue

    processing_time = time.time() - start_time

    logger.info(
        "batch_processing_completed",
        total_items=len(raw_contents),
        successful_items=len(results),
        failed_items=len(raw_contents) - len(results),
        processing_time=processing_time,
    )

    return results


def create_processor_selector() -> Callable[[str], ProcessorFunc]:
    """
    Factory function that returns a processor selector.

    Returns a function that maps content types to processor functions.

    Returns:
        Function that maps content_type -> processor function

    Examples:
        >>> get_processor = create_processor_selector()
        >>> html_processor = get_processor("html")
        >>> pdf_processor = get_processor("pdf")
    """

    def get_processor(content_type: str) -> ProcessorFunc:
        """
        Get processor function for content type.

        Args:
            content_type: Type of content to process

        Returns:
            Processor function for the content type

        Raises:
            UnsupportedFormatError: If content type is not supported
        """
        # Normalize content type
        normalized_type = content_type.lower()

        # Map common MIME types to our processor keys
        type_mappings = {
            "text/html": "html",
            "application/pdf": "pdf",
            "text/plain": "text",
            "html": "html",
            "pdf": "pdf",
            "text": "text",
        }

        processor_key = type_mappings.get(normalized_type, normalized_type)
        processor = CONTENT_PROCESSORS.get(processor_key)

        if not processor:
            raise UnsupportedFormatError(content_type)

        return processor

    return get_processor


async def create_processing_summary(
    raw_contents: list[RawContent],
    processed_contents: list[ProcessedContent],
    processing_time: float,
) -> ProcessingSummary:
    """
    Create a summary of processing results.

    Args:
        raw_contents: Original content items
        processed_contents: Successfully processed items
        processing_time: Time taken for processing

    Returns:
        ProcessingSummary with statistics
    """
    # Count content types processed
    content_types_processed: dict[str, int] = {}
    for content in processed_contents:
        original_type = content.processing_metadata.get("original_type", "unknown")
        content_types_processed[original_type] = (
            content_types_processed.get(original_type, 0) + 1
        )

    # Calculate total word count
    total_word_count = sum(content.word_count for content in processed_contents)

    return ProcessingSummary(
        total_items=len(raw_contents),
        successful_items=len(processed_contents),
        failed_items=len(raw_contents) - len(processed_contents),
        total_word_count=total_word_count,
        processing_time_seconds=processing_time,
        content_types_processed=content_types_processed,
    )
