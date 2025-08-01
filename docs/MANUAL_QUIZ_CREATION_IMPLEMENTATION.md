# Manual Quiz Creation Implementation Guide

**Date:** August 1, 2025
**Feature:** Manual Module Creation for Quiz Generation
**Version:** 1.0

## 1. Feature Overview

### Description

The Manual Quiz Creation feature allows teachers to create quiz modules from their own content when Canvas courses contain only videos or other non-parseable content. Teachers can upload PDF transcripts or paste text content directly into the application, which will be processed immediately and integrated into the quiz creation workflow alongside traditional Canvas modules.

### Business Value

- **Flexibility**: Teachers are no longer limited by Canvas content types
- **Efficiency**: Immediate content processing with preview feedback
- **Integration**: Seamless mixing of Canvas and manual modules in a single quiz
- **User Experience**: Intuitive multi-step dialog workflow

### User Benefits

- Upload PDF transcripts (up to 5MB) or paste text content directly
- Real-time content processing with preview and word count
- Mixed workflows supporting both Canvas and manual modules
- Consistent question generation experience across all module types

## 2. Technical Architecture

### High-Level Architecture

```
Frontend (React + TypeScript)
├── ManualModuleDialog (Multi-step UI)
├── ModuleSelectionStep (Enhanced with manual modules)
└── Quiz Creation Flow (Updated state management)

Backend (FastAPI + SQLModel)
├── File Upload Endpoint (/quiz/manual-modules/upload)
├── Content Processing (PDF + Text)
├── Mixed Content Orchestration
└── Question Generation (Unified pipeline)

Data Flow:
1. User uploads file/text → Immediate processing → Preview
2. Module creation → Added to quiz selection
3. Quiz creation → Mixed Canvas/manual content extraction
4. Question generation → Unified LLM processing
```

### System Integration

- **Content Extraction**: Extends existing pipeline to handle manual content alongside Canvas API calls
- **Question Generation**: Uses same LLM pipeline for both Canvas and manual content
- **Quiz Management**: Backward compatible with existing Canvas-only workflows
- **Database**: Uses JSONB fields for flexible module storage with source type discrimination

## 3. Dependencies & Prerequisites

### Backend Dependencies

```toml
# Already included in existing pyproject.toml
fastapi = "^0.104.0"
sqlmodel = "^0.0.14"
pydantic = "^2.5.0"
httpx = "^0.25.2"
python-multipart = "^0.0.6"  # Required for file uploads
```

### Frontend Dependencies

```json
// Already included in existing package.json
"@chakra-ui/react": "^3.0.0",
"@tanstack/react-query": "^5.0.0",
"@tanstack/react-router": "^1.0.0",
"react-icons": "^4.12.0"
```

### Environment Setup

- Python 3.12+ with uv package manager
- Node.js 18+ with npm
- PostgreSQL database
- Docker and Docker Compose (for development)

## 4. Implementation Details

### 4.1 File Structure

```
backend/
├── src/quiz/
│   ├── manual.py              # NEW: Manual module services
│   ├── models.py              # MODIFIED: Extended validation
│   ├── orchestrator.py        # MODIFIED: Mixed content extraction
│   ├── router.py              # MODIFIED: Upload endpoint + orchestration
│   └── schemas.py             # MODIFIED: Manual module schemas

frontend/
├── src/components/QuizCreation/
│   ├── ManualModuleDialog.tsx     # NEW: Main dialog component
│   ├── FileUploadZone.tsx         # NEW: PDF upload component
│   ├── TextContentEditor.tsx      # NEW: Text input component
│   ├── ContentPreview.tsx         # NEW: Content preview component
│   └── ModuleSelectionStep.tsx    # MODIFIED: Manual module integration
└── src/routes/_layout/
    └── create-quiz.tsx            # MODIFIED: State management updates
```

### 4.2 Step-by-Step Implementation

#### Step 1: Backend Data Models and Schemas

**File:** `backend/src/quiz/schemas.py`

