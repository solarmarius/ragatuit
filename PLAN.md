# Implementation Plan: Add Language Selection to Quiz Creation

## Overview
This document outlines the comprehensive implementation plan for adding language selection (English/Norwegian) to the quiz creation process. The feature will allow users to select the language for question generation, affecting the LLM templates used during the AI-powered question generation process.

## Requirements Summary
- **Languages**: English (default) and Norwegian only
- **Scope**: Quiz-level language setting (affects all questions in a quiz)
- **UI Pattern**: Visual card-based selection in QuizSettingsStep
- **Storage**: Language field in Quiz model with English as default
- **Templates**: Separate Norwegian template files for question generation
- **Error Handling**: Missing language templates treated as standard LLM generation errors

## Architecture Impact
- **Backend**: Quiz model, schemas, template system, question generation pipeline
- **Frontend**: QuizSettingsStep UI, form handling, type definitions
- **Database**: New language field in quiz table
- **Templates**: New Norwegian template files

## Implementation Phases

### Phase 0: Documentation & Planning ✅
- [x] Create comprehensive PLAN.md document
- [x] Document all implementation steps and validation procedures
- [x] Establish testing and commit protocols

### Phase 1: Backend Model & Database Changes

#### 1.1 Update Quiz Model
**Files to modify:**
- `backend/src/quiz/models.py`

**Changes:**
- Add `QuizLanguage` enum with `ENGLISH` and `NORWEGIAN` values
- Add `language` field to Quiz model with default `ENGLISH`
- Add appropriate validation and constraints

#### 1.2 Update Schemas
**Files to modify:**
- `backend/src/quiz/schemas.py`

**Changes:**
- Add language field to `QuizCreate` schema
- Add language field to `QuizUpdate` schema
- Add language field to `QuizPublic` response schema
- Add language validation in request schemas

#### 1.3 Database Migration
**Manual step for user:**
```bash
cd backend
alembic revision --autogenerate -m "add language field to quiz"
```

#### 1.4 Validation & Testing
**Commands to run:**
```bash
# Backend tests
cd backend && source .venv/bin/activate && bash scripts/test.sh

# Backend linting
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Commit changes
git add . && git commit -m "feat: add language field to Quiz model and schemas"
```

### Phase 2: Backend Template System

#### 2.1 Create Norwegian Templates
**Files to create:**
- `backend/src/question/templates/files/default_multiple_choice_no.json`
- `backend/src/question/templates/files/enhanced_mcq_no.json`

**Template structure:**
- Copy existing English templates as base
- Add placeholder Norwegian content (user will edit with proper terminology)
- Set `language` field to `"no"`
- Update metadata and description

#### 2.2 Update Template Manager
**Files to modify:**
- `backend/src/question/templates/manager.py`

**Changes:**
- Add language parameter to `get_template()` method
- Implement language-aware template selection logic
- Add fallback handling (Norwegian → English if not found)
- Update error handling for missing templates

#### 2.3 Update Question Generation
**Files to modify:**
- `backend/src/question/services/generation_service.py`
- `backend/src/question/workflows/base.py`
- `backend/src/question/workflows/mcq_workflow.py`

**Changes:**
- Update generation services to accept and use language parameter
- Modify workflows to pass language to template selection
- Ensure language flows through entire generation pipeline

#### 2.4 Validation & Testing
**Commands to run:**
```bash
# Backend tests
cd backend && source .venv/bin/activate && bash scripts/test.sh

# Backend linting
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Commit changes
git add . && git commit -m "feat: add Norwegian templates and language-aware template selection"
```

### Phase 3: Backend API Changes

#### 3.1 Update Quiz Endpoints
**Files to modify:**
- `backend/src/quiz/router.py`
- `backend/src/quiz/service.py`

**Changes:**
- Update quiz creation endpoint to accept language parameter
- Ensure language is properly validated and stored
- Update quiz response to include language field

#### 3.2 Update Question Generation Flow
**Files to modify:**
- `backend/src/quiz/orchestrator.py`
- `backend/src/quiz/service.py`

**Changes:**
- Modify question generation service to use quiz language
- Update orchestrator to pass language to generation services
- Add error handling for missing language templates

#### 3.3 Validation & Testing
**Commands to run:**
```bash
# Backend tests
cd backend && source .venv/bin/activate && bash scripts/test.sh

# Backend linting
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Commit changes
git add . && git commit -m "feat: update API endpoints to support language parameter"
```

### Phase 4: Frontend UI Changes

#### 4.1 Update QuizSettingsStep Component
**Files to modify:**
- `frontend/src/components/QuizCreation/QuizSettingsStep.tsx`

**Changes:**
- Add language selection after question count field
- Implement card-based visual selection (English/Norwegian)
- Add proper form validation and state management
- Follow existing UI patterns from course/module selection

#### 4.2 Update Form Handling
**Files to modify:**
- `frontend/src/components/QuizCreation/QuizSettingsStep.tsx`

**Changes:**
- Add language field to quiz creation form data
- Update form validation to include language
- Update API calls to include language parameter

#### 4.3 Update Types and Constants
**Files to modify:**
- `frontend/src/types/index.ts`
- `frontend/src/lib/constants/index.ts`

