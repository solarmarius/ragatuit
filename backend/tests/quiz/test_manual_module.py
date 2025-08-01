"""Tests for manual module service layer."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile


@pytest.mark.asyncio
async def test_process_uploaded_file_success():
    """Test successful PDF file processing."""
    from src.quiz.manual import process_uploaded_file

    # Create mock file content (PDF-like binary data)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF"

    # Create mock UploadFile
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test_document.pdf"
    mock_file.read = AsyncMock(return_value=pdf_content)

    result = await process_uploaded_file(mock_file)

    # Verify result structure
    assert result.content_type == "pdf"
    assert result.title == "test_document.pdf"
    assert result.metadata["source"] == "manual_upload"
    assert result.metadata["filename"] == "test_document.pdf"
    assert result.metadata["file_size"] == len(pdf_content)

    # Verify file was read
    mock_file.read.assert_called_once()


@pytest.mark.asyncio
async def test_process_uploaded_file_invalid_extension():
    """Test file processing with invalid file extension."""
    from src.quiz.manual import process_uploaded_file

    # Mock non-PDF file
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "document.txt"

    with pytest.raises(HTTPException) as exc_info:
        await process_uploaded_file(mock_file)

    assert exc_info.value.status_code == 400
    assert "Only PDF files are supported" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_uploaded_file_no_filename():
    """Test file processing with no filename."""
    from src.quiz.manual import process_uploaded_file

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = None

    with pytest.raises(HTTPException) as exc_info:
        await process_uploaded_file(mock_file)

    assert exc_info.value.status_code == 400
    assert "Only PDF files are supported" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_uploaded_file_oversized():
    """Test file processing with file size exceeding limit."""
    from src.quiz.manual import process_uploaded_file

    # Create oversized content (6MB)
    oversized_content = b"x" * (6 * 1024 * 1024)

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "large_document.pdf"
    mock_file.read = AsyncMock(return_value=oversized_content)

    with pytest.raises(HTTPException) as exc_info:
        await process_uploaded_file(mock_file)

    assert exc_info.value.status_code == 400
    assert "exceeds maximum limit of 5.0MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_success():
    """Test successful processing of multiple PDF files."""
    from src.quiz.manual import process_multiple_uploaded_files

    # Mock file contents
    pdf_content_1 = b"%PDF-1.4\nSample PDF 1 content"
    pdf_content_2 = b"%PDF-1.4\nSample PDF 2 content"

    # Mock UploadFile objects
    mock_file_1 = MagicMock(spec=UploadFile)
    mock_file_1.filename = "doc1.pdf"
    mock_file_1.read = AsyncMock(return_value=pdf_content_1)

    mock_file_2 = MagicMock(spec=UploadFile)
    mock_file_2.filename = "doc2.pdf"
    mock_file_2.read = AsyncMock(return_value=pdf_content_2)

    files = [mock_file_1, mock_file_2]

    # Mock content processors and process_content
    with (
        patch("src.quiz.manual.CONTENT_PROCESSORS") as mock_processors,
        patch("src.quiz.manual.process_content") as mock_process_content,
    ):
        # Mock processor
        mock_processors.__contains__ = Mock(return_value=True)
        mock_processors.__getitem__ = Mock(return_value=Mock())

        # Mock processed content for each file
        mock_processed_1 = Mock()
        mock_processed_1.content = "Extracted text from PDF 1"
        mock_processed_1.word_count = 5

        mock_processed_2 = Mock()
        mock_processed_2.content = "Extracted text from PDF 2"
        mock_processed_2.word_count = 5

        mock_process_content.side_effect = [mock_processed_1, mock_processed_2]

        result = await process_multiple_uploaded_files(files)

        # Verify result structure
        assert result.content_type == "text"  # Combined content is text
        assert result.title == "doc1.pdf and 1 other file(s)"
        assert result.metadata["source"] == "manual_multi_upload"
        assert result.metadata["total_files"] == 2
        assert result.metadata["filenames"] == ["doc1.pdf", "doc2.pdf"]

        # Verify content includes both files with separator
        assert "Extracted text from PDF 1" in result.content
        assert "Extracted text from PDF 2" in result.content
        assert "--- Document 2: doc2.pdf ---" in result.content


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_empty_list():
    """Test multiple file processing with empty file list."""
    from src.quiz.manual import process_multiple_uploaded_files

    with pytest.raises(HTTPException) as exc_info:
        await process_multiple_uploaded_files([])

    assert exc_info.value.status_code == 400
    assert "At least one file must be provided" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_too_many():
    """Test multiple file processing with too many files."""
    from src.quiz.manual import process_multiple_uploaded_files

    # Create 6 mock files (exceeding limit of 5)
    files = []
    for i in range(6):
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = f"doc{i+1}.pdf"
        files.append(mock_file)

    with pytest.raises(HTTPException) as exc_info:
        await process_multiple_uploaded_files(files)

    assert exc_info.value.status_code == 400
    assert "Maximum 5 files allowed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_total_size_exceeded():
    """Test multiple file processing with total size exceeding limit."""
    from src.quiz.manual import process_multiple_uploaded_files

    # Create files that individually are under 5MB but together exceed 25MB
    # 4.5MB each × 6 files = 27MB total (exceeds 25MB limit)
    large_content = b"x" * (int(4.5 * 1024 * 1024))  # 4.5MB each

    files = []
    for i in range(6):  # 6 files × 4.5MB = 27MB total
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = f"large_doc{i+1}.pdf"
        mock_file.read = AsyncMock(return_value=large_content)
        files.append(mock_file)

    with pytest.raises(HTTPException) as exc_info:
        await process_multiple_uploaded_files(files)

    assert exc_info.value.status_code == 400
    # Should fail on file count limit first (max 5 files)
    assert "Maximum 5 files allowed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_total_size_validation():
    """Test multiple file processing with total size exceeding limit (individual files OK)."""
    from src.quiz.manual import process_multiple_uploaded_files

    # Use 3 files to test total size validation properly
    # 3 files of 4.5MB each = 13.5MB (all under 5MB individual limit)
    # Then make total exceed 25MB: need files totaling > 25MB
    # Use 6 files of 4.5MB each = 27MB total > 25MB (but violates 5 file limit)
    # Use 5 files: 4 × 4.5MB + 1 × 7MB = 18MB + 7MB = 25MB (7MB exceeds individual)

    # Correct approach: Use files that can exceed total limit without exceeding individual limit
    # This requires having more than 25MB ÷ 5MB = 5 files, or having unequal file sizes

    # Solution: Use exactly 6 files of 4.2MB each = 25.2MB > 25MB total
    # But this exceeds the 5 file count limit, so it will fail on count first

    # Alternative: Mock the implementation to test total validation in isolation
    # Or change the test to use different size files

    # Working solution: Use 4 files that total just over 25MB
    file_size = int(6.3 * 1024 * 1024)  # 6.3MB each - exceeds individual limit

    # Better approach: Use 3 large files that exceed total but stay under individual
    # 3 files of 4.9MB each = 14.7MB (under 25MB)
    # 6 files of 4.9MB each = 29.4MB (over 25MB but violates file count)
    # 5 files of 4.9MB each = 24.5MB (under 25MB)

    # The only way to test total size validation properly is to have more files
    # or have some files exceed individual limits

    # Final working approach: Test the scenario where total would be checked
    # Use patch to temporarily modify the limits for testing

    with patch(
        "src.quiz.manual.MAX_TOTAL_FILE_SIZE", 20 * 1024 * 1024
    ):  # Lower total limit to 20MB
        files = []
        # Use 5 files of 4.1MB each = 20.5MB > 20MB total, but each < 5MB individual
        for i in range(5):
            mock_file = MagicMock(spec=UploadFile)
            mock_file.filename = f"test_doc{i+1}.pdf"
            content = b"x" * int(4.1 * 1024 * 1024)  # 4.1MB each
            mock_file.read = AsyncMock(return_value=content)
            files.append(mock_file)

        with pytest.raises(HTTPException) as exc_info:
            await process_multiple_uploaded_files(files)

        assert exc_info.value.status_code == 400
        assert "Total file size" in exc_info.value.detail
        assert "exceeds maximum limit of 20.0MB" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_multiple_uploaded_files_mixed_invalid_extension():
    """Test multiple file processing with mixed valid/invalid extensions."""
    from src.quiz.manual import process_multiple_uploaded_files

    mock_file_1 = MagicMock(spec=UploadFile)
    mock_file_1.filename = "valid.pdf"

    mock_file_2 = MagicMock(spec=UploadFile)
    mock_file_2.filename = "invalid.txt"

    files = [mock_file_1, mock_file_2]

    with pytest.raises(HTTPException) as exc_info:
        await process_multiple_uploaded_files(files)

    assert exc_info.value.status_code == 400
    assert "Only PDF files are supported" in exc_info.value.detail
    assert "invalid.txt" in exc_info.value.detail


@pytest.mark.asyncio
async def test_process_text_content_success():
    """Test successful text content processing."""
    from src.quiz.manual import process_text_content

    text = "This is sample text content for testing manual module creation."
    module_name = "Test Module"

    result = await process_text_content(text, module_name)

    # Verify result structure
    assert result.content == text
    assert result.content_type == "text"
    assert result.title == module_name
    assert result.metadata["source"] == "manual_text"
    assert result.metadata["character_count"] == len(text)


@pytest.mark.asyncio
async def test_create_manual_module_with_text_success():
    """Test successful manual module creation with text content."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    module_data = ManualModuleCreate(
        name="Test Text Module",
        text_content="This is test content for the manual module.",
    )

    # Mock content processing
    with (
        patch("src.quiz.manual.CONTENT_PROCESSORS") as mock_processors,
        patch("src.quiz.manual.process_content") as mock_process_content,
    ):
        mock_processors.__contains__ = Mock(return_value=True)
        mock_processors.__getitem__ = Mock(return_value=Mock())

        mock_processed = Mock()
        mock_processed.content = "This is test content for the manual module."
        mock_processed.word_count = 9
        mock_processed.processing_metadata = {"processing_time": 0.1}

        mock_process_content.return_value = mock_processed

        result = await create_manual_module(module_data)

        # Verify result structure
        assert result.name == "Test Text Module"
        assert result.module_id.startswith("manual_")
        assert result.word_count == 9
        assert result.content_preview == "This is test content for the manual module."
        assert result.full_content == "This is test content for the manual module."
        assert result.processing_metadata == {"processing_time": 0.1}


