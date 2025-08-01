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

# File size limit: 5MB per file, 25MB total
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_TOTAL_FILE_SIZE = 25 * 1024 * 1024
MAX_FILES_COUNT = 5


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


async def process_multiple_uploaded_files(files: list[UploadFile]) -> RawContent:
    """
    Process multiple uploaded files and concatenate their content.

    Args:
        files: List of FastAPI UploadFile objects

    Returns:
        RawContent object with concatenated content ready for processing

    Raises:
        HTTPException: If file validation fails or total size exceeds limit
    """
    if not files:
        raise HTTPException(
            status_code=400, detail="At least one file must be provided"
        )

    if len(files) > MAX_FILES_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES_COUNT} files allowed per manual module",
        )

    # Validate each file and store content to avoid multiple reads
    total_size = 0
    file_names = []
    file_contents = []  # Store the content during validation

    for file in files:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are supported. Invalid file: {file.filename}",
            )

        # Read file content once and store it
        content_bytes = await file.read()
        file_size = len(content_bytes)

        # Validate individual file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds maximum size of {MAX_FILE_SIZE / (1024*1024):.1f}MB",
            )

        total_size += file_size
        file_names.append(file.filename)
        file_contents.append(content_bytes)  # Store content for later use

    # Validate total size
    if total_size > MAX_TOTAL_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Total file size ({total_size / (1024*1024):.1f}MB) exceeds maximum limit of {MAX_TOTAL_FILE_SIZE / (1024*1024):.1f}MB",
        )

    # Process each file and concatenate content
    concatenated_content_parts = []
    all_metadata: dict[str, Any] = {
        "source": "manual_multi_upload",
        "total_files": len(files),
        "total_file_size": total_size,
        "filenames": file_names,
        "individual_file_sizes": [len(content) for content in file_contents],
    }

    # Process each PDF individually and extract text content
    for i, (file, content_bytes) in enumerate(zip(files, file_contents, strict=False)):
        # Create individual RawContent for each file
        individual_raw_content = RawContent(
            content=content_bytes.decode("latin-1"),
            content_type="pdf",
            title=file.filename or f"document_{i+1}.pdf",
            metadata={
                "source": "manual_multi_upload_individual",
                "file_size": len(content_bytes),
                "filename": file.filename,
                "file_index": i + 1,
            },
        )

        # Process individual PDF through content extraction pipeline
        if individual_raw_content.content_type not in CONTENT_PROCESSORS:
            logger.warning(
                "unsupported_content_type_in_multi_upload",
                content_type=individual_raw_content.content_type,
                filename=file.filename,
            )
            continue

        processor = CONTENT_PROCESSORS[individual_raw_content.content_type]
        processed_individual = await process_content(individual_raw_content, processor)

        if not processed_individual:
            logger.warning(
                "individual_file_processing_failed",
                filename=file.filename,
                file_index=i + 1,
            )
            # Don't add error messages to content - just skip this file
            continue

        # Add document separator (except for first file)
        if i > 0:
            concatenated_content_parts.append(
                f"\n\n--- Document {i + 1}: {file.filename} ---\n\n"
            )

        # Add the extracted text content, not raw binary data
        concatenated_content_parts.append(processed_individual.content)

        logger.info(
            "multi_file_processed",
            filename=file.filename,
            file_size=len(content_bytes),
            extracted_word_count=processed_individual.word_count,
            file_index=i + 1,
            total_files=len(files),
        )

    # Combine all content
    combined_content = "".join(concatenated_content_parts)

    # Check if we have any meaningful content
    if not combined_content.strip():
        logger.warning(
            "multi_file_upload_no_content_extracted",
            total_files=len(files),
            filenames=file_names,
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract text from any of the uploaded PDF files. "
                "The files may contain only images, be password-protected, or be corrupted. "
                "Please try uploading PDF files with extractable text content."
            ),
        )

    # Create combined title
    if len(files) == 1:
        title = files[0].filename or "uploaded_file.pdf"
    else:
        first_filename = files[0].filename or "uploaded_file.pdf"
        title = f"{first_filename} and {len(files) - 1} other file(s)"

    # Create RawContent object with combined extracted text content
    raw_content = RawContent(
        content=combined_content,
        content_type="text",  # Now it's extracted text, not raw PDF
        title=title,
        metadata=all_metadata,
    )

    logger.info(
        "multi_file_upload_completed",
        total_files=len(files),
        total_size=total_size,
        combined_content_length=len(combined_content),
        title=title,
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
    module_data: ManualModuleCreate,
    file: UploadFile | None = None,
    files: list[UploadFile] | None = None,
) -> ManualModuleResponse:
    """
    Create a manual module from single file, multiple files, or text content.

    Args:
        module_data: Manual module creation data
        file: Optional single uploaded file (for backward compatibility)
        files: Optional list of uploaded files (for multi-file upload)

    Returns:
        ManualModuleResponse with processed content preview

    Raises:
        HTTPException: If processing fails or no content provided
    """
    # Count how many input methods are provided
    input_methods = sum(
        [bool(file), bool(files and len(files) > 0), bool(module_data.text_content)]
    )

    if input_methods == 0:
        raise HTTPException(
            status_code=400,
            detail="Either file upload(s) or text content must be provided",
        )

    if input_methods > 1:
        raise HTTPException(
            status_code=400,
            detail="Provide either file upload(s) or text content, not both",
        )

    # Generate unique module ID
    module_id = f"manual_{uuid.uuid4().hex[:8]}"

    try:
        # Process content based on input type
        if files and len(files) > 0:
            raw_content = await process_multiple_uploaded_files(files)
        elif file:
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
            # Determine more specific error message based on content type
            if raw_content.content_type == "pdf":
                error_msg = (
                    "Could not extract text from the PDF file. "
                    "This file may contain only images, be password-protected, "
                    "or be corrupted. Please try a different PDF with extractable text."
                )
            else:
                error_msg = "Failed to process content. Please check the content format and try again."

            logger.warning(
                "content_processing_returned_none",
                content_type=raw_content.content_type,
                title=raw_content.title,
                module_name=module_data.name,
            )

            raise HTTPException(status_code=400, detail=error_msg)

        # Additional check for empty content
        if not processed_content.content.strip():
            logger.warning(
                "processed_content_empty",
                content_type=raw_content.content_type,
                title=raw_content.title,
                module_name=module_data.name,
            )
            if raw_content.content_type == "pdf":
                error_msg = (
                    "The PDF file appears to be empty or contains no extractable text. "
                    "Please upload a PDF with readable text content."
                )
            else:
                error_msg = (
                    "The content appears to be empty. Please provide non-empty content."
                )

            raise HTTPException(status_code=400, detail=error_msg)

        # Create preview (first 500 characters)
        content_preview = processed_content.content[:500]
        if len(processed_content.content) > 500:
            content_preview += "..."

        response = ManualModuleResponse(
            module_id=module_id,
            name=module_data.name,
            content_preview=content_preview,
            full_content=processed_content.content,
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


def create_manual_module_selection_from_response(
    response: ManualModuleResponse, question_batches: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Create a complete manual module selection from ManualModuleResponse and question batches.

    This function bridges the gap between the manual module upload response and the
    data structure needed for quiz creation.

    Args:
        response: ManualModuleResponse from create_manual_module
        question_batches: List of question batch configurations

    Returns:
        Dictionary suitable for use as ModuleSelection in quiz creation
    """
    return {
        "name": response.name,
        "source_type": "manual",
        "content": response.full_content,  # Use full content for question generation
        "word_count": response.word_count,
        "processing_metadata": response.processing_metadata,
        "content_type": "text",  # Default for now, could be enhanced
        "question_batches": question_batches,
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


def get_full_manual_content(processed_content: ProcessedContent) -> str:
    """
    Get the full content for a manual module (not just the preview).

    In the current implementation, we store the preview in the response,
    but for question generation we need the full content. This function
    would ideally retrieve the full content from a cache or storage system.

    Args:
        module_id: Manual module ID
        processed_content: Full processed content object

    Returns:
        Full content string for question generation
    """
    # For now, return the full content directly
    # In production, this might retrieve from Redis/cache using module_id
    return processed_content.content