```python
# Add to existing imports
from fastapi import UploadFile
from pydantic import field_validator
from sqlmodel import Field, SQLModel

# Extend existing ModuleSelection
class ModuleSelection(SQLModel):
    """Schema for module selection with multiple question type batches."""

    name: str
    question_batches: list[QuestionBatch] = Field(
        min_length=1, max_length=4, description="Question type batches (1-4 per module)"
    )
    source_type: str = Field(
        default="canvas", description="Module source: 'canvas' or 'manual'"
    )

    @property
    def total_questions(self) -> int:
        """Calculate total questions across all batches."""
        return sum(batch.count for batch in self.question_batches)

# Add new schemas
class ManualModuleCreate(SQLModel):
    """Schema for creating a manual module with file upload or text content."""

    name: str = Field(min_length=1, max_length=255, description="Module name")
    text_content: str | None = Field(default=None, description="Direct text content")

    @field_validator("text_content")
    def validate_content_provided(cls, v: str | None) -> str | None:
        """Ensure at least text content is provided."""
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Text content cannot be empty")
        return v

class ManualModuleResponse(SQLModel):
    """Response schema for manual module creation."""

    module_id: str = Field(description="Generated manual module ID")
    name: str = Field(description="Module name")
    content_preview: str = Field(description="Preview of processed content")
    word_count: int = Field(description="Word count of processed content")
    processing_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Processing details"
    )

# Update QuizCreate validation
class QuizCreate(SQLModel):
    # ... existing fields ...

    @field_validator("selected_modules")
    def validate_modules(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate selected modules structure supporting both Canvas and manual modules."""
        if not v:
            raise ValueError("At least one module must be selected")

        for module_id, module_data in v.items():
            # ... existing validation ...

            # Validate source_type
            if hasattr(module_selection, "source_type"):
                if module_selection.source_type not in ["canvas", "manual"]:
                    raise ValueError(
                        f"Module {module_id} source_type must be 'canvas' or 'manual'"
                    )

                # Manual modules should have manual_ prefix
                if (
                    module_selection.source_type == "manual"
                    and not module_id.startswith("manual_")
                ):
                    raise ValueError(
                        f"Manual module {module_id} must have 'manual_' prefix"
                    )
        return v
```

**Key Points:**

- `source_type` field distinguishes Canvas vs manual modules
- Manual modules use `manual_` prefix for ID uniqueness
- Validation ensures proper module structure and content

#### Step 2: Manual Module Service

**File:** `backend/src/quiz/manual.py`

```python
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
    """Process an uploaded file and convert to RawContent."""
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read and validate file content
    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024*1024):.1f}MB",
        )

    # Convert to RawContent for processing pipeline
    content_str = content_bytes.decode("latin-1")
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
    """Process direct text input and convert to RawContent."""
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
    """Create a manual module from file upload or text content."""
    # Validation
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
            text_content = module_data.text_content or ""
            raw_content = await process_text_content(text_content, module_data.name)

        # Process through existing content pipeline
        if raw_content.content_type not in CONTENT_PROCESSORS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {raw_content.content_type}",
            )

        processor = CONTENT_PROCESSORS[raw_content.content_type]
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

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("manual_module_creation_failed", module_name=module_data.name, error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to process content. Please try again."
        )
```

**Key Points:**

- Immediate content processing with preview generation
- File validation (PDF only, 5MB max)
- Integration with existing content processing pipeline
- Proper error handling and logging

#### Step 3: Upload Endpoint and Mixed Orchestration

**File:** `backend/src/quiz/router.py`

Add to imports:

```python
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from .manual import create_manual_module
from .schemas import ManualModuleCreate, ManualModuleResponse, QuizCreate
from .orchestrator import (
    orchestrate_mixed_content_extraction,
    orchestrate_quiz_content_extraction,
    # ... existing imports
)
```

Add upload endpoint:

```python
@router.post("/manual-modules/upload", response_model=ManualModuleResponse)
async def upload_manual_module(
    current_user: CurrentUser,
    name: str = Form(..., description="Module name"),
    text_content: str | None = Form(None, description="Direct text content"),
    file: UploadFile | None = File(None, description="PDF file upload"),
) -> ManualModuleResponse:
    """
    Create a manual module from file upload or text content with immediate processing.

    This endpoint accepts either a PDF file upload OR direct text content to create
    a manual module. The content is immediately processed and a preview is returned.
    """
    logger.info(
        "manual_module_upload_initiated",
        user_id=str(current_user.id),
        module_name=name,
        has_file=file is not None,
        has_text=text_content is not None,
    )

    try:
        module_data = ManualModuleCreate(name=name, text_content=text_content)
        result = await create_manual_module(module_data, file)

        logger.info(
            "manual_module_upload_completed",
            user_id=str(current_user.id),
            module_id=result.module_id,
            module_name=result.name,
            word_count=result.word_count,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "manual_module_upload_failed",
            user_id=str(current_user.id),
            module_name=name,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to process manual module. Please try again."
        )
```