**Changes:**
- Add language enum/constants to frontend
- Update quiz types to include language field
- Add language to API client types (after regeneration)

#### 4.4 Regenerate API Client
**Manual step for user:**
```bash
npm run generate-client
```

#### 4.5 Validation & Testing
**Commands to run:**
```bash
# Frontend type checking
cd frontend && npx tsc --noEmit

# Commit changes
git add . && git commit -m "feat: add language selection to QuizSettingsStep"
```

### Phase 5: Integration & Testing

#### 5.1 Backend Testing
**Files to modify:**
- `backend/tests/quiz/test_quiz_service.py`
- `backend/tests/question/test_question_service.py`

**Changes:**
- Add unit tests for language field validation
- Add tests for language-aware template selection
- Add tests for Norwegian template loading
- Add integration tests for quiz creation with language

#### 5.2 Frontend Testing
**Files to modify:**
- Frontend test files as needed

**Changes:**
- Add tests for language selection UI
- Add tests for form validation with language
- Update existing quiz creation tests

#### 5.3 End-to-End Testing
**Testing scenarios:**
- Test complete quiz creation flow with both languages
- Test question generation with Norwegian templates
- Test error handling for missing templates

#### 5.4 Final Validation & Testing
**Commands to run:**
```bash
# Full backend test suite
cd backend && source .venv/bin/activate && bash scripts/test.sh

# Backend linting
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Frontend type checking
cd frontend && npx tsc --noEmit

# Commit final changes
git add . && git commit -m "feat: add comprehensive tests for language selection feature"
```

## Key Implementation Details

### Language Enum Definition
```python
class QuizLanguage(str, Enum):
    ENGLISH = "en"
    NORWEGIAN = "no"
```

### Template Naming Convention
- English: `default_multiple_choice.json`, `enhanced_mcq.json`
- Norwegian: `default_multiple_choice_no.json`, `enhanced_mcq_no.json`

### Template Selection Logic
1. Try to load template with language suffix (e.g., `default_multiple_choice_no.json`)
2. If not found, fallback to English template
3. If still not found, raise appropriate error

### Error Handling
- Missing language templates: Set quiz status to `FAILED` with appropriate failure reason
- Invalid language values: Validation error in API layer
- Template loading errors: Standard LLM generation error handling

## Manual Steps for User

1. **After Phase 1**: Generate Alembic migration
   ```bash
   cd backend
   alembic revision --autogenerate -m "add language field to quiz"
   ```

2. **After Phase 2.1**: Edit Norwegian template files with proper terminology
   - Review and update Norwegian text in template files
   - Ensure educational terminology is appropriate

3. **After Phase 3**: Regenerate frontend API client
   ```bash
   cd frontend
   npm run generate-client
   ```

## Testing Protocol

### After Each Phase:
1. Run appropriate tests (backend/frontend)
2. Run linting and type checking
3. Commit changes with descriptive messages

### Commands Reference:
```bash
# Backend
cd backend && source .venv/bin/activate && bash scripts/test.sh
cd backend && source .venv/bin/activate && bash scripts/lint.sh

# Frontend
cd frontend && npx tsc --noEmit

# Commit
git add . && git commit -m "descriptive commit message"
```

## Success Criteria

✅ **Phase 0**: Plan document created and approved
✅ **Phase 1**: Quiz model updated with language field, migration ready
✅ **Phase 2**: Norwegian templates created and template system updated
✅ **Phase 3**: API endpoints support language parameter
✅ **Phase 4**: Frontend UI includes language selection
✅ **Phase 5**: All tests pass and feature works end-to-end

## Risk Mitigation

- **Template Loading**: Fallback mechanism ensures English templates are used if Norwegian templates fail
- **Database Migration**: User handles migration manually to avoid deployment issues
- **Validation**: Comprehensive testing at each phase ensures stability
- **Type Safety**: TypeScript ensures frontend type safety after API client regeneration

This plan ensures a systematic, tested, and validated implementation of the language selection feature while maintaining code quality and system stability.

## Post-Implementation Notes

### Implementation Highlights

1. **QuizLanguage Enum Placement**: Initially placed in `quiz/schemas.py`, but moved to `question/types/base.py` to resolve circular import issues when used in `GenerationParameters`.

2. **Frontend Type Safety**: Used string literal types (`"en" | "no"`) from auto-generated API client rather than enums to maintain consistency with backend.

3. **Template Naming Convention**: Successfully implemented with `_no` suffix for Norwegian templates (e.g., `default_multiple_choice_no.json`).

4. **UI Implementation**: Card-based selection pattern matches existing course/module selection for consistency.

5. **Testing Results**:
   - Backend: All 202 tests passing
   - Frontend: All 175 tests passing
   - TypeScript validation: No errors

### Key Technical Decisions

- **Language Flow**: Quiz → Orchestrator → Generation Service → Template Manager
- **Default Language**: English ("en") set at multiple levels for robustness
- **Fallback Strategy**: Norwegian templates fallback to English if not found
- **Type Imports**: Used `type` imports in frontend to avoid runtime issues

### Future Extensibility

The implementation is designed to easily support additional languages:
1. Add new language to `QuizLanguage` enum
2. Create new template files with appropriate suffix
3. Add language option to frontend constants
4. Update UI language options array

The architecture supports this without structural changes.
