# Plan: Remove LLM Settings from Quiz Creation

## Overview

This document outlines the plan to remove LLM (Language Model) settings from the quiz creation interface. Currently, users can choose between "Recommended Settings" and "Advanced Settings" for the AI model and temperature. This change will simplify the user experience by removing these options and relying on backend defaults.

## Rationale

- **Simplification**: Users don't need to understand AI model differences or temperature settings
- **Developer Control**: Model selection should be a backend decision based on performance and cost
- **Consistency**: All quizzes will use the same optimized settings
- **Future Flexibility**: Backend can still experiment with different models without UI changes

## Current State

### UI Flow
1. Step 1: Course Selection
2. Step 2: Module Selection
3. Step 3: Quiz Settings
   - Question Count field
   - LLM Settings section with two tabs:
     - Recommended Settings (fixed display of o3 model, temperature 1)
     - Advanced Settings (dropdown for model selection, slider for temperature)

### Backend Defaults
- Model: "o3"
- Temperature: 1.0

## Target State

### UI Flow
1. Step 1: Course Selection
2. Step 2: Module Selection
3. Step 3: Quiz Configuration (renamed)
   - Question Count field only
   - No LLM settings visible

### Backend Behavior
- Continues to use default values (o3, temperature 1.0)
- No changes to backend models or schemas
- Frontend simply doesn't send llm_model and llm_temperature values

## Files to Modify

### 1. QuizSettingsStep Component
**File**: `src/components/QuizCreation/QuizSettingsStep.tsx`
- Remove LLM Settings section (lines 85-233)
- Remove tab state and handlers
- Remove llmModel and llmTemperature from interface
- Remove unused imports

### 2. Create Quiz Route
**File**: `src/routes/_layout/create-quiz.tsx`
- Rename step from "Quiz Settings" to "Quiz Configuration"
- Remove llmModel and llmTemperature from QuizFormData interface
- Remove these fields from form data handling
- Update validation logic

### 3. Quiz Badges Component
**File**: `src/components/common/QuizBadges.tsx`
- Remove the purple badge that displays quiz.llm_model
- Adjust layout/spacing

### 4. Other Components
Search and update any other components that might display or reference:
- llm_model / llmModel
- llm_temperature / llmTemperature

## Testing Strategy

### Unit Tests
- Update tests for QuizSettingsStep to expect only question count
- Remove LLM-related test assertions
- Update create-quiz route tests

### Integration Tests
- Verify quiz creation works without LLM parameters
- Ensure backend uses defaults correctly

### E2E Tests
- Update Playwright tests to reflect new UI flow
- Remove any steps that interact with LLM settings

### Type Safety
- Run `npx tsc --noEmit` after each step
- Ensure no TypeScript errors

## Implementation Steps

1. **Document Plan** (this document)
   - Commit: "docs: add plan for removing LLM settings from quiz creation"

2. **Update QuizSettingsStep**
   - Simplify to show only question count
   - Update related tests
   - Commit: "refactor: simplify QuizSettingsStep by removing LLM settings"

3. **Update Create Quiz Route**
   - Rename step to "Quiz Configuration"
   - Remove LLM fields from interfaces and handlers
   - Update tests
   - Commit: "refactor: rename Quiz Settings to Quiz Configuration and remove LLM fields"

4. **Remove Model Badge**
   - Update QuizBadges component
   - Update tests
   - Commit: "refactor: remove LLM model badge from quiz displays"

5. **Clean Up Remaining References**
   - Search for any missed references
   - Update tests
   - Commit: "refactor: remove remaining LLM setting references"

6. **Final Testing**
   - Run full test suite
   - Manual testing of complete flow
   - Commit: "test: update tests for LLM settings removal"

## Rollback Plan

Each step is committed separately. If issues arise:
1. Identify the problematic commit
2. Use `git revert <commit-hash>` to undo specific changes
3. Or reset to a known good state with `git reset`

## Success Criteria

- [ ] Quiz creation flow works without LLM settings
- [ ] All tests pass
- [ ] No TypeScript errors
- [ ] Backend correctly uses default LLM settings
- [ ] UI is cleaner and simpler for users
- [ ] Model badge removed from all quiz displays