Update quiz creation logic:

```python
# In the existing create_new_quiz function, add:
# Check if quiz has manual modules to determine which orchestrator to use
has_manual_modules = False
for module_data in quiz_data.selected_modules.values():
    if hasattr(module_data, "source_type"):
        if module_data.source_type == "manual":
            has_manual_modules = True
            break
    elif (
        isinstance(module_data, dict)
        and module_data.get("source_type") == "manual"
    ):
        has_manual_modules = True
        break

if has_manual_modules:
    # Use mixed content extraction for quizzes with manual modules
    background_tasks.add_task(
        safe_background_orchestration,
        orchestrate_mixed_content_extraction,
        "mixed_content_extraction",
        quiz.id,
        quiz.id,
        quiz_data.canvas_course_id,
        canvas_token,
        extract_content_for_modules,
        get_content_summary,
    )
else:
    # Use Canvas-only content extraction for traditional quizzes
    background_tasks.add_task(
        safe_background_orchestration,
        orchestrate_quiz_content_extraction,
        # ... existing parameters
    )
```

#### Step 4: Mixed Content Orchestration

**File:** `backend/src/quiz/orchestrator.py`

Add mixed content extraction function:

```python
async def _execute_mixed_content_extraction_workflow(
    quiz_id: UUID,
    canvas_course_id: int,
    canvas_token: str,
    selected_modules: dict[str, dict[str, Any]],
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> tuple[dict[str, Any] | None, str]:
    """
    Execute content extraction workflow for mixed Canvas and manual modules.

    This function handles both Canvas modules (using the injected content extractor)
    and manual modules (using pre-stored content from quiz creation).
    """
    logger.info(
        "mixed_content_extraction_started",
        quiz_id=str(quiz_id),
        canvas_course_id=canvas_course_id,
        total_modules=len(selected_modules),
    )

    try:
        all_extracted_content = {}
        canvas_modules = []
        manual_modules = []

        # Separate Canvas and manual modules
        for module_id, module_data in selected_modules.items():
            source_type = module_data.get("source_type", "canvas")
            if source_type == "canvas":
                canvas_modules.append(int(module_id))
            elif source_type == "manual":
                manual_modules.append((module_id, module_data))

        # Extract Canvas content if there are Canvas modules
        if canvas_modules:
            logger.info("extracting_canvas_content", canvas_module_ids=canvas_modules)
            canvas_content = await content_extractor(
                canvas_token, canvas_course_id, canvas_modules
            )
            all_extracted_content.update(canvas_content)

        # Add manual content if there are manual modules
        if manual_modules:
            logger.info("processing_manual_content", manual_module_count=len(manual_modules))
            for module_id, module_data in manual_modules:
                # Manual modules already have processed content from quiz creation
                all_extracted_content[module_id] = {
                    "name": module_data["name"],
                    "source_type": "manual",
                    "content": module_data.get("content", ""),
                    "word_count": module_data.get("word_count", 0),
                    "processing_metadata": module_data.get("processing_metadata", {}),
                    "content_type": module_data.get("content_type", "text"),
                }

        # Generate content summary for all modules
        content_summary = content_summarizer(all_extracted_content)

        logger.info(
            "mixed_content_extraction_completed",
            modules_processed=content_summary["modules_processed"],
            total_word_count=content_summary["total_word_count"],
            canvas_modules_processed=len(canvas_modules),
            manual_modules_processed=len(manual_modules),
        )

        # Check if meaningful content was extracted
        total_word_count = content_summary.get("total_word_count", 0)
        total_pages = content_summary.get("total_pages", 0)

        if total_word_count == 0 or total_pages == 0:
            return None, "no_content"
        else:
            return all_extracted_content, "completed"

    except Exception as e:
        logger.error(
            "mixed_content_extraction_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        return None, "failed"

@timeout_operation(OPERATION_TIMEOUTS["content_extraction"])
async def orchestrate_mixed_content_extraction(
    quiz_id: UUID,
    canvas_course_id: int,
    canvas_token: str,
    content_extractor: ContentExtractorFunc,
    content_summarizer: ContentSummaryFunc,
) -> None:
    """Orchestrate content extraction for quizzes with mixed Canvas and manual modules."""
    # ... implementation follows same pattern as existing orchestrators
    # but calls _execute_mixed_content_extraction_workflow
```

#### Step 5: Frontend Dialog Components

