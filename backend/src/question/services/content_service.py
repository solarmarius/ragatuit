"""Content processing functions for module-based question generation."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session

logger = get_logger("content_service")


async def get_content_from_quiz(quiz_id: UUID) -> dict[str, Any]:
    """
    Get extracted content from a quiz.

    Args:
        quiz_id: Quiz identifier

    Returns:
        Content dictionary

    Raises:
        ValueError: If no content is found
    """
    logger.info("content_extraction_started", quiz_id=str(quiz_id))

    try:
        async with get_async_session() as session:
            from src.quiz.service import get_content_from_quiz as _get_quiz_content

            content_dict = await _get_quiz_content(session, quiz_id)

            if not content_dict:
                raise ValueError(f"No extracted content found for quiz {quiz_id}")

            logger.info(
                "content_extraction_completed",
                quiz_id=str(quiz_id),
                modules_count=len(content_dict),
                total_content_size=_calculate_total_content_size(content_dict),
            )

            return content_dict

    except Exception as e:
        logger.error(
            "content_extraction_failed",
            quiz_id=str(quiz_id),
            error=str(e),
            exc_info=True,
        )
        raise


def validate_module_content(content_dict: dict[str, Any]) -> dict[str, str]:
    """
    Validate and prepare module content for question generation.

    Args:
        content_dict: Content dictionary from quiz

    Returns:
        Dictionary mapping module_id to concatenated module content
    """
    logger.info(
        "module_content_validation_started",
        modules_count=len(content_dict),
    )

    validated_modules = {}

    for module_id, pages in content_dict.items():
        if not isinstance(pages, list):
            logger.warning(
                "module_content_invalid_format",
                module_id=module_id,
                type=type(pages).__name__,
            )
            continue

        module_content = _combine_module_pages(module_id, pages)

        if (
            module_content and len(module_content.strip()) >= 100
        ):  # Minimum content length
            validated_modules[module_id] = module_content
            logger.debug(
                "module_content_validated",
                module_id=module_id,
                content_length=len(module_content),
                word_count=len(module_content.split()),
            )
        else:
            logger.warning(
                "module_content_insufficient",
                module_id=module_id,
                content_length=len(module_content) if module_content else 0,
            )

    logger.info(
        "module_content_validation_completed",
        total_modules=len(content_dict),
        validated_modules=len(validated_modules),
        total_content_size=sum(len(content) for content in validated_modules.values()),
    )

    return validated_modules


async def prepare_content_for_generation(
    quiz_id: UUID, custom_content: dict[str, Any] | None = None
) -> dict[str, str]:
    """
    Prepare content for module-based question generation.

    Args:
        quiz_id: Quiz identifier
        custom_content: Optional custom content to use instead of quiz content

    Returns:
        Dictionary mapping module_id to prepared module content
    """
    if custom_content:
        content_dict = custom_content
        logger.info(
            "using_custom_content",
            quiz_id=str(quiz_id),
            modules_count=len(content_dict),
        )
    else:
        content_dict = await get_content_from_quiz(quiz_id)

    return validate_module_content(content_dict)


def validate_content_quality(modules_content: dict[str, str]) -> dict[str, str]:
    """
    Validate and filter module content based on quality criteria.

    Args:
        modules_content: Dictionary mapping module_id to content

    Returns:
        Filtered dictionary of high-quality module content
    """
    logger.info("module_quality_validation_started", input_modules=len(modules_content))

    quality_modules = {}

    for module_id, content in modules_content.items():
        quality_score = _calculate_module_quality_score(content)

        if (
            quality_score >= 0.4
        ):  # Quality threshold for modules (lowered for practical use)
            quality_modules[module_id] = content
            logger.debug(
                "module_content_quality_validated",
                module_id=module_id,
                quality_score=quality_score,
                content_length=len(content),
            )
        else:
            logger.warning(
                "module_content_filtered_low_quality",
                module_id=module_id,
                quality_score=quality_score,
                content_length=len(content),
            )

    logger.info(
        "module_quality_validation_completed",
        input_modules=len(modules_content),
        output_modules=len(quality_modules),
        avg_quality_score=sum(
            _calculate_module_quality_score(content)
            for content in quality_modules.values()
        )
        / len(quality_modules)
        if quality_modules
        else 0,
    )

    return quality_modules


def get_content_statistics(modules_content: dict[str, str]) -> dict[str, Any]:
    """
    Get statistics about module content.

    Args:
        modules_content: Dictionary mapping module_id to content

    Returns:
        Statistics dictionary
    """
    if not modules_content:
        return {
            "total_modules": 0,
            "total_characters": 0,
            "total_words": 0,
            "avg_module_size": 0,
            "avg_word_count": 0,
            "module_ids": [],
        }

    total_characters = sum(len(content) for content in modules_content.values())
    total_words = sum(len(content.split()) for content in modules_content.values())
    module_lengths = [len(content) for content in modules_content.values()]

    return {
        "total_modules": len(modules_content),
        "total_characters": total_characters,
        "total_words": total_words,
        "avg_module_size": total_characters // len(modules_content),
        "avg_word_count": total_words // len(modules_content),
        "min_module_size": min(module_lengths) if module_lengths else 0,
        "max_module_size": max(module_lengths) if module_lengths else 0,
        "module_ids": list(modules_content.keys()),
        "module_count": len(modules_content),
    }


def _combine_module_pages(_module_id: str, pages: list[dict[str, Any]]) -> str:
    """Combine all pages from a module into a single content string."""
    module_content_parts = []

    for page in pages:
        if not isinstance(page, dict):
            continue

        page_content = page.get("content", "")
        if (
            not page_content or len(page_content.strip()) < 10
        ):  # Skip very short content
            continue

        # Add page title as context if available
        page_title = page.get("title", "")
        if page_title:
            module_content_parts.append(f"## {page_title}\n")

        module_content_parts.append(page_content.strip())
        module_content_parts.append("\n\n")  # Separator between pages

    return "\n".join(module_content_parts).strip()


def _calculate_total_content_size(content_dict: dict[str, Any]) -> int:
    """Calculate total size of content in characters."""
    total_size = 0

    for pages in content_dict.values():
        if isinstance(pages, list):
            for page in pages:
                if isinstance(page, dict):
                    content = page.get("content", "")
                    total_size += len(content)

    return total_size


def _calculate_module_quality_score(content: str) -> float:
    """
    Calculate quality score for module content.

    Args:
        content: Module content to evaluate

    Returns:
        Quality score between 0.0 and 1.0
    """
    content = content.strip()

    if not content:
        return 0.0

    score = 0.0
    content_length = len(content)
    word_count = len(content.split())

    # Length score (prefer modules with substantial content)
    length_score = min(content_length / 5000, 1.0)  # Target ~5000 chars
    if length_score < 0.1:  # Very short content
        length_score *= 0.3
    score += length_score * 0.3

    # Word count score (prefer modules with adequate word count)
    word_score = min(word_count / 500, 1.0)  # Target ~500 words
    score += word_score * 0.2

    # Sentence structure score (look for complete sentences)
    sentence_endings = content.count(".") + content.count("!") + content.count("?")
    sentence_score = min(sentence_endings / max(word_count / 20, 1), 1.0)
    score += sentence_score * 0.2

    # Content richness score (avoid repetitive content)
    unique_words = len(set(content.lower().split()))
    richness_score = min(unique_words / max(word_count, 1), 1.0)
    score += richness_score * 0.2

    # Low markup ratio score (avoid content with excessive formatting)
    formatting_chars = (
        content.count("<")
        + content.count(">")
        + content.count("[")
        + content.count("]")
    )
    formatting_ratio = formatting_chars / content_length if content_length > 0 else 0
    formatting_score = max(0, 1.0 - formatting_ratio * 10)  # Penalize high markup ratio
    score += formatting_score * 0.1

    return min(score, 1.0)


# Convenience function for common workflow
async def prepare_and_validate_content(
    quiz_id: UUID,
    custom_content: dict[str, Any] | None = None,
    quality_filter: bool = True,
) -> dict[str, str]:
    """
    Complete content preparation pipeline with optional quality filtering.

    Args:
        quiz_id: Quiz identifier
        custom_content: Optional custom content
        quality_filter: Whether to apply quality filtering

    Returns:
        Prepared and optionally filtered module content
    """
    content = await prepare_content_for_generation(quiz_id, custom_content)

    if quality_filter:
        content = validate_content_quality(content)

    return content
