"""Manual module service functions for handling file uploads and text content."""

import uuid
from typing import Any

from fastapi import HTTPException, UploadFile

from src.config import get_logger
from src.content_extraction.models import ProcessedContent, RawContent
from src.content_extraction.processors import CONTENT_PROCESSORS
from src.content_extraction.service import process_content

from .schemas import ManualModuleCreate, ManualModuleResponse

logger = get_logger("manual_module_service")

# File size limit: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024


async def process_uploaded_file(file: UploadFile) -> RawContent:
    """
    Process an uploaded file and convert to RawContent.

    Args:
        file: FastAPI UploadFile object

    Returns:
        RawContent object ready for processing

    Raises:
        HTTPException: If file validation fails
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    content_bytes = await file.read()

    # Validate file size
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB",
        )

    # Convert bytes to string for RawContent (PDF processor expects string)
    content_str = content_bytes.decode("latin-1")

    # Create RawContent object
    raw_content = RawContent(
        content=content_str,
        content_type="pdf",
        title=file.filename,
        metadata={
            "source": "manual_upload",
            "file_size": len(content_bytes),
            "filename": file.filename,
        },
    )

    logger.info(
        "file_uploaded_for_processing",
        filename=file.filename,
        file_size=len(content_bytes),
        content_type="pdf",
    )

    return raw_content


async def process_text_content(text: str, module_name: str) -> RawContent:
    """
    Process direct text input and convert to RawContent.

    Args:
        text: Raw text content
        module_name: Name for the module

    Returns:
        RawContent object ready for processing
    """
    raw_content = RawContent(
        content=text,
        content_type="text",
        title=module_name,
        metadata={"source": "manual_text", "character_count": len(text)},
    )

    logger.info(
        "text_content_prepared_for_processing",
        module_name=module_name,
        character_count=len(text),
        content_type="text",
    )

    return raw_content


async def create_manual_module(
    module_data: ManualModuleCreate, file: UploadFile | None = None
) -> ManualModuleResponse:
    """
    Create a manual module from file upload or text content.

    Args:
        module_data: Manual module creation data
        file: Optional uploaded file

    Returns:
        ManualModuleResponse with processed content preview

    Raises:
        HTTPException: If processing fails or no content provided
    """
    # Validate that either file or text content is provided
    if not file and not module_data.text_content:
        raise HTTPException(
            status_code=400,
            detail="Either file upload or text content must be provided",
        )

    if file and module_data.text_content:
        raise HTTPException(
            status_code=400,
            detail="Provide either file upload or text content, not both",
        )

    # Generate unique module ID
    module_id = f"manual_{uuid.uuid4().hex[:8]}"

    try:
        # Process content based on input type
        if file:
            raw_content = await process_uploaded_file(file)
        else:
            # We already validated text_content exists above
            text_content = module_data.text_content or ""
            raw_content = await process_text_content(text_content, module_data.name)

        # Get appropriate processor
        if raw_content.content_type not in CONTENT_PROCESSORS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {raw_content.content_type}",
            )

        processor = CONTENT_PROCESSORS[raw_content.content_type]

        # Process content
        processed_content = await process_content(raw_content, processor)

        if not processed_content:
            raise HTTPException(
                status_code=400,
                detail="Failed to process content. Please check file format and try again.",
            )

        # Create preview (first 500 characters)
        content_preview = processed_content.content[:500]
        if len(processed_content.content) > 500:
            content_preview += "..."

        response = ManualModuleResponse(
            module_id=module_id,
            name=module_data.name,
            content_preview=content_preview,
            word_count=processed_content.word_count,
            processing_metadata=processed_content.processing_metadata,
        )

        logger.info(
            "manual_module_created",
            module_id=module_id,
            module_name=module_data.name,
            word_count=processed_content.word_count,
            content_type=raw_content.content_type,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "manual_module_creation_failed", module_name=module_data.name, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail="Failed to process content. Please try again."
        )


def generate_module_id() -> str:
    """Generate a unique manual module ID."""
    return f"manual_{uuid.uuid4().hex[:8]}"


def create_manual_module_selection(
    module_id: str, module_name: str, processed_content: ProcessedContent
) -> dict[str, Any]:
    """
    Create a manual module selection entry for use in extracted_content.

    Args:
        module_id: Manual module ID
        module_name: Module name
        processed_content: Processed content object

    Returns:
        Dictionary suitable for storing in quiz.extracted_content
    """
    return {
        module_id: {
            "name": module_name,
            "source_type": "manual",
            "content": processed_content.content,
            "word_count": processed_content.word_count,
            "processing_metadata": processed_content.processing_metadata,
            "content_type": processed_content.content_type,
        }
    }


async def prepare_manual_module_for_quiz(
    module_data: dict[str, Any], module_id: str
) -> dict[str, Any]:
    """
    Prepare a manual module for storage in quiz.selected_modules.

    This function processes manual module content and stores the processed content
    directly in the module data so it's available during content extraction.

    Args:
        module_data: Module data from frontend (includes content info)
        module_id: The manual module ID

    Returns:
        Updated module data with processed content stored
    """
    # Check if this module already has processed content
    if "content" in module_data and "word_count" in module_data:
        # Already processed, just ensure source_type is set
        module_data["source_type"] = "manual"
        return module_data

    # If we get here, we need to process content from a temporary storage or cache
    # For now, this function expects the content to already be processed
    # In a production system, you might store temporary content in Redis or similar

    logger.warning(
        "manual_module_missing_processed_content",
        module_id=module_id,
        module_name=module_data.get("name", "unknown"),
    )

    # Set default values if content is missing
    module_data.setdefault("content", "")
    module_data.setdefault("word_count", 0)
    module_data.setdefault("processing_metadata", {})
    module_data.setdefault("content_type", "text")
    module_data["source_type"] = "manual"

    return module_data