**File:** `frontend/src/components/QuizCreation/FileUploadZone.tsx`

```typescript
import { Box, Button, FileUpload, Text, VStack } from "@chakra-ui/react";
import { memo, useCallback, useState } from "react";
import { HiUpload } from "react-icons/hi";

interface FileUploadZoneProps {
  onFileSelect: (file: File | null) => void;
  isLoading?: boolean;
  error?: string | null;
}

export const FileUploadZone = memo(function FileUploadZone({
  onFileSelect,
  isLoading = false,
  error,
}: FileUploadZoneProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const validateFile = useCallback((file: File): string | null => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF files are supported";
    }

    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      return "File size must be less than 5MB";
    }

    return null;
  }, []);

  const handleFileChange = useCallback(
    (details: { acceptedFiles: File[] }) => {
      const file = details.acceptedFiles[0];

      if (!file) {
        setSelectedFile(null);
        onFileSelect(null);
        return;
      }

      const validationError = validateFile(file);
      if (validationError) {
        setSelectedFile(null);
        onFileSelect(null);
        return;
      }

      setSelectedFile(file);
      onFileSelect(file);
    },
    [onFileSelect, validateFile]
  );

  return (
    <VStack gap={4} align="stretch">
      <Text fontSize="lg" fontWeight="semibold">
        Upload PDF File
      </Text>

      <FileUpload.Root
        accept="application/pdf,.pdf"
        maxFiles={1}
        maxFileSize={5 * 1024 * 1024}
        onFileChange={handleFileChange}
        disabled={isLoading}
      >
        <FileUpload.HiddenInput />

        <FileUpload.Trigger asChild>
          <Box
            p={8}
            border="2px dashed"
            borderColor={error ? "red.300" : "gray.300"}
            borderRadius="lg"
            bg={error ? "red.50" : "gray.50"}
            cursor={isLoading ? "not-allowed" : "pointer"}
            opacity={isLoading ? 0.6 : 1}
            transition="all 0.2s"
            _hover={
              !isLoading
                ? {
                    borderColor: "blue.400",
                    bg: "blue.50",
                  }
                : {}
            }
            textAlign="center"
          >
            <VStack gap={3}>
              <Box fontSize="3xl" color="gray.400">
                📄
              </Box>
              <VStack gap={1}>
                <Text fontSize="md" fontWeight="medium" color="gray.700">
                  {isLoading
                    ? "Processing..."
                    : "Click to upload or drag and drop"}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  PDF files only, up to 5MB
                </Text>
              </VStack>
              <Button variant="outline" size="sm" disabled={isLoading}>
                <HiUpload /> Choose File
              </Button>
            </VStack>
          </Box>
        </FileUpload.Trigger>
      </FileUpload.Root>

      {error && (
        <Box
          p={3}
          bg="red.50"
          border="1px solid"
          borderColor="red.200"
          borderRadius="md"
        >
          <Text fontSize="sm" color="red.600">
            {error}
          </Text>
        </Box>
      )}

      {selectedFile && (
        <Box
          p={3}
          bg="green.50"
          border="1px solid"
          borderColor="green.200"
          borderRadius="md"
        >
          <Text fontSize="sm" color="green.700">
            Selected: {selectedFile.name} (
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
          </Text>
        </Box>
      )}
    </VStack>
  );
});
```

**File:** `frontend/src/components/QuizCreation/ManualModuleDialog.tsx`

