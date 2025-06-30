from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.canvas.content_extraction_service import ContentExtractionService


class TestContentExtractionPDF:
    """Test PDF extraction functionality in ContentExtractionService"""

    @pytest.fixture
    def service(self) -> ContentExtractionService:
        """Create a ContentExtractionService instance for testing"""
        return ContentExtractionService(
            canvas_token="test_canvas_token", course_id=37823
        )

    @pytest.fixture
    def mock_file_item(self) -> dict[str, Any]:
        """Mock Canvas file item for testing"""
        return {
            "id": 1187794,
            "title": "linear_algebra_in_4_pages.pdf",
            "position": 7,
            "indent": 0,
            "quiz_lti": False,
            "type": "File",
            "module_id": 173690,
            "html_url": "https://uit.instructure.com/courses/37823/modules/items/1187794",
            "content_id": 3611093,
            "url": "https://uit.instructure.com/api/v1/courses/37823/files/3611093",
            "published": True,
            "unpublishable": False,
        }

    @pytest.fixture
    def mock_file_info(self) -> dict[str, Any]:
        """Mock Canvas file info response"""
        return {
            "id": 3611093,
            "folder_id": 708060,
            "display_name": "linear_algebra_in_4_pages.pdf",
            "filename": "linear_algebra_in_4_pages.pdf",
            "uuid": "DbkzelfegXe2xwtsWlcwJyUg074Kwk3rSxKyC32x",
            "upload_status": "success",
            "content-type": "application/pdf",
            "url": "https://uit.instructure.com/files/3611093/download?download_frd=1&verifier=DbkzelfegXe2xwtsWlcwJyUg074Kwk3rSxKyC32x",
            "size": 258646,
            "created_at": "2025-06-25T06:24:29Z",
            "updated_at": "2025-06-25T06:24:29Z",
            "mime_class": "pdf",
        }

    @pytest.fixture
    def mock_pdf_content(self) -> bytes:
        """Create a minimal valid PDF for testing"""
        # This is a minimal PDF structure that pypdf can read
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000204 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF"""
        return pdf_content

    @pytest.mark.asyncio
    async def test_extract_file_content_success(
        self,
        service: ContentExtractionService,
        mock_file_item: dict[str, Any],
        mock_file_info: dict[str, Any],
        mock_pdf_content: bytes,
    ) -> None:
        """Test successful PDF file content extraction"""
        with (
            patch.object(service, "_fetch_file_info") as mock_fetch_file_info,
            patch.object(service, "_download_and_extract_pdf") as mock_download_extract,
        ):
            mock_fetch_file_info.return_value = mock_file_info
            mock_download_extract.return_value = "This is extracted PDF text content with sufficient length to meet the minimum requirements for content validation."

            result = await service._extract_file_content(mock_file_item)

            assert result is not None
            assert result["title"] == "linear_algebra_in_4_pages.pdf"
            assert (
                result["content"]
                == "This is extracted PDF text content with sufficient length to meet the minimum requirements for content validation."
            )
            assert result["type"] == "file"
            assert result["content_type"] == "application/pdf"

            # Verify method calls
            mock_fetch_file_info.assert_called_once_with(3611093)
            mock_download_extract.assert_called_once_with(
                3611093, mock_file_info["url"]
            )

    @pytest.mark.asyncio
    async def test_extract_file_content_no_content_id(
        self, service: ContentExtractionService
    ) -> None:
        """Test file extraction with missing content_id"""
        file_item_no_id = {
            "id": 1187794,
            "title": "test.pdf",
            "type": "File",
            # Missing content_id
        }

        result = await service._extract_file_content(file_item_no_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_extract_file_content_unsupported_type(
        self, service: ContentExtractionService, mock_file_item: dict[str, Any]
    ) -> None:
        """Test file extraction with unsupported file type"""
        unsupported_file_info = {
            "id": 3611093,
            "display_name": "document.docx",
            "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "mime_class": "doc",
            "size": 50000,
            "url": "https://example.com/download",
        }

        with patch.object(service, "_fetch_file_info") as mock_fetch_file_info:
            mock_fetch_file_info.return_value = unsupported_file_info

            result = await service._extract_file_content(mock_file_item)
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_file_content_file_too_large(
        self, service: ContentExtractionService, mock_file_item: dict[str, Any]
    ) -> None:
        """Test file extraction with file exceeding size limit"""
        large_file_info = {
            "id": 3611093,
            "display_name": "large_file.pdf",
            "content-type": "application/pdf",
            "mime_class": "pdf",
            "size": 11 * 1024 * 1024,  # 11MB, exceeds 10MB limit
            "url": "https://example.com/download",
        }

        with patch.object(service, "_fetch_file_info") as mock_fetch_file_info:
            mock_fetch_file_info.return_value = large_file_info

            result = await service._extract_file_content(mock_file_item)
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_file_content_short_content(
        self,
        service: ContentExtractionService,
        mock_file_item: dict[str, Any],
        mock_file_info: dict[str, Any],
    ) -> None:
        """Test file extraction with content too short (below MIN_CONTENT_LENGTH)"""
        with (
            patch.object(service, "_fetch_file_info") as mock_fetch_file_info,
            patch.object(service, "_download_and_extract_pdf") as mock_download_extract,
        ):
            mock_fetch_file_info.return_value = mock_file_info
            mock_download_extract.return_value = "Short"  # Less than 50 chars

            result = await service._extract_file_content(mock_file_item)
            assert result is None

    @pytest.mark.asyncio
    async def test_extract_file_content_truncation(
        self,
        service: ContentExtractionService,
        mock_file_item: dict[str, Any],
        mock_file_info: dict[str, Any],
    ) -> None:
        """Test file extraction with content exceeding MAX_CONTENT_LENGTH"""
        long_content = "A" * 500_001  # Exceeds 500,000 char limit

        with (
            patch.object(service, "_fetch_file_info") as mock_fetch_file_info,
            patch.object(service, "_download_and_extract_pdf") as mock_download_extract,
        ):
            mock_fetch_file_info.return_value = mock_file_info
            mock_download_extract.return_value = long_content

            result = await service._extract_file_content(mock_file_item)

            assert result is not None
            assert len(result["content"]) == 500_000  # Truncated to limit
            assert result["content"] == "A" * 500_000

    @pytest.mark.asyncio
    async def test_fetch_file_info_success(
        self, service: ContentExtractionService, mock_file_info: dict[str, Any]
    ) -> None:
        """Test successful file info fetching"""
        with patch.object(service, "_make_request_with_retry") as mock_request:
            mock_request.return_value = mock_file_info

            result = await service._fetch_file_info(3611093)

            assert result == mock_file_info
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "courses/37823/files/3611093" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_fetch_file_info_error(
        self, service: ContentExtractionService
    ) -> None:
        """Test file info fetching with error"""
        with patch.object(service, "_make_request_with_retry") as mock_request:
            mock_request.side_effect = Exception("Network error")

            result = await service._fetch_file_info(3611093)
            assert result == {}

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_success(
        self, service: ContentExtractionService, mock_pdf_content: bytes
    ) -> None:
        """Test successful PDF download and text extraction"""
        with (
            patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx,
            patch("app.services.content_extraction.pypdf.PdfReader") as mock_pdf_reader,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = mock_pdf_content
            mock_response.raise_for_status.return_value = None

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            # Mock PDF reader to return predictable text
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content extracted successfully with sufficient length for validation."

            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = await service._download_and_extract_pdf(
                3611093, "https://example.com/download"
            )

            # Should extract the mocked text
            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0
            assert "Test PDF content extracted successfully" in result

            # Verify HTTP client was called correctly
            mock_client.get.assert_called_once_with(
                "https://example.com/download",
                follow_redirects=True,
                timeout=60.0,
            )

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_http_error(
        self, service: ContentExtractionService
    ) -> None:
        """Test PDF download with HTTP error"""
        with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_http_error = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )

            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_http_error
            mock_httpx.return_value.__aenter__.return_value = mock_client

            result = await service._download_and_extract_pdf(
                3611093, "https://example.com/download"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_network_error(
        self, service: ContentExtractionService
    ) -> None:
        """Test PDF download with network error"""
        with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.RequestError("Connection failed")
            mock_httpx.return_value.__aenter__.return_value = mock_client

            result = await service._download_and_extract_pdf(
                3611093, "https://example.com/download"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_corrupt_pdf(
        self, service: ContentExtractionService
    ) -> None:
        """Test PDF extraction with corrupt PDF data"""
        corrupt_pdf_data = b"This is not a valid PDF file"

        with patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx:
            mock_response = MagicMock()
            mock_response.content = corrupt_pdf_data
            mock_response.raise_for_status.return_value = None

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            result = await service._download_and_extract_pdf(
                3611093, "https://example.com/download"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_page_extraction_error(
        self, service: ContentExtractionService, mock_pdf_content: bytes
    ) -> None:
        """Test PDF extraction with page extraction errors"""
        with (
            patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx,
            patch("app.services.content_extraction.pypdf.PdfReader") as mock_pdf_reader,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = mock_pdf_content
            mock_response.raise_for_status.return_value = None

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            # Mock PDF reader with page extraction error
            mock_page = MagicMock()
            mock_page.extract_text.side_effect = Exception("Page extraction failed")

            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader

            result = await service._download_and_extract_pdf(
                3611093, "https://example.com/download"
            )

            # Should return empty string since no pages extracted successfully
            assert result == ""

    @pytest.mark.asyncio
    async def test_download_and_extract_pdf_memory_cleanup(
        self, service: ContentExtractionService, mock_pdf_content: bytes
    ) -> None:
        """Test that PDF buffer is properly cleaned up even when errors occur"""
        with (
            patch("app.services.content_extraction.httpx.AsyncClient") as mock_httpx,
            patch("app.services.content_extraction.io.BytesIO") as mock_bytesio,
        ):
            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.content = mock_pdf_content
            mock_response.raise_for_status.return_value = None

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            # Mock BytesIO buffer
            mock_buffer = MagicMock()
            mock_bytesio.return_value = mock_buffer

            # Mock pypdf to raise an error during extraction
            with patch(
                "app.services.content_extraction.pypdf.PdfReader"
            ) as mock_pdf_reader:
                mock_pdf_reader.side_effect = Exception("PDF parsing failed")

                result = await service._download_and_extract_pdf(
                    3611093, "https://example.com/download"
                )

                # Should return None due to error
                assert result is None

                # Verify buffer was closed and cleaned up
                mock_buffer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_module_content_with_files(
        self, service: ContentExtractionService, mock_file_item: dict[str, Any]
    ) -> None:
        """Test module content extraction including file items"""
        mock_module_items = [
            {
                "id": 1001,
                "title": "Introduction Page",
                "type": "Page",
                "page_url": "introduction",
            },
            mock_file_item,  # PDF file
            {
                "id": 1003,
                "title": "Assignment",
                "type": "Assignment",
                "assignment_id": 5001,
            },
        ]

        mock_page_content = {
            "title": "Introduction Page",
            "content": "This is page content with sufficient length to meet the minimum requirements.",
            "type": "page",
        }

        mock_file_content = {
            "title": "linear_algebra_in_4_pages.pdf",
            "content": "This is PDF content with sufficient length to meet the minimum requirements.",
            "type": "file",
            "content_type": "application/pdf",
        }

        with (
            patch.object(service, "_fetch_module_items") as mock_fetch_items,
            patch.object(service, "_extract_page_content") as mock_extract_page,
            patch.object(service, "_extract_file_content") as mock_extract_file,
        ):
            mock_fetch_items.return_value = mock_module_items
            mock_extract_page.return_value = mock_page_content
            mock_extract_file.return_value = mock_file_content

            result = await service.extract_content_for_modules([173690])

            assert "module_173690" in result
            module_content = result["module_173690"]
            assert len(module_content) == 2  # Page and file, assignment ignored

            # Find page and file content in results
            page_result = next(
                item for item in module_content if item["type"] == "page"
            )
            file_result = next(
                item for item in module_content if item["type"] == "file"
            )

            assert page_result["title"] == "Introduction Page"
            assert file_result["title"] == "linear_algebra_in_4_pages.pdf"
            assert file_result["content_type"] == "application/pdf"

            # Verify method calls
            mock_extract_page.assert_called_once()
            mock_extract_file.assert_called_once()
