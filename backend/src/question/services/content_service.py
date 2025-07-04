"""Content processing service for question generation."""

from typing import Any
from uuid import UUID

from src.config import get_logger
from src.database import get_async_session

from ..workflows import ContentChunk, WorkflowConfiguration

logger = get_logger("content_service")


class ContentProcessingService:
    """
    Service for processing and preparing content for question generation.

    Handles content extraction, chunking, and preparation for different
    question types and workflows.
    """

    def __init__(self, configuration: WorkflowConfiguration):
        """
        Initialize content processing service.

        Args:
            configuration: Workflow configuration for content processing
        """
        self.configuration = configuration

    async def get_content_from_quiz(self, quiz_id: UUID) -> dict[str, Any]:
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
                from src.quiz.service import get_content_from_quiz

                content_dict = await get_content_from_quiz(session, quiz_id)

                if not content_dict:
                    raise ValueError(f"No extracted content found for quiz {quiz_id}")

                logger.info(
                    "content_extraction_completed",
                    quiz_id=str(quiz_id),
                    modules_count=len(content_dict),
                    total_content_size=self._calculate_total_content_size(content_dict),
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

    def chunk_content(self, content_dict: dict[str, Any]) -> list[ContentChunk]:
        """
        Split content into manageable chunks for question generation.

        Args:
            content_dict: Content dictionary from quiz

        Returns:
            List of content chunks
        """
        logger.info(
            "content_chunking_started",
            modules_count=len(content_dict),
            max_chunk_size=self.configuration.max_chunk_size,
            min_chunk_size=self.configuration.min_chunk_size,
        )

        chunks = []

        for module_id, pages in content_dict.items():
            if not isinstance(pages, list):
                continue

            module_chunks = self._process_module_pages(module_id, pages)
            chunks.extend(module_chunks)

        # Filter chunks by minimum size
        valid_chunks = [
            chunk
            for chunk in chunks
            if len(chunk.content.strip()) >= self.configuration.min_chunk_size
        ]

        logger.info(
            "content_chunking_completed",
            total_chunks=len(valid_chunks),
            filtered_chunks=len(chunks) - len(valid_chunks),
            avg_chunk_size=sum(len(c.content) for c in valid_chunks)
            // len(valid_chunks)
            if valid_chunks
            else 0,
            avg_word_count=sum(c.get_word_count() for c in valid_chunks)
            // len(valid_chunks)
            if valid_chunks
            else 0,
        )

        return valid_chunks

    async def prepare_content_for_generation(
        self, quiz_id: UUID, custom_content: dict[str, Any] | None = None
    ) -> list[ContentChunk]:
        """
        Prepare content for question generation.

        Args:
            quiz_id: Quiz identifier
            custom_content: Optional custom content to use instead of quiz content

        Returns:
            List of prepared content chunks
        """
        if custom_content:
            content_dict = custom_content
            logger.info(
                "using_custom_content",
                quiz_id=str(quiz_id),
                modules_count=len(content_dict),
            )
        else:
            content_dict = await self.get_content_from_quiz(quiz_id)

        return self.chunk_content(content_dict)

    def validate_content_quality(
        self, chunks: list[ContentChunk]
    ) -> list[ContentChunk]:
        """
        Validate and filter content chunks based on quality criteria.

        Args:
            chunks: List of content chunks to validate

        Returns:
            Filtered list of high-quality chunks
        """
        logger.info("content_quality_validation_started", input_chunks=len(chunks))

        quality_chunks = []

        for chunk in chunks:
            quality_score = self._calculate_content_quality(chunk)

            if quality_score >= self.configuration.quality_threshold:
                quality_chunks.append(chunk)

                # Add quality score to metadata
                chunk.metadata["quality_score"] = quality_score
            else:
                logger.debug(
                    "content_chunk_filtered_low_quality",
                    source=chunk.source,
                    quality_score=quality_score,
                    threshold=self.configuration.quality_threshold,
                    content_length=len(chunk.content),
                )

        logger.info(
            "content_quality_validation_completed",
            input_chunks=len(chunks),
            output_chunks=len(quality_chunks),
            avg_quality_score=sum(
                c.metadata.get("quality_score", 0) for c in quality_chunks
            )
            / len(quality_chunks)
            if quality_chunks
            else 0,
        )

        return quality_chunks

    def get_content_statistics(self, chunks: list[ContentChunk]) -> dict[str, Any]:
        """
        Get statistics about content chunks.

        Args:
            chunks: List of content chunks

        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "total_words": 0,
                "avg_chunk_size": 0,
                "avg_word_count": 0,
                "sources": [],
            }

        total_characters = sum(chunk.get_character_count() for chunk in chunks)
        total_words = sum(chunk.get_word_count() for chunk in chunks)
        sources = list({chunk.source for chunk in chunks if chunk.source})

        return {
            "total_chunks": len(chunks),
            "total_characters": total_characters,
            "total_words": total_words,
            "avg_chunk_size": total_characters // len(chunks),
            "avg_word_count": total_words // len(chunks),
            "min_chunk_size": min(chunk.get_character_count() for chunk in chunks),
            "max_chunk_size": max(chunk.get_character_count() for chunk in chunks),
            "sources": sources,
            "source_count": len(sources),
        }

    def _process_module_pages(
        self, module_id: str, pages: list[dict[str, Any]]
    ) -> list[ContentChunk]:
        """Process pages from a module into content chunks."""
        chunks = []

        for page in pages:
            if not isinstance(page, dict):
                continue

            page_content = page.get("content", "")
            if (
                not page_content or len(page_content.strip()) < 50
            ):  # Skip very short content
                continue

            page_chunks = self._chunk_page_content(module_id, page, page_content)
            chunks.extend(page_chunks)

        return chunks

    def _chunk_page_content(
        self, module_id: str, page: dict[str, Any], content: str
    ) -> list[ContentChunk]:
        """Chunk content from a single page."""
        chunks = []

        if len(content) <= self.configuration.max_chunk_size:
            # Content fits in single chunk
            chunk = ContentChunk(
                content=content,
                source=f"{module_id}/{page.get('id', 'unknown')}",
                metadata={
                    "module_id": module_id,
                    "page_id": page.get("id"),
                    "page_title": page.get("title", ""),
                    "page_url": page.get("url"),
                    "chunk_type": "full_page",
                },
            )
            chunks.append(chunk)
        else:
            # Need to split content
            split_chunks = self._split_large_content(content, module_id, page)
            chunks.extend(split_chunks)

        return chunks

    def _split_large_content(
        self, content: str, module_id: str, page: dict[str, Any]
    ) -> list[ContentChunk]:
        """Split large content into smaller chunks."""
        chunks = []

        # Try splitting by paragraphs first
        paragraphs = content.split("\n\n")
        current_chunk = ""
        chunk_index = 0

        for paragraph in paragraphs:
            potential_chunk = current_chunk + paragraph + "\n\n"

            if len(potential_chunk) <= self.configuration.max_chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it's not empty
                if current_chunk.strip():
                    chunk = ContentChunk(
                        content=current_chunk.strip(),
                        source=f"{module_id}/{page.get('id', 'unknown')}/chunk_{chunk_index}",
                        metadata={
                            "module_id": module_id,
                            "page_id": page.get("id"),
                            "page_title": page.get("title", ""),
                            "page_url": page.get("url"),
                            "chunk_type": "split",
                            "chunk_index": chunk_index,
                            "overlap_size": self.configuration.overlap_size,
                        },
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # Start new chunk with overlap if configured
                if self.configuration.overlap_size > 0 and current_chunk:
                    # Take last N characters as overlap
                    overlap = current_chunk[-self.configuration.overlap_size :]
                    current_chunk = overlap + paragraph + "\n\n"
                else:
                    current_chunk = paragraph + "\n\n"

        # Save remaining content
        if current_chunk.strip():
            chunk = ContentChunk(
                content=current_chunk.strip(),
                source=f"{module_id}/{page.get('id', 'unknown')}/chunk_{chunk_index}",
                metadata={
                    "module_id": module_id,
                    "page_id": page.get("id"),
                    "page_title": page.get("title", ""),
                    "page_url": page.get("url"),
                    "chunk_type": "split",
                    "chunk_index": chunk_index,
                },
            )
            chunks.append(chunk)

        return chunks

    def _calculate_total_content_size(self, content_dict: dict[str, Any]) -> int:
        """Calculate total size of content in characters."""
        total_size = 0

        for pages in content_dict.values():
            if isinstance(pages, list):
                for page in pages:
                    if isinstance(page, dict):
                        content = page.get("content", "")
                        total_size += len(content)

        return total_size

    def _calculate_content_quality(self, chunk: ContentChunk) -> float:
        """
        Calculate quality score for a content chunk.

        Args:
            chunk: Content chunk to evaluate

        Returns:
            Quality score between 0.0 and 1.0
        """
        content = chunk.content.strip()

        if not content:
            return 0.0

        score = 0.0

        # Length score (prefer chunks with reasonable length)
        length_score = min(len(content) / self.configuration.max_chunk_size, 1.0)
        if length_score < 0.1:  # Very short content
            length_score *= 0.5
        score += length_score * 0.3

        # Word count score
        word_count = chunk.get_word_count()
        word_score = min(word_count / 100, 1.0)  # Target ~100 words
        score += word_score * 0.2

        # Sentence structure score (look for complete sentences)
        sentence_endings = content.count(".") + content.count("!") + content.count("?")
        sentence_score = min(sentence_endings / max(word_count / 20, 1), 1.0)
        score += sentence_score * 0.2

        # Content richness score (avoid repetitive content)
        unique_words = len(set(content.lower().split()))
        richness_score = min(unique_words / max(word_count, 1), 1.0)
        score += richness_score * 0.2

        # No excessive formatting score (avoid chunks with too much markup)
        formatting_chars = (
            content.count("<")
            + content.count(">")
            + content.count("[")
            + content.count("]")
        )
        formatting_ratio = formatting_chars / len(content)
        formatting_score = max(
            0, 1.0 - formatting_ratio * 10
        )  # Penalize high markup ratio
        score += formatting_score * 0.1

        return min(score, 1.0)