```typescript
import { Button, HStack, Input, Text, VStack } from "@chakra-ui/react";
import { memo, useState, useCallback } from "react";

import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useCustomToast } from "@/hooks/common";
import { ContentPreview } from "./ContentPreview";
import { FileUploadZone } from "./FileUploadZone";
import { TextContentEditor } from "./TextContentEditor";

type DialogStep = "input-method" | "file-upload" | "text-input" | "preview";
type InputMethod = "file" | "text";

interface ManualModuleDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onModuleCreated: (moduleData: {
    moduleId: string;
    name: string;
    contentPreview: string;
    wordCount: number;
  }) => void;
}

export const ManualModuleDialog = memo(function ManualModuleDialog({
  isOpen,
  onOpenChange,
  onModuleCreated,
}: ManualModuleDialogProps) {
  // State management
  const [currentStep, setCurrentStep] = useState<DialogStep>("input-method");
  const [inputMethod, setInputMethod] = useState<InputMethod | null>(null);
  const [moduleName, setModuleName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [textContent, setTextContent] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [previewData, setPreviewData] = useState<{
    moduleId: string;
    contentPreview: string;
    wordCount: number;
    metadata?: Record<string, any>;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toast = useCustomToast();

  // Reset dialog state when it closes
  const handleOpenChange = useCallback(
    (open: boolean) => {
      if (!open) {
        setCurrentStep("input-method");
        setInputMethod(null);
        setModuleName("");
        setSelectedFile(null);
        setTextContent("");
        setIsProcessing(false);
        setPreviewData(null);
        setError(null);
      }
      onOpenChange(open);
    },
    [onOpenChange]
  );

  // Process content and move to preview
  const handleProcessContent = useCallback(async () => {
    if (!moduleName.trim()) {
      setError("Module name is required");
      return;
    }

    if (inputMethod === "file" && !selectedFile) {
      setError("Please select a PDF file");
      return;
    }

    if (inputMethod === "text" && !textContent.trim()) {
      setError("Please enter some text content");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("name", moduleName.trim());

      if (inputMethod === "file" && selectedFile) {
        formData.append("file", selectedFile);
      } else if (inputMethod === "text") {
        formData.append("text_content", textContent.trim());
      }

      const response = await fetch("/api/v1/quiz/manual-modules/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const result = await response.json();

      setPreviewData({
        moduleId: result.module_id,
        contentPreview: result.content_preview,
        wordCount: result.word_count,
        metadata: result.processing_metadata,
      });

      setCurrentStep("preview");
      toast.success("Content processed successfully!");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to process content";
      setError(errorMessage);
      toast.error("Failed to process content", errorMessage);
    } finally {
      setIsProcessing(false);
    }
  }, [moduleName, inputMethod, selectedFile, textContent, toast]);

  // Multi-step workflow implementation
  // ... (rest of the component implementation)
});
```

#### Step 6: Module Selection Integration

**File:** `frontend/src/components/QuizCreation/ModuleSelectionStep.tsx`

```typescript
// Update interface to support manual modules
interface ManualModule {
  id: string
  name: string
  contentPreview: string
  wordCount: number
  isManual: true
}

interface ModuleSelectionStepProps {
  courseId: number
  selectedModules: { [id: string]: string }
  manualModules?: ManualModule[]
  onModulesSelect: (modules: { [id: string]: string }) => void
  onManualModuleAdd?: (module: ManualModule) => void
}

export function ModuleSelectionStep({
  courseId,
  selectedModules,
  manualModules = [],
  onModulesSelect,
  onManualModuleAdd,
}: ModuleSelectionStepProps) {
  const [isManualDialogOpen, setIsManualDialogOpen] = useState(false)

  // Updated module toggle handler
  const handleModuleToggle = useCallback(
    (module: Module | ManualModule, checked: boolean) => {
      const newSelectedModules = { ...selectedModules }
      const moduleId = String(module.id)

      if (checked) {
        newSelectedModules[moduleId] = module.name
      } else {
        delete newSelectedModules[moduleId]
      }

      onModulesSelect(newSelectedModules)
    },
    [selectedModules, onModulesSelect],
  )

  // Handle manual module creation
  const handleManualModuleCreated = useCallback(
    (moduleData: {
      moduleId: string
      name: string
      contentPreview: string
      wordCount: number
    }) => {
      const manualModule: ManualModule = {
        id: moduleData.moduleId,
        name: moduleData.name,
        contentPreview: moduleData.contentPreview,
        wordCount: moduleData.wordCount,
        isManual: true,
      }

      // Add the manual module to the list
      onManualModuleAdd?.(manualModule)

      // Automatically select the new manual module
      const newSelectedModules = { ...selectedModules }
      newSelectedModules[moduleData.moduleId] = moduleData.name
      onModulesSelect(newSelectedModules)
    },
    [selectedModules, onModulesSelect, onManualModuleAdd],
  )

  return (
    <VStack gap={4} align="stretch">
      {/* Manual Module Creation Card */}
      <Card.Root
        variant="outline"
        cursor="pointer"
        _hover={{ borderColor: "green.300" }}
        borderColor="green.200"
        bg="green.50"
        onClick={() => setIsManualDialogOpen(true)}
      >
        <Card.Body p={4}>
          <HStack gap={3}>
            <Box fontSize="xl">➕</Box>
            <Box flex={1}>
              <Text fontWeight="medium" fontSize="md" color="green.700">
                Add Manual Module
              </Text>
              <Text fontSize="sm" color="green.600" mt={1}>
                Upload a PDF file or paste text content to create a custom module
              </Text>
            </Box>
            <Button size="sm" colorScheme="green" variant="outline">
              Add Module
            </Button>
          </HStack>
        </Card.Body>
      </Card.Root>

      <VStack gap={3} align="stretch">
        {/* Canvas Modules */}
        {modules.map((module) => (
          // ... existing Canvas module rendering
        ))}

        {/* Manual Modules */}
        {manualModules.map((module) => (
          <Card.Root key={module.id} /* ... manual module styling */>
            <Card.Body p={4}>
              <HStack gap={3}>
                <Checkbox
                  checked={!!selectedModules[module.id]}
                  inputProps={{
                    onChange: (e) => handleModuleToggle(module, e.target.checked),
                  }}
                />
                <Box flex={1}>
                  <HStack gap={2} align="center">
                    <Text fontWeight="medium">{module.name}</Text>
                    <Box
                      px={2} py={1} bg="purple.100" color="purple.800"
                      fontSize="xs" fontWeight="medium" borderRadius="md"
                    >
                      Manual
                    </Box>
                  </HStack>
                  <Text fontSize="sm" color="gray.600">
                    {module.wordCount.toLocaleString()} words
                  </Text>
                </Box>
              </HStack>
            </Card.Body>
          </Card.Root>
        ))}
      </VStack>

      {/* Manual Module Dialog */}
      <ManualModuleDialog
        isOpen={isManualDialogOpen}
        onOpenChange={setIsManualDialogOpen}
        onModuleCreated={handleManualModuleCreated}
      />
    </VStack>
  )
}
```