@pytest.mark.asyncio
async def test_create_manual_module_with_file_success():
    """Test successful manual module creation with file upload."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    module_data = ManualModuleCreate(name="Test PDF Module")

    # Mock PDF file
    pdf_content = b"%PDF-1.4\nTest PDF content"
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.read = AsyncMock(return_value=pdf_content)

    # Mock content processing
    with (
        patch("src.quiz.manual.CONTENT_PROCESSORS") as mock_processors,
        patch("src.quiz.manual.process_content") as mock_process_content,
    ):
        mock_processors.__contains__ = Mock(return_value=True)
        mock_processors.__getitem__ = Mock(return_value=Mock())

        mock_processed = Mock()
        mock_processed.content = "Extracted PDF content for testing"
        mock_processed.word_count = 5
        mock_processed.processing_metadata = {"extraction_method": "pdf"}

        mock_process_content.return_value = mock_processed

        result = await create_manual_module(module_data, file=mock_file)

        # Verify result structure
        assert result.name == "Test PDF Module"
        assert result.module_id.startswith("manual_")
        assert result.word_count == 5
        assert result.content_preview == "Extracted PDF content for testing"
        assert result.full_content == "Extracted PDF content for testing"


@pytest.mark.asyncio
async def test_create_manual_module_no_content():
    """Test manual module creation with no content provided."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    module_data = ManualModuleCreate(name="Test Module")

    with pytest.raises(HTTPException) as exc_info:
        await create_manual_module(module_data)

    assert exc_info.value.status_code == 400
    assert (
        "Either file upload(s) or text content must be provided"
        in exc_info.value.detail
    )