### 4.3 Data Models & Schemas

#### Backend Schemas

- **ManualModuleCreate**: Input validation for file upload/text
- **ManualModuleResponse**: Processed content with preview
- **ModuleSelection**: Extended with `source_type` field
- **QuizCreate**: Updated validation for mixed modules

#### Frontend Interfaces

- **ManualModule**: Client-side manual module representation
- **QuizFormData**: Extended with `manualModules` array
- **Dialog Props**: Type-safe component interfaces

### 4.4 Configuration

#### Backend Configuration

```python
# In manual.py
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB file size limit

# File types accepted
ACCEPTED_FILE_TYPES = [".pdf"]

# Content processing timeout
PROCESSING_TIMEOUT = 30  # seconds
```

#### Frontend Configuration

```typescript
// API endpoint configuration
const API_BASE_URL = "/api/v1";
const MANUAL_MODULE_ENDPOINT = `${API_BASE_URL}/quiz/manual-modules/upload`;

// File validation
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_FILE_TYPES = ["application/pdf", ".pdf"];
```

## 5. Testing Strategy

### 5.1 Unit Tests

#### Backend Tests

```python
# test_manual_module.py
async def test_create_manual_module_with_text():
    """Test manual module creation with text content."""
    module_data = ManualModuleCreate(
        name="Test Module",
        text_content="This is test content for the module."
    )

    result = await create_manual_module(module_data)

    assert result.name == "Test Module"
    assert result.word_count > 0
    assert result.module_id.startswith("manual_")
    assert "This is test content" in result.content_preview

async def test_file_upload_validation():
    """Test file upload validation."""
    # Test file size limit
    large_file = create_large_pdf_file(6 * 1024 * 1024)  # 6MB

    with pytest.raises(HTTPException) as exc_info:
        await process_uploaded_file(large_file)

    assert exc_info.value.status_code == 400
    assert "exceeds maximum limit" in exc_info.value.detail

def test_quiz_creation_with_mixed_modules():
    """Test quiz creation with both Canvas and manual modules."""
    quiz_data = QuizCreate(
        canvas_course_id=123,
        canvas_course_name="Test Course",
        selected_modules={
            "456": {
                "name": "Canvas Module",
                "source_type": "canvas",
                "question_batches": [{"question_type": "multiple_choice", "count": 5}]
            },
            "manual_abc123": {
                "name": "Manual Module",
                "source_type": "manual",
                "content": "Test content",
                "word_count": 100,
                "question_batches": [{"question_type": "true_false", "count": 3}]
            }
        },
        title="Mixed Quiz"
    )

    # Should validate successfully
    assert quiz_data.selected_modules["456"]["source_type"] == "canvas"
    assert quiz_data.selected_modules["manual_abc123"]["source_type"] == "manual"
```

#### Frontend Tests

```typescript
// ManualModuleDialog.test.tsx
describe("ManualModuleDialog", () => {
  it("should handle file upload workflow", async () => {
    const mockOnModuleCreated = jest.fn();

    render(
      <ManualModuleDialog
        isOpen={true}
        onOpenChange={() => {}}
        onModuleCreated={mockOnModuleCreated}
      />
    );

    // Test multi-step workflow
    fireEvent.click(screen.getByText("Upload PDF File"));
    fireEvent.change(screen.getByLabelText("Module Name"), {
      target: { value: "Test Module" },
    });

    // Mock file upload
    const file = new File(["test content"], "test.pdf", {
      type: "application/pdf",
    });
    const fileInput = screen.getByRole("button", { name: /choose file/i });
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Mock API response
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          module_id: "manual_test123",
          name: "Test Module",
          content_preview: "Test content preview...",
          word_count: 50,
        }),
    });

    fireEvent.click(screen.getByText("Process Content"));

    await waitFor(() => {
      expect(mockOnModuleCreated).toHaveBeenCalledWith({
        moduleId: "manual_test123",
        name: "Test Module",
        contentPreview: "Test content preview...",
        wordCount: 50,
      });
    });
  });
});
```

### 5.2 Integration Tests

#### API Integration

```python
# test_integration.py
async def test_manual_module_end_to_end(client: TestClient):
    """Test complete manual module workflow."""
    # Create manual module
    with open("test_files/sample.pdf", "rb") as f:
        response = client.post(
            "/api/v1/quiz/manual-modules/upload",
            data={"name": "Integration Test Module"},
            files={"file": ("sample.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    manual_module = response.json()

    # Create quiz with manual module
    quiz_data = {
        "canvas_course_id": 123,
        "canvas_course_name": "Test Course",
        "selected_modules": {
            manual_module["module_id"]: {
                "name": manual_module["name"],
                "source_type": "manual",
                "content": "Full content here",
                "word_count": manual_module["word_count"],
                "question_batches": [
                    {"question_type": "multiple_choice", "count": 5}
                ]
            }
        },
        "title": "Integration Test Quiz"
    }

    response = client.post("/api/v1/quiz/", json=quiz_data)
    assert response.status_code == 200

    quiz = response.json()
    assert quiz["selected_modules"][manual_module["module_id"]]["source_type"] == "manual"
```

### 5.3 Manual Testing Steps

1. **File Upload Testing**

   - Upload valid PDF (under 5MB) → Should process successfully
   - Upload invalid file type → Should show error
   - Upload oversized file → Should show size error
   - Upload corrupted PDF → Should show processing error

2. **Text Content Testing**

   - Enter valid text content → Should process successfully
   - Enter empty text → Should show validation error
   - Enter very long text → Should process and show word count

3. **Mixed Module Testing**
   - Create quiz with only Canvas modules → Should use Canvas orchestrator
   - Create quiz with only manual modules → Should use mixed orchestrator
   - Create quiz with both types → Should use mixed orchestrator
   - Verify question generation works for all module types

## 6. Deployment Instructions

### 6.1 Backend Deployment

```bash
# 1. Install dependencies (if not already present)
cd backend
uv add python-multipart

# 2. Run database migrations (if any schema changes)
alembic upgrade head

# 3. Run tests
uv run pytest tests/quiz/test_manual.py -v

# 4. Lint and format
bash scripts/lint.sh

# 5. Start backend
docker compose up -d backend
```

### 6.2 Frontend Deployment

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Generate API client from updated backend
npm run generate-client

# 3. Run tests
npm test -- --testPathPattern=ManualModule

# 4. Build for production
npm run build

# 5. Start frontend
docker compose up -d frontend
```

### 6.3 Full Stack Deployment

```bash
# Start entire stack
docker compose up -d

# Verify services
docker compose ps
docker compose logs backend | grep "manual_module"
docker compose logs frontend | grep "ManualModule"
```

## 7. Monitoring & Maintenance

### 7.1 Key Metrics

- **File Upload Success Rate**: Track successful vs failed uploads
- **Content Processing Time**: Monitor processing latency
- **Manual Module Usage**: Track adoption of manual modules
- **Mixed Quiz Success Rate**: Monitor quiz creation with manual content

### 7.2 Log Entries to Monitor

#### Backend Logs

```python
# Success indicators
"manual_module_upload_completed"
"mixed_content_extraction_completed"

# Error indicators
"manual_module_creation_failed"
"mixed_content_extraction_failed"