@pytest.mark.asyncio
async def test_create_manual_module_multiple_inputs():
    """Test manual module creation with both file and text provided."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    module_data = ManualModuleCreate(
        name="Test Module", text_content="Some text content"
    )

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"

    with pytest.raises(HTTPException) as exc_info:
        await create_manual_module(module_data, file=mock_file)

    assert exc_info.value.status_code == 400
    assert (
        "Provide either file upload(s) or text content, not both"
        in exc_info.value.detail
    )


@pytest.mark.asyncio
async def test_create_manual_module_processing_failure():
    """Test manual module creation with content processing failure."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    module_data = ManualModuleCreate(name="Test Module", text_content="Test content")

    # Mock content processing failure
    with (
        patch("src.quiz.manual.CONTENT_PROCESSORS") as mock_processors,
        patch("src.quiz.manual.process_content") as mock_process_content,
    ):
        mock_processors.__contains__ = Mock(return_value=True)
        mock_processors.__getitem__ = Mock(return_value=Mock())
        mock_process_content.return_value = None  # Processing failed

        with pytest.raises(HTTPException) as exc_info:
            await create_manual_module(module_data)

        assert exc_info.value.status_code == 400
        assert "Failed to process content" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_manual_module_content_preview_truncation():
    """Test content preview truncation for long content."""
    from src.quiz.manual import create_manual_module
    from src.quiz.schemas import ManualModuleCreate

    # Create long content (over 500 characters)
    long_content = "A" * 600
    module_data = ManualModuleCreate(
        name="Long Content Module", text_content=long_content
    )

    # Mock content processing
    with (
        patch("src.quiz.manual.CONTENT_PROCESSORS") as mock_processors,
        patch("src.quiz.manual.process_content") as mock_process_content,
    ):
        mock_processors.__contains__ = Mock(return_value=True)
        mock_processors.__getitem__ = Mock(return_value=Mock())

        mock_processed = Mock()
        mock_processed.content = long_content
        mock_processed.word_count = 1
        mock_processed.processing_metadata = {}

        mock_process_content.return_value = mock_processed

        result = await create_manual_module(module_data)

        # Verify preview is truncated
        assert len(result.content_preview) == 503  # 500 + "..."
        assert result.content_preview.endswith("...")
        assert result.full_content == long_content  # Full content preserved