# Performance indicators
"content_processing_time_seconds"
"file_upload_size_bytes"
```

#### Frontend Logs

```typescript
// Success indicators
"Manual module created successfully";
"Content processed successfully";

// Error indicators
"Failed to process content";
"File upload validation failed";
```

### 7.3 Common Issues & Troubleshooting

| Issue                             | Symptoms                                    | Solution                                          |
| --------------------------------- | ------------------------------------------- | ------------------------------------------------- |
| File upload fails                 | 413 Request Entity Too Large                | Check nginx/proxy max body size                   |
| PDF processing fails              | "Failed to process content" error           | Verify PDF is not password-protected or corrupted |
| Mixed orchestration not triggered | Canvas orchestrator used for manual modules | Check `source_type` field in `selected_modules`   |
| Manual modules not appearing      | Empty manual modules list                   | Verify `onManualModuleAdd` callback is connected  |

## 8. Security Considerations

### 8.1 File Upload Security

- **File Type Validation**: Only PDF files accepted, validated by extension and MIME type
- **File Size Limits**: 5MB maximum to prevent DoS attacks
- **Content Scanning**: PDF content is processed and sanitized before storage
- **No Persistent Storage**: Files are processed immediately and not stored permanently

### 8.2 Content Processing Security

- **Input Sanitization**: All text content is sanitized during processing
- **Processing Timeouts**: Content processing has timeout limits to prevent hanging
- **Resource Limits**: Processing is memory and CPU bounded

### 8.3 API Security

- **Authentication Required**: All endpoints require valid JWT token
- **User Ownership**: Users can only access their own manual modules
- **Rate Limiting**: File upload endpoints should be rate limited
- **CORS Configuration**: Proper CORS headers for file uploads

### 8.4 Data Privacy

- **No Content Persistence**: File content is not stored permanently
- **User Isolation**: Manual modules are user-scoped
- **Audit Logging**: All manual module operations are logged with user ID

## 9. Future Considerations

### 9.1 Known Limitations

- **File Types**: Currently only supports PDF files
- **Content Preview**: Only first 500 characters shown in preview
- **No Content Editing**: Manual modules cannot be edited after creation
- **No Bulk Upload**: Single file upload only

### 9.2 Potential Improvements

#### Short-term (Next Sprint)

- **Support for .docx files**: Add Word document processing
- **Content editing**: Allow users to modify manual module content
- **Bulk upload**: Support multiple file upload at once
- **Rich text preview**: Better formatting in content preview

#### Medium-term (Next Quarter)

- **OCR Support**: Process scanned PDFs with text extraction
- **Content templates**: Pre-built templates for common content types
- **Module sharing**: Share manual modules between users
- **Advanced processing**: Extract images, tables from documents

#### Long-term (Future Releases)

- **AI-powered enhancement**: Automatic content improvement suggestions
- **Multi-language support**: Content translation capabilities
- **Integration with external sources**: Google Drive, Dropbox integration
- **Advanced analytics**: Content quality scoring and recommendations

### 9.3 Scalability Considerations

- **File Processing**: Move to background job queue for large files
- **Content Storage**: Consider Redis/database for temporary content caching
- **CDN Integration**: Serve processed content through CDN
- **Microservice Split**: Separate manual module service from quiz service

---

## Appendix

### A. API Reference

#### POST /api/v1/quiz/manual-modules/upload

**Request:**

```
Content-Type: multipart/form-data

name: string (required) - Module name
text_content: string (optional) - Direct text content
file: File (optional) - PDF file upload
```

**Response:**

```json
{
  "module_id": "manual_abc12345",
  "name": "Module Name",
  "content_preview": "First 500 characters...",
  "word_count": 1250,
  "processing_metadata": {
    "processing_time_seconds": 1.2,
    "content_type": "pdf",
    "extracted_pages": 5
  }
}
```

### B. Error Codes

| Code | Description       | Resolution                          |
| ---- | ----------------- | ----------------------------------- |
| 400  | Invalid file type | Use PDF files only                  |
| 413  | File too large    | Reduce file size to under 5MB       |
| 422  | Missing content   | Provide either file or text content |
| 500  | Processing failed | Check file format and try again     |

### C. Browser Compatibility

- Chrome 90+: Full support
- Firefox 88+: Full support
- Safari 14+: Full support
- Edge 90+: Full support

---

_This document should be updated as the feature evolves. Last updated: January 1, 2025_