def test_generate_module_id():
    """Test manual module ID generation."""
    from src.quiz.manual import generate_module_id

    module_id = generate_module_id()

    # Verify format
    assert module_id.startswith("manual_")
    assert len(module_id) == 15  # "manual_" + 8 hex chars

    # Verify uniqueness
    another_id = generate_module_id()
    assert module_id != another_id


def test_create_manual_module_selection():
    """Test manual module selection creation."""
    from src.content_extraction.models import ProcessedContent
    from src.quiz.manual import create_manual_module_selection

    module_id = "manual_test123"
    module_name = "Test Module"
    processed_content = ProcessedContent(
        title=module_name,
        content="Test content",
        word_count=2,
        content_type="text",
        processing_metadata={"test": True},
    )

    result = create_manual_module_selection(module_id, module_name, processed_content)

    # Verify structure
    assert module_id in result
    module_data = result[module_id]
    assert module_data["name"] == module_name
    assert module_data["source_type"] == "manual"
    assert module_data["content"] == "Test content"
    assert module_data["word_count"] == 2
    assert module_data["processing_metadata"] == {"test": True}
    assert module_data["content_type"] == "text"


def test_create_manual_module_selection_from_response():
    """Test manual module selection creation from response."""
    from src.question.types import QuestionDifficulty, QuestionType
    from src.quiz.manual import create_manual_module_selection_from_response
    from src.quiz.schemas import ManualModuleResponse

    response = ManualModuleResponse(
        module_id="manual_test123",
        name="Test Response Module",
        content_preview="Preview content...",
        full_content="Full content for testing",
        word_count=4,
        processing_metadata={"source": "test"},
    )

    question_batches = [
        {
            "question_type": QuestionType.MULTIPLE_CHOICE,
            "count": 5,
            "difficulty": QuestionDifficulty.MEDIUM,
        }
    ]

    result = create_manual_module_selection_from_response(response, question_batches)

    # Verify structure
    assert result["name"] == "Test Response Module"
    assert result["source_type"] == "manual"
    assert result["content"] == "Full content for testing"
    assert result["word_count"] == 4
    assert result["processing_metadata"] == {"source": "test"}
    assert result["content_type"] == "text"
    assert result["question_batches"] == question_batches


@pytest.mark.asyncio
async def test_prepare_manual_module_for_quiz_already_processed():
    """Test prepare manual module for quiz when already processed."""
    from src.quiz.manual import prepare_manual_module_for_quiz

    module_data = {
        "name": "Test Module",
        "content": "Existing content",
        "word_count": 2,
        "processing_metadata": {"test": True},
        "content_type": "text",
    }
    module_id = "manual_test123"

    result = await prepare_manual_module_for_quiz(module_data, module_id)

    # Verify source_type is set and data is preserved
    assert result["source_type"] == "manual"
    assert result["name"] == "Test Module"
    assert result["content"] == "Existing content"
    assert result["word_count"] == 2


@pytest.mark.asyncio
async def test_prepare_manual_module_for_quiz_missing_content():
    """Test prepare manual module for quiz with missing content."""
    from src.quiz.manual import prepare_manual_module_for_quiz

    module_data = {"name": "Test Module"}
    module_id = "manual_test123"

    result = await prepare_manual_module_for_quiz(module_data, module_id)

    # Verify defaults are set
    assert result["source_type"] == "manual"
    assert result["name"] == "Test Module"
    assert result["content"] == ""
    assert result["word_count"] == 0
    assert result["processing_metadata"] == {}
    assert result["content_type"] == "text"


def test_get_full_manual_content():
    """Test getting full manual content."""
    from src.content_extraction.models import ProcessedContent
    from src.quiz.manual import get_full_manual_content

    processed_content = ProcessedContent(
        title="Test",
        content="Full content for retrieval",
        word_count=4,
        content_type="text",
    )

    result = get_full_manual_content(processed_content)

    assert result == "Full content for retrieval"
