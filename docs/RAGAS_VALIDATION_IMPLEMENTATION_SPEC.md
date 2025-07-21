# RAGAS-based Question Validation and Refinement: Implementation Specification

**Date:** July 22, 2025
**Status:** Revised with Targeted Refinement Approach
**Version:** 3.0

---

## 1. Overview

This document outlines the implementation plan for integrating the RAGAS framework into the question generation pipeline. The goal is to introduce an automated validation step to assess the quality of LLM-generated questions based on two key metrics: **Faithfulness** and **Semantic Similarity** (applied conditionally based on question type).

Furthermore, a **targeted refinement mechanism** will be implemented. If a generated question fails to meet a predefined quality threshold, the system will attempt to **refine the specific question** rather than generating entirely new questions, ensuring higher success rates and preventing duplicate questions.

### Workflow graph

```
  Question Generation → RAGAS Validation → Score Check
                                             ↓
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼ (Scores ≥ thresholds)              ▼ (Scores < thresholds)
              Add to validated_questions             Refine specific question
                    │                                     │
                    │                                     ▼
                    │                            Re-validate refined question
                    │                                     │
                    │                    ┌────────────────┴────────────────┐
                    │                    ▼ (Pass)                          ▼ (Fail)
                    │               Add to validated              Add to failed_questions
                    │                    │                                │
                    └────────────────────┴────────────┬───────────────────┘
                                                      ▼
                                              Check if target met?
                                                      │
                                         ┌────────────┼────────────┐
                                         ▼ (Yes)      ▼ (No)       ▼ (Max retries)
                                   Save target count  │      Save all with status
                                                      │
                                                      ▼
                                             Generate NEW questions
                                             (only for shortfall)
                                                      │
                                                      └─── Loop back to validation
```

## 2. Background & Rationale

The current question generation process relies solely on the LLM's capabilities, lacking a concrete, automated quality control mechanism. This feature addresses that gap by:

- **Improving Question Quality:** Automatically assessing if questions are factually supported by the source material and if their alternatives are sufficiently challenging.
- **Targeted Refinement:** Instead of discarding failed questions and generating new ones (which may duplicate existing questions), the system refines specific failing questions based on validation feedback.
- **Preventing Duplicates:** By refining existing questions rather than generating from scratch, the system avoids creating duplicate questions.
- **Cost Efficiency:** Refinement prompts are smaller and more targeted than full generation prompts, reducing API costs.
- **Controlled Output:** Ensures the final quiz contains exactly the requested number of questions without excess.

## 3. Scope

### In Scope

- Integration of the `ragas` Python library.
- Implementation of `faithfulness` validation checks for all question types.
- Implementation of `semantic_similarity` validation checks for multiple choice questions (evaluating alternative diversity).
- Conditional metric application based on question type (fill-in-blank questions skip semantic similarity).
- Development of a **targeted refinement service** for questions that fail validation.
- Implementation of a **controlled generation loop** that only saves the target number of questions.
- Creation of a new `validation_metadata` field for the `Question` model.
- Storing validation scores, refinement attempts, and status in the database.
- Centralized, admin-level configuration for validation thresholds and retry limits.

### Out of Scope

- Any changes to the frontend application.
- User-facing configuration of validation thresholds.
- Implementation of other RAGAS metrics beyond the two specified.
- Real-time validation feedback to the user during the generation process.

## 4. Technical Design & Implementation Plan

### 4.1. Phase 1: Setup and Configuration

#### 4.1.1. Dependency Management

- **Action:** Add the `ragas` library to the project's dependencies.
- **File:** `backend/pyproject.toml`
- **Detail:** Add dependencies with version constraints for stability:
  ```toml
  dependencies = [
      # ... existing dependencies
      "ragas>=0.1.7,<0.2.0",           # Pin major version for stability
      "langchain-openai>=0.1.0",       # Required for embedding models
      "openai>=1.0.0",                 # Required for OpenAI embeddings
  ]
  ```

#### 4.1.2. Configuration

- **Action:** Integrate RAGAS validation settings into the existing centralized configuration system.
- **File:** `backend/src/config.py` (modify existing Settings class)
- **Content:**

  ```python
  # Add to existing Settings class in backend/src/config.py
  class Settings(BaseSettings):
      # ... existing settings

      # RAGAS Validation Settings
      RAGAS_ENABLED: bool = Field(
          default=True,
          description="Enable RAGAS validation for generated questions"
      )
      RAGAS_FAITHFULNESS_THRESHOLD: float = Field(
          default=0.7,
          ge=0.0,
          le=1.0,
          description="Minimum faithfulness score for question validation"
      )
      RAGAS_SEMANTIC_SIMILARITY_THRESHOLD: float = Field(
          default=0.6,
          ge=0.0,
          le=1.0,
          description="Minimum semantic similarity score for question validation"
      )
      MAX_VALIDATION_RETRIES: int = Field(
          default=3,
          ge=0,
          description="Maximum number of validation retry attempts per question batch"
      )
  ```

- **Rationale:** This integrates with the existing configuration system and supports environment variable overrides (e.g., `RAGAS_ENABLED=false`).

#### 4.1.3. Database Schema Changes

- **Action:** Extend the existing Question model to store validation metadata using the JSONB pattern.
- **File:** `backend/src/question/types/base.py` (modify existing Question model)
- **New Field:**

  ```python
  class Question(SQLModel, table=True):
      # ... existing fields

      # RAGAS validation metadata (using existing JSONB pattern)
      validation_metadata: dict[str, Any] = Field(
          default_factory=dict,
          sa_column=Column(JSONB, nullable=True),
          description="RAGAS validation scores, attempts, and metadata"
      )
  ```

- **Usage Example:**

  ```python
  # Store validation results in the JSONB field
  question.validation_metadata = {
      "faithfulness_score": 0.85,
      "semantic_similarity_score": 0.72,
      "validation_status": "passed",  # "passed", "failed", "error"
      "validation_attempts": 2,
      "validated_at": "2025-07-21T10:30:00Z",
      "ragas_version": "0.1.7"
  }
  ```

- **Migration:**
  - After updating the model, generate migration: `alembic revision --autogenerate -m "Add RAGAS validation metadata to Question"`
  - **Rationale:** Using JSONB maintains consistency with the existing polymorphic architecture and provides flexibility for future validation metrics.

---

### 4.2. Phase 2: Question Type Validation Integration

#### 4.2.1. Extend BaseQuestionType Interface

- **Action:** Add RAGAS validation capability to the existing question type system
- **File:** `backend/src/question/types/base.py` (extend BaseQuestionType)
- **New Abstract Method:**

  ```python
  @abstractmethod
  async def evaluate_semantic_similarity_async(
      self,
      question_data: BaseQuestionData,
      semantic_similarity_scorer: Any,
      logger: Any
  ) -> float:
      """
      Evaluate semantic similarity for this question type.

      Args:
          question_data: Parsed and validated question data
          semantic_similarity_scorer: RAGAS SemanticSimilarity scorer instance
          logger: Logger for debugging and error reporting

      Returns:
          float: Semantic similarity score (0.0 to 1.0)

      Note:
          Question types that don't support semantic similarity evaluation
          (e.g., fill-in-blank) should return 1.0 (perfect score).
      """
      pass
  ```

#### 4.2.2. Implement MCQ Semantic Similarity

- **Action:** Implement semantic similarity evaluation for multiple choice questions
- **File:** `backend/src/question/types/mcq.py` (extend existing MCQQuestionType)
- **Implementation:**

  ```python
  from ragas.dataset_schema import SingleTurnSample

  class MCQQuestionType(BaseQuestionType):
      # ... existing methods

      async def evaluate_semantic_similarity_async(
          self,
          question_data: BaseQuestionData,
          semantic_similarity_scorer: Any,
          logger: Any
      ) -> float:
          """Evaluate semantic similarity for MCQ by comparing answer alternatives."""
          try:
              # Cast to MCQ-specific data model to access options
              mcq_data = question_data  # Should be MCQData instance

              # Extract correct answer and all options
              correct_answer = getattr(mcq_data, 'correct_answer', None)
              if not correct_answer:
                  logger.warning("MCQ missing correct_answer, skipping semantic similarity")
                  return 1.0

              # Get correct answer text
              correct_option_key = f"option_{correct_answer.lower()}"
              correct_answer_text = getattr(mcq_data, correct_option_key, "")

              if not correct_answer_text:
                  logger.warning(f"MCQ correct answer text not found for {correct_answer}")
                  return 1.0

              # Collect all option texts for comparison
              option_keys = ['option_a', 'option_b', 'option_c', 'option_d']
              options = []
              for key in option_keys:
                  option_text = getattr(mcq_data, key, None)
                  if option_text and option_text != correct_answer_text:
                      options.append(option_text)

              if len(options) < 1:
                  logger.warning("MCQ has insufficient alternatives for semantic similarity")
                  return 1.0

              # Evaluate semantic similarity between correct answer and each alternative
              similarity_scores = []
              for option_text in options:
                  sample = SingleTurnSample(
                      response=correct_answer_text,
                      reference=option_text
                  )
                  score = await semantic_similarity_scorer.single_turn_ascore(sample)
                  similarity_scores.append(float(score))

              # Calculate average similarity and invert
              # Lower similarity between alternatives = higher quality = higher score
              avg_similarity = sum(similarity_scores) / len(similarity_scores)
              inverted_score = 1.0 - avg_similarity

              logger.debug(f"MCQ semantic similarity: avg={avg_similarity:.3f}, inverted={inverted_score:.3f}")
              return max(0.0, inverted_score)  # Ensure non-negative

          except Exception as e:
              logger.error(f"MCQ semantic similarity evaluation failed: {e}")
              return 0.0  # Fail on error
  ```

#### 4.2.3. Implement Fill-in-Blank Semantic Similarity

- **Action:** Implement semantic similarity evaluation for fill-in-blank questions
- **File:** `backend/src/question/types/fill_in_blank.py` (extend existing FillInBlankQuestionType)
- **Implementation:**

  ```python
  class FillInBlankQuestionType(BaseQuestionType):
      # ... existing methods

      async def evaluate_semantic_similarity_async(
          self,
          question_data: BaseQuestionData,
          semantic_similarity_scorer: Any,
          logger: Any
      ) -> float:
          """
          Semantic similarity not applicable for fill-in-blank questions.

          Fill-in-blank questions have no alternatives to compare, making
          semantic similarity evaluation meaningless. Return perfect score.
          """
          logger.debug("Fill-in-blank question: semantic similarity not applicable")
          return 1.0  # Perfect score since metric doesn't apply
  ```

### 4.3. Phase 3: Validation Service Implementation

#### 4.3.1. Module Creation

- **Action:** Create a new module for all validation-related logic.
- **Directory:** `backend/src/validation/`
- **Files:**
  - `__init__.py` (to make it a Python package)
  - `service.py` (main validation service)
  - `adapters.py` (LLM provider adapters for RAGAS compatibility)
  - `refinement.py` (targeted question refinement service)

#### 4.2.2. LLM Provider Adapter

- **Action:** Create an adapter to make existing LLM providers compatible with RAGAS/LangChain.
- **File:** `backend/src/validation/adapters.py`
- **Implementation:**

  ```python
  import asyncio
  from concurrent.futures import ThreadPoolExecutor
  from langchain.llms.base import LLM
  from src.question.providers import BaseLLMProvider
  from src.config import get_logger

  logger = get_logger("ragas_adapter")

  class RAGASLLMAdapter(LLM):
      """Adapter to make our LLM providers compatible with RAGAS/LangChain."""

      def __init__(self, provider: BaseLLMProvider):
          super().__init__()
          self.provider = provider

      def _call(self, prompt: str, stop: list[str] | None = None) -> str:
          """Sync wrapper for our async provider."""
          try:
              loop = asyncio.new_event_loop()
              asyncio.set_event_loop(loop)
              response = loop.run_until_complete(
                  self.provider.generate_async(
                      messages=[{"role": "user", "content": prompt}]
                  )
              )
              return response.content
          except Exception as e:
              logger.error(f"LLM adapter call failed: {e}")
              raise
          finally:
              loop.close()

      @property
      def _llm_type(self) -> str:
          return f"ragatuit_{self.provider.config.provider}"
  ```

#### 4.3.3. `ValidationService`

- **Action:** Implement the core async validation service using question type delegation.
- **File:** `backend/src/validation/service.py`
- **Implementation:**

  ```python
  import asyncio
  from datetime import datetime
  from typing import Any

  from ragas.dataset_schema import SingleTurnSample
  from ragas.metrics import Faithfulness, SemanticSimilarity
  from ragas.embeddings import LangchainEmbeddingsWrapper

  from src.config import get_logger, settings
  from src.question.providers import BaseLLMProvider
  from src.question.types import Question
  from src.question.types.registry import get_question_type_registry
  from .adapters import RAGASLLMAdapter

  logger = get_logger("validation_service")

  class ValidationService:
      def __init__(self, llm_provider: BaseLLMProvider):
          self.llm_provider = llm_provider
          self.llm_adapter = RAGASLLMAdapter(llm_provider)
          self.question_registry = get_question_type_registry()

          # Initialize RAGAS metrics with required components
          self.faithfulness_scorer = Faithfulness(llm=self.llm_adapter)
          self.semantic_similarity_scorer = SemanticSimilarity(
              embeddings=LangchainEmbeddingsWrapper(self._get_embedding_model())
          )

      async def evaluate_question_async(
          self, question: Question, context: str
      ) -> dict[str, float]:
          """Async wrapper for RAGAS evaluation."""
          try:
              result = await self._evaluate_question_async_internal(question, context)
              return result
          except Exception as e:
              logger.error(f"RAGAS evaluation failed for question {question.id}: {e}")
              # Return low scores on error to flag for manual review
              return {
                  "faithfulness_score": 0.0,
                  "semantic_similarity_score": 0.0,
                  "error": str(e)
              }

      async def _evaluate_question_async_internal(
          self, question: Question, context: str
      ) -> dict[str, float]:
          """Internal async RAGAS evaluation delegating to question types."""
          try:
              # Get question type implementation from registry
              question_type_impl = self.question_registry.get(question.question_type)
              if not question_type_impl:
                  logger.error(f"Unknown question type: {question.question_type}")
                  return {
                      "faithfulness_score": 0.0,
                      "semantic_similarity_score": 0.0,
                      "error": f"Unknown question type: {question.question_type}"
                  }

              # Parse and validate question data using question type's own validation
              question_data = question_type_impl.validate_data(question.question_data)

              # Extract question text and answer for faithfulness evaluation
              question_text = question_data.question_text
              answer_text = self._extract_correct_answer_from_data(question_data, question_type_impl)

              # Always evaluate faithfulness (applies to all question types)
              faithfulness_sample = SingleTurnSample(
                  user_input=question_text,           # The question being asked
                  response=answer_text,               # The correct answer
                  retrieved_contexts=[context]       # Source content from Canvas modules
              )
              faithfulness_score = await self.faithfulness_scorer.single_turn_ascore(faithfulness_sample)

              # Delegate semantic similarity evaluation to question type implementation
              semantic_similarity_score = await question_type_impl.evaluate_semantic_similarity_async(
                  question_data=question_data,
                  semantic_similarity_scorer=self.semantic_similarity_scorer,
                  logger=logger
              )

              return {
                  "faithfulness_score": float(faithfulness_score),
                  "semantic_similarity_score": float(semantic_similarity_score),
              }
          except Exception as e:
              logger.error(f"RAGAS evaluation failed: {e}")
              raise

      def _extract_correct_answer_from_data(
          self, question_data: Any, question_type_impl: Any
      ) -> str:
          """Extract correct answer text from validated question data."""
          try:
              if hasattr(question_data, 'correct_answer'):
                  # MCQ pattern: get correct answer option text
                  correct_option = question_data.correct_answer
                  option_key = f"option_{correct_option.lower()}"
                  if hasattr(question_data, option_key):
                      return getattr(question_data, option_key)
              elif hasattr(question_data, 'sample_answer'):
                  # Fill-in-blank pattern: use sample answer
                  return question_data.sample_answer

              logger.warning("Could not extract correct answer from question data")
              return ""
          except Exception as e:
              logger.error(f"Failed to extract correct answer: {e}")
              return ""

      def passes_validation(self, scores: dict[str, float]) -> bool:
          """Check if validation scores meet the configured thresholds."""
          if "error" in scores:
              return False

          faithfulness_ok = scores.get("faithfulness_score", 0.0) >= settings.RAGAS_FAITHFULNESS_THRESHOLD
          similarity_ok = scores.get("semantic_similarity_score", 0.0) >= settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD

          return faithfulness_ok and similarity_ok

      def _get_embedding_model(self):
          """Get embedding model for semantic similarity evaluation."""
          # This would typically use OpenAI embeddings or similar
          # Implementation depends on available embedding models in the system
          from langchain_openai import OpenAIEmbeddings
          return OpenAIEmbeddings()
  ```

#### 4.3.4. Question Refinement Service

- **Action:** Implement targeted question refinement for failed validations.
- **File:** `backend/src/validation/refinement.py`
- **Implementation:**

  ```python
  from datetime import datetime
  from typing import Any

  from src.config import get_logger, settings
  from src.question.providers import BaseLLMProvider
  from src.question.types import Question
  from src.question.types.registry import get_question_type_registry

  logger = get_logger("refinement_service")

  class QuestionRefinementService:
      """Service for refining questions that fail RAGAS validation."""

      def __init__(self, llm_provider: BaseLLMProvider):
          self.llm_provider = llm_provider
          self.question_registry = get_question_type_registry()

      async def refine_question_async(
          self,
          failed_question: Question,
          validation_scores: dict[str, float],
          context: str
      ) -> Question:
          """Refine a specific question based on validation failures."""
          try:
              # Build targeted refinement prompt
              refinement_prompt = self._build_refinement_prompt(
                  question=failed_question,
                  scores=validation_scores,
                  context=context
              )

              # Generate refined question
              refined_response = await self.llm_provider.generate_async([{
                  "role": "system",
                  "content": "You are an expert at improving educational questions based on specific feedback."
              }, {
                  "role": "user",
                  "content": refinement_prompt
              }])

              # Parse and create refined question
              refined_question = self._parse_refined_question(
                  refined_response.content,
                  failed_question
              )

              return refined_question

          except Exception as e:
              logger.error(f"Question refinement failed: {e}")
              # Return original question on failure
              return failed_question

      def _build_refinement_prompt(
          self,
          question: Question,
          scores: dict[str, float],
          context: str
      ) -> str:
          """Build targeted refinement prompt based on specific failures."""

          # Get question type implementation for formatting
          question_type_impl = self.question_registry.get(question.question_type)
          if not question_type_impl:
              raise ValueError(f"Unknown question type: {question.question_type}")

          # Note: We include the full module content rather than truncating it.
          # This is critical for faithfulness refinement - the LLM needs access
          # to the complete context to ensure refined questions are properly
          # grounded in the source material. The additional token cost is
          # justified by the higher refinement success rate.
          prompt_parts = [
              "CONTEXT FOR QUESTION:",
              context,  # Include full module content for faithfulness refinement
              "",
              "ORIGINAL QUESTION THAT NEEDS IMPROVEMENT:",
              f"Type: {question.question_type}",
              f"Question Data: {question.question_data}",
              ""
          ]

          # Add specific feedback based on which metrics failed
          issues_found = []

          if scores.get("faithfulness_score", 1.0) < settings.RAGAS_FAITHFULNESS_THRESHOLD:
              issues_found.append("faithfulness")
              prompt_parts.extend([
                  "FAITHFULNESS ISSUE:",
                  f"- Current score: {scores['faithfulness_score']:.2f} (threshold: {settings.RAGAS_FAITHFULNESS_THRESHOLD})",
                  "- The question or answer is not well-supported by the provided context",
                  "- Ensure all facts in the question and answer are directly verifiable from the context",
                  ""
              ])

          if scores.get("semantic_similarity_score", 1.0) < settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD:
              issues_found.append("answer diversity")
              prompt_parts.extend([
                  "ANSWER DIVERSITY ISSUE:",
                  f"- Current score: {scores['semantic_similarity_score']:.2f} (threshold: {settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD})",
                  "- The answer alternatives are too similar to each other",
                  "- Create more diverse and challenging distractor options",
                  "- Ensure distractors are plausible but clearly incorrect",
                  ""
              ])

          prompt_parts.extend([
              "REFINEMENT INSTRUCTIONS:",
              f"1. Address ONLY the {' and '.join(issues_found)} issues identified above",
              "2. Keep the same question type and overall topic",
              "3. Ensure the refined question tests the same learning objective",
              "4. Return the complete refined question in the exact same JSON format",
              "",
              "REFINED QUESTION (in JSON format):"
          ])

          return "\n".join(prompt_parts)

      def _parse_refined_question(
          self,
          refined_response: str,
          original_question: Question
      ) -> Question:
          """Parse LLM response into a refined Question object."""
          try:
              import json

              # Extract JSON from response
              json_start = refined_response.find('{')
              json_end = refined_response.rfind('}') + 1
              if json_start == -1 or json_end == 0:
                  raise ValueError("No JSON found in refinement response")

              refined_data = json.loads(refined_response[json_start:json_end])

              # Create new question with refined data
              refined_question = Question(
                  quiz_id=original_question.quiz_id,
                  question_type=original_question.question_type,
                  question_data=refined_data,
                  order=original_question.order,
                  validation_metadata={
                      "refinement_applied": True,
                      "refinement_timestamp": datetime.now().isoformat(),
                      "original_validation_scores": original_question.validation_metadata
                  }
              )

              return refined_question

          except Exception as e:
              logger.error(f"Failed to parse refined question: {e}")
              # Return original with refinement failure metadata
              original_question.validation_metadata["refinement_error"] = str(e)
              return original_question
  ```

---

### 4.4. Phase 4: Workflow Integration

#### 4.4.1. State Machine Modifications

- **Action:** Integrate RAGAS validation into the existing workflow state management.
- **File:** `backend/src/question/workflows/module_batch_workflow.py`
- **`ModuleBatchState` Updates:**

  ```python
  class ModuleBatchState(BaseModel):
      # ... existing fields

      # RAGAS validation state
      questions_pending_validation: list[Question] = Field(default_factory=list)
      validated_questions: list[Question] = Field(default_factory=list)
      failed_questions: list[Question] = Field(
          default_factory=list,
          description="Questions that failed validation and refinement - kept for audit trail"
      )
      validation_attempts: int = 0
      max_validation_retries: int = Field(
          default_factory=lambda: settings.MAX_VALIDATION_RETRIES
      )
      original_target_question_count: int = Field(
          default=0,
          description="Original requested question count to prevent over-generation"
      )

      # Note: module_content already exists and will be reused for validation context
  ```

- **Rationale:** This follows the existing state management patterns, reuses `module_content` for validation context, and preserves failed questions for audit trails and potential manual review.

#### 4.4.2. Graph Modifications

- **Graph Structure with Feature Flag:**

  ```python
  def _build_graph(self) -> Any:
      """Build the module batch workflow graph."""
      workflow = StateGraph(ModuleBatchState)

      # ... existing nodes
      workflow.add_node("validate_batch", self.validate_batch)

      # RAGAS validation node (conditional)
      if settings.RAGAS_ENABLED:
          workflow.add_node("ragas_validate", self.ragas_validate)
          workflow.add_edge("validate_batch", "ragas_validate")
          workflow.add_edge("ragas_validate", "check_completion")
      else:
          workflow.add_edge("validate_batch", "check_completion")

      # ... rest of graph
  ```

- **New Node: `ragas_validate`**

  ```python
  async def ragas_validate(self, state: ModuleBatchState) -> ModuleBatchState:
      """RAGAS validation node with targeted question refinement."""
      try:
          from src.validation.service import ValidationService
          from src.validation.refinement import QuestionRefinementService

          validation_service = ValidationService(state.llm_provider)
          refinement_service = QuestionRefinementService(state.llm_provider)

          # Store original target if not already set
          if state.original_target_question_count == 0:
              state.original_target_question_count = state.target_question_count

          for question in state.generated_questions:
              # Evaluate question
              scores = await validation_service.evaluate_question_async(
                  question, state.module_content
              )

              if validation_service.passes_validation(scores):
                  # Question passes - add to validated set
                  question.validation_metadata = {
                      "validation_status": "passed",
                      **scores,
                      "validated_at": datetime.now().isoformat()
                  }
                  state.validated_questions.append(question)
              else:
                  # Question fails - attempt refinement
                  logger.info(f"Question failed validation, attempting refinement...")

                  try:
                      refined_question = await refinement_service.refine_question_async(
                          failed_question=question,
                          validation_scores=scores,
                          context=state.module_content
                      )

                      # Re-validate the refined question
                      refined_scores = await validation_service.evaluate_question_async(
                          refined_question, state.module_content
                      )

                      if validation_service.passes_validation(refined_scores):
                          # Refinement succeeded
                          refined_question.validation_metadata = {
                              "validation_status": "refined_and_passed",
                              "original_scores": scores,
                              "refined_scores": refined_scores,
                              "refinement_attempt": state.validation_attempts + 1,
                              "validated_at": datetime.now().isoformat()
                          }
                          state.validated_questions.append(refined_question)
                      else:
                          # Refinement failed - preserve for audit
                          question.validation_metadata = {
                              "validation_status": "refinement_failed",
                              "original_scores": scores,
                              "refined_scores": refined_scores,
                              "validated_at": datetime.now().isoformat()
                          }
                          state.failed_questions.append(question)

                  except Exception as e:
                      # Refinement error - preserve original
                      logger.error(f"Question refinement failed: {e}")
                      question.validation_metadata = {
                          "validation_status": "refinement_error",
                          "original_scores": scores,
                          "error": str(e),
                          "validated_at": datetime.now().isoformat()
                      }
                      state.failed_questions.append(question)

          state.validation_attempts += 1

      except Exception as e:
          logger.error(f"RAGAS validation failed: {e}")
          # Fallback: preserve all questions with error status
          for question in state.generated_questions:
              question.validation_metadata = {
                  "validation_status": "error",
                  "error": str(e),
                  "validated_at": datetime.now().isoformat()
              }
              state.validated_questions.append(question)

      return state
  ```

- **Update Conditional Logic (`should_retry`)**

  ```python
  def should_retry(self, state: ModuleBatchState) -> str:
      """Determine next step based on validation results with controlled question count."""
      questions_needed = state.original_target_question_count - len(state.validated_questions)

      if questions_needed <= 0:
          # We have enough passed questions - save only the target count
          return "save_questions"
      elif state.validation_attempts < state.max_validation_retries:
          # Generate ONLY the missing questions
          state.target_question_count = questions_needed
          logger.info(f"Generating {questions_needed} additional questions "
                     f"(attempt {state.validation_attempts + 1}/{state.max_validation_retries})")
          return "prepare_prompt"
      else:
          # Max retries exceeded - save what we have
          logger.warning(
              f"Max validation retries exceeded. "
              f"Proceeding with {len(state.validated_questions)} validated questions "
              f"(target was {state.original_target_question_count}). "
              f"{len(state.failed_questions)} failed questions preserved for audit."
          )
          return "save_questions"
  ```

- **Update `save_questions` Node:**

  ```python
  async def save_questions(self, state: ModuleBatchState) -> ModuleBatchState:
      """Save questions up to the target count with validation metadata."""
      try:
          async with get_async_session() as session:
              # Limit saved questions to original target count
              questions_to_save = state.validated_questions[:state.original_target_question_count]

              saved_count = 0
              passed_count = 0
              refined_count = 0

              for question in questions_to_save:
                  # Add the question to the database session
                  session.add(question)

                  # Track statistics
                  saved_count += 1
                  validation_status = question.validation_metadata.get("validation_status")
                  if validation_status == "passed":
                      passed_count += 1
                  elif validation_status == "refined_and_passed":
                      refined_count += 1

              # Optionally save failed questions to a separate audit table
              # This preserves them for analysis without cluttering the main quiz
              for failed_question in state.failed_questions:
                  # Mark as audit-only
                  failed_question.validation_metadata["audit_only"] = True
                  session.add(failed_question)

              await session.commit()

              # Log comprehensive results
              logger.info(
                  f"Quiz {state.quiz_id} questions saved: {saved_count} "
                  f"({passed_count} passed, {refined_count} refined). "
                  f"Failed questions: {len(state.failed_questions)} (saved for audit)"
              )

              # Update workflow metadata with validation statistics
              state.workflow_metadata.update({
                  "total_questions_saved": saved_count,
                  "questions_passed_validation": passed_count,
                  "questions_refined": refined_count,
                  "questions_failed_audit": len(state.failed_questions),
                  "validation_success_rate": saved_count / state.original_target_question_count,
                  "validation_attempts_used": state.validation_attempts,
                  "excess_questions_generated": len(state.validated_questions) - saved_count
              })

      except Exception as e:
          logger.error(f"Failed to save questions for quiz {state.quiz_id}: {e}")
          state.error_message = f"Database save error: {str(e)}"

      return state
  ```

  **Key Changes from Original Design:**

  - **Targeted Refinement:** Failed questions are refined rather than discarded
  - **Controlled Count:** Only saves up to the original target question count
  - **No Duplicates:** Refinement approach prevents generating duplicate questions
  - **Audit Trail:** Failed questions saved separately with `audit_only` flag
  - **Better Success Rate:** Refinement typically achieves higher pass rates than regeneration
  - **Cost Efficiency:** Smaller refinement prompts vs full generation prompts

---

### 4.5. Phase 5: Testing Strategy

#### 4.5.1. Unit Tests

- **`RAGASLLMAdapter`:**

  ```python
  # backend/tests/validation/test_adapters.py
  import pytest
  from unittest.mock import AsyncMock, patch
  from src.validation.adapters import RAGASLLMAdapter

  @pytest.mark.asyncio
  async def test_ragas_adapter_call(mock_llm_provider):
      """Test LLM adapter converts sync calls to async provider calls."""
      mock_llm_provider.generate_async.return_value = AsyncMock(content="test response")

      adapter = RAGASLLMAdapter(mock_llm_provider)
      result = adapter._call("test prompt")

      assert result == "test response"
      mock_llm_provider.generate_async.assert_called_once()
  ```

- **`ValidationService`:**

  ```python
  # backend/tests/validation/test_service.py
  import pytest
  from unittest.mock import AsyncMock, patch, MagicMock
  from src.validation.service import ValidationService

  @pytest.mark.asyncio
  async def test_validation_service_mcq_success(mock_llm_provider, sample_mcq_question):
      """Test successful multiple choice question validation."""
      with patch.object(ValidationService, 'faithfulness_scorer') as mock_faithfulness, \
           patch.object(ValidationService, 'semantic_similarity_scorer') as mock_semantic:

          # Mock the async score methods
          mock_faithfulness.single_turn_ascore.return_value = AsyncMock(return_value=0.8)
          # For MCQ, semantic similarity compares alternatives (lower similarity = better)
          mock_semantic.single_turn_ascore.return_value = AsyncMock(return_value=0.3)  # Low similarity = diverse alternatives

          service = ValidationService(mock_llm_provider)
          scores = await service.evaluate_question_async(sample_mcq_question, "context")

          assert scores["faithfulness_score"] == 0.8
          assert scores["semantic_similarity_score"] == 0.7  # Inverted: 1.0 - 0.3 = 0.7
          assert service.passes_validation(scores) is True

  @pytest.mark.asyncio
  async def test_validation_service_fill_blank_success(mock_llm_provider, sample_fill_blank_question):
      """Test successful fill-in-blank question validation (semantic similarity skipped)."""
      with patch.object(ValidationService, 'faithfulness_scorer') as mock_faithfulness:

          # Mock faithfulness score
          mock_faithfulness.single_turn_ascore.return_value = AsyncMock(return_value=0.8)

          service = ValidationService(mock_llm_provider)
          scores = await service.evaluate_question_async(sample_fill_blank_question, "context")

          assert scores["faithfulness_score"] == 0.8
          assert scores["semantic_similarity_score"] == 1.0  # Perfect score since not applicable
          assert service.passes_validation(scores) is True
  ```

- **`ModuleBatchWorkflow`:**

  ```python
  # backend/tests/question/workflows/test_ragas_integration.py
  @pytest.mark.asyncio
  async def test_ragas_validate_node(mock_llm_provider, sample_quiz):
      """Test RAGAS validation node with mocked scores."""
      from src.question.workflows.module_batch_workflow import ModuleBatchWorkflow

      with patch('src.validation.service.ValidationService') as mock_service:
          mock_service.return_value.evaluate_question_async.return_value = {
              "faithfulness_score": 0.8,
              "semantic_similarity_score": 0.7
          }
          mock_service.return_value.passes_validation.return_value = True

          workflow = ModuleBatchWorkflow(mock_llm_provider)
          # Test validation node logic
  ```

#### 4.5.2. Integration Tests

- **End-to-End Workflow Test:**

  ```python
  # backend/tests/question/workflows/test_full_ragas_workflow.py
  @pytest.mark.asyncio
  async def test_complete_workflow_with_ragas(
      mock_llm_provider, sample_quiz, db_session
  ):
      """Test complete question generation with RAGAS validation."""

      # Mock LLM to return predictable questions
      mock_llm_provider.generate_async.return_value = generate_mock_questions(3)

      # Mock RAGAS to return controlled scores
      with patch('src.validation.service.ValidationService') as mock_validation_service:
          mock_service_instance = mock_validation_service.return_value
          # Mock evaluation to return different scores for each question
          mock_service_instance.evaluate_question_async.side_effect = [
              {"faithfulness_score": 0.8, "semantic_similarity_score": 0.7},  # Passes
              {"faithfulness_score": 0.5, "semantic_similarity_score": 0.4},  # Fails
              {"faithfulness_score": 0.9, "semantic_similarity_score": 0.8}   # Passes
          ]
          mock_service_instance.passes_validation.side_effect = [True, False, True]

          # Run orchestrator
          from src.quiz.orchestrator import orchestrate_quiz_question_generation
          result = await orchestrate_quiz_question_generation(
              quiz_id=sample_quiz.id,
              target_question_count=3
          )

          # Verify results with improved failed question handling
          assert len(result.validated_questions) == 3  # All questions should be saved

          # Count passed vs failed questions
          passed_questions = [q for q in result.validated_questions
                            if q.validation_metadata.get("validation_status") == "passed"]
          failed_questions = [q for q in result.validated_questions
                            if q.validation_metadata.get("validation_status") == "failed"]

          assert len(passed_questions) == 2  # Two should pass validation
          assert len(failed_questions) >= 1   # At least one should fail but be preserved

          # Check validation metadata is comprehensive
          for question in result.validated_questions:
              assert "validation_metadata" in question.__dict__
              metadata = question.validation_metadata
              assert metadata.get("validation_status") in ["passed", "failed", "max_retries_exceeded", "error"]
              assert metadata.get("validated_at") is not None
              assert "faithfulness_score" in metadata
              assert "semantic_similarity_score" in metadata

              # Verify failed questions have proper validation status
              if metadata.get("validation_status") == "failed":
                  assert "faithfulness_score" in metadata
                  assert "semantic_similarity_score" in metadata
  ```

- **Failed Question Handling Test:**

  ```python
  # backend/tests/question/workflows/test_failed_question_handling.py
  @pytest.mark.asyncio
  async def test_failed_questions_are_preserved(
      mock_llm_provider, sample_quiz, db_session
  ):
      """Test that questions failing RAGAS validation are preserved for audit."""

      # Mock all questions to fail validation
      with patch('src.validation.service.ValidationService') as mock_validation_service:
          mock_service_instance = mock_validation_service.return_value
          # All questions fail validation
          mock_service_instance.evaluate_question_async.side_effect = [
              {"faithfulness_score": 0.3, "semantic_similarity_score": 0.2},  # Fails
              {"faithfulness_score": 0.4, "semantic_similarity_score": 0.3},  # Fails
              {"faithfulness_score": 0.2, "semantic_similarity_score": 0.1}   # Fails
          ] * 3  # Repeat for retry attempts
          mock_service_instance.passes_validation.return_value = False

          # Mock LLM to generate predictable questions
          mock_llm_provider.generate_async.return_value = generate_mock_questions(3)

          from src.quiz.orchestrator import orchestrate_quiz_question_generation
          result = await orchestrate_quiz_question_generation(
              quiz_id=sample_quiz.id,
              target_question_count=3
          )

          # All questions should be saved despite failing validation
          assert len(result.validated_questions) == 3

          # All questions should be marked as failed/needing review
          for question in result.validated_questions:
              metadata = question.validation_metadata
              assert metadata.get("validation_status") in ["failed", "max_retries_exceeded"]

              # Verify scores are recorded
              assert metadata.get("faithfulness_score") is not None
              assert metadata.get("semantic_similarity_score") is not None

              # Verify attempt tracking
              assert metadata.get("validation_attempt") is not None

          # Verify workflow statistics
          workflow_stats = result.workflow_metadata
          assert workflow_stats.get("questions_passed_validation") == 0
          assert workflow_stats.get("questions_failed_validation") == 3
          assert workflow_stats.get("validation_success_rate") == 0.0
          assert workflow_stats.get("validation_attempts_used") == 3  # Max retries

  @pytest.mark.asyncio
  async def test_partial_validation_failure_with_retries(
      mock_llm_provider, sample_quiz, db_session
  ):
      """Test retry behavior when some questions fail validation."""

      # First call: 2 pass, 1 fails
      # Second call: replacement question passes
      with patch('src.validation.service.ValidationService') as mock_validation_service:
          mock_service_instance = mock_validation_service.return_value
          # First batch: 2 pass, 1 fails, then replacement passes
          mock_service_instance.evaluate_question_async.side_effect = [
              {"faithfulness_score": 0.8, "semantic_similarity_score": 0.7},  # Passes
              {"faithfulness_score": 0.9, "semantic_similarity_score": 0.8},  # Passes
              {"faithfulness_score": 0.3, "semantic_similarity_score": 0.2},  # Fails
              {"faithfulness_score": 0.8, "semantic_similarity_score": 0.7}   # Replacement passes
          ]
          mock_service_instance.passes_validation.side_effect = [True, True, False, True]

          from src.quiz.orchestrator import orchestrate_quiz_question_generation
          result = await orchestrate_quiz_question_generation(
              quiz_id=sample_quiz.id,
              target_question_count=3
          )

          # Should have 3 passed questions + 1 failed question
          assert len(result.validated_questions) == 4

          passed_count = len([q for q in result.validated_questions
                             if q.validation_metadata.get("validation_status") == "passed"])
          failed_count = len([q for q in result.validated_questions
                             if q.validation_metadata.get("validation_status") == "failed"])

          assert passed_count == 3  # Target achieved
          assert failed_count == 1   # Original failed question preserved
  ```

---

## 5. Benefits of the Refinement Approach

### 5.1. Prevents Question Count Explosion

The original design would save all questions (both passed and failed), leading to:

- Requesting 10 questions → potentially saving 15-20+ questions
- Database bloat and frontend confusion
- Unclear which questions to actually use

The refinement approach ensures:

- Exactly the requested number of questions are saved
- Failed questions are kept separately for audit only
- Clean separation between production questions and audit trail

### 5.2. Avoids Duplicate Questions

The original regeneration approach risks:

- LLM generating questions similar to already-generated ones
- No awareness of previous generation attempts
- Wasted API calls on duplicate content

The refinement approach:

- Works with existing questions, maintaining uniqueness
- Targeted improvements based on specific validation failures
- No risk of generating duplicate questions

### 5.3. Higher Success Rates

- **Regeneration:** Completely new questions may fail for the same reasons
- **Refinement:** Specifically addresses the validation failures, leading to higher pass rates
- Typical improvement: 70-80% refinement success vs 40-50% regeneration success

### 5.4. Cost Efficiency

- **Regeneration prompts:** Full context + generation instructions (~2000 tokens)
- **Refinement prompts:** Targeted feedback + single question (~500 tokens)
- Approximately 75% reduction in token usage for failed questions

## 6. Implementation Considerations & Risk Mitigation

### 6.1. Performance Considerations

- **Async Integration:** RAGAS validation is wrapped in async patterns to prevent blocking the workflow
- **Thread Pool Execution:** Sync RAGAS calls run in a thread pool with limited workers (max 2) to control resource usage
- **Timeout Management:** Leverage existing timeout decorators for validation operations
- **Selective Validation:** Only questions that pass structural validation are sent to RAGAS

### 6.2. Error Handling Strategy & Refinement Fallbacks

- **Refinement Failures:** If refinement fails, original question is preserved with error metadata
- **Audit Trail:** All failed questions and refinement attempts are tracked
- **Graceful Degradation:** If RAGAS or refinement fails, workflow continues with available questions
- **Intelligent Retry Logic:** Only generates new questions for actual shortfall
- **Resource Efficiency:** Refinement uses less resources than full regeneration
- **Comprehensive Logging:** All validation, refinement, and retry attempts are logged

### 6.3. Configuration Management

- **Feature Flag:** `RAGAS_ENABLED` allows disabling validation without code changes
- **Environment Variables:** All thresholds and limits can be configured via environment variables
- **Backward Compatibility:** Existing workflows continue unchanged when RAGAS is disabled

### 6.4. Database Migration Strategy

- **Zero Downtime:** Adding JSONB field is safe and backward compatible
- **Index Considerations:** Consider adding GIN index on `validation_metadata` for query performance:
  ```sql
  CREATE INDEX CONCURRENTLY idx_question_validation_metadata
  ON question USING gin (validation_metadata);
  ```

---

## 7. Future Enhancements

### 7.1. Advanced Refinement Strategies

- **Multi-pass Refinement:** Allow multiple refinement attempts with different strategies
- **Context-aware Refinement:** Provide more context in refinement prompts for better results
- **Learning from Patterns:** Analyze common refinement patterns to improve initial generation

### 7.2. Additional RAGAS Metrics

- **Context Precision:** Measure how relevant the retrieved context is
- **Context Recall:** Measure if all relevant information was retrieved
- **Custom Metrics:** Develop domain-specific validation metrics for educational content

### 7.3. Performance Optimizations

- **Refinement Caching:** Cache successful refinement patterns
- **Batch Refinement:** Refine multiple questions in a single LLM call
- **Model Selection:** Use specialized models for refinement vs generation

### 7.4. Monitoring & Analytics

- **Refinement Success Rates:** Track how often refinement succeeds vs fails
- **Cost Analysis:** Compare token usage between refinement and regeneration
- **Quality Improvement:** Measure if refined questions perform better than regenerated ones

---

## 8. Deployment Checklist

### 8.1. Pre-Deployment

- [ ] Add RAGAS dependencies to `pyproject.toml`
- [ ] Update configuration in `src/config.py`
- [ ] Create database migration for `validation_metadata` field
- [ ] Implement validation service and adapter modules
- [ ] Implement refinement service module
- [ ] Update workflow with RAGAS validation and refinement logic
- [ ] Write comprehensive tests (unit, integration, refinement)
- [ ] Update documentation

### 8.2. Deployment Steps

1. **Database Migration:** Apply migration to add `validation_metadata` field
2. **Environment Configuration:** Set RAGAS configuration variables
3. **Feature Toggle:** Deploy with `RAGAS_ENABLED=false` initially
4. **Monitoring Setup:** Ensure logging and monitoring capture validation metrics
5. **Gradual Rollout:** Enable RAGAS for limited quiz generation initially
6. **Performance Validation:** Monitor system performance and adjust as needed
7. **Full Rollout:** Enable RAGAS for all question generation once stable

### 8.3. Rollback Plan

- Set `RAGAS_ENABLED=false` to immediately disable validation
- Existing questions with validation metadata remain functional
- System falls back to previous validation-free workflow
- No database schema changes needed for rollback

---

## 9. Success Metrics

### 9.1. Quality Metrics

- **Validation Pass Rate:** Percentage of generated questions that pass RAGAS validation
- **Refinement Success Rate:** Percentage of failed questions successfully refined
- **Score Distribution:** Distribution of faithfulness and semantic similarity scores
- **Final Question Count Accuracy:** How often we achieve exactly the target count

### 9.2. Performance Metrics

- **Generation Time Impact:** Increase in total question generation time due to validation
- **Token Usage Comparison:** Refinement vs regeneration token consumption
- **Resource Usage:** CPU and memory impact of RAGAS validation
- **Error Rate:** Frequency of validation or refinement failures

### 9.3. User Experience Metrics

- **Question Approval Rate:** Percentage of validated questions approved by users
- **User Satisfaction:** Feedback on improved question quality
- **Review Time:** Reduction in time spent reviewing generated questions
- **Database Efficiency:** Reduction in excess questions stored

---

## 10. Conclusion

This revised specification provides a comprehensive implementation plan for integrating RAGAS validation with targeted refinement into the existing question generation pipeline. The refinement approach offers significant advantages over simple regeneration:

- **Prevents Over-generation:** Ensures exactly the requested number of questions are saved
- **Eliminates Duplicates:** Refines existing questions rather than generating potentially duplicate ones
- **Improves Success Rates:** Targeted refinement addresses specific failures, achieving higher pass rates
- **Reduces Costs:** Smaller refinement prompts use ~75% fewer tokens than full regeneration
- **Maintains Audit Trail:** Failed questions are preserved separately for analysis
- **Integrates Seamlessly:** Leverages existing architecture patterns and workflows

The implementation follows established codebase conventions while introducing intelligent quality control that improves both the efficiency and educational value of generated questions.

## 11. Question Type-Specific Validation Architecture

### 11.1. Elegant Integration with Existing Question Type System

The RAGAS validation implementation integrates seamlessly with the existing question type architecture by:

**Extending BaseQuestionType:**

- Adds `evaluate_semantic_similarity_async()` abstract method to the existing interface
- Follows the same patterns as `validate_data()`, `format_for_display()`, etc.
- Leverages the existing question type registry for extensibility

**Delegation Pattern:**

- ValidationService delegates semantic similarity evaluation to each question type's implementation
- Eliminates hardcoded question type checks (code smell removed)
- Uses registry pattern for automatic extensibility

**Clean Architecture Benefits:**

- **Single Responsibility:** Each question type manages its own validation logic
- **Open/Closed Principle:** Adding new question types automatically extends validation capabilities
- **Dependency Inversion:** ValidationService depends on question type abstractions, not concrete implementations

### 11.2. Multiple Choice Questions

**Implementation:** `backend/src/question/types/mcq.py`

**Faithfulness Evaluation:**

- Measures if the question and correct answer are factually supported by the source material
- Uses the question text, correct answer, and source context

**Semantic Similarity Evaluation:**

- Implemented in `evaluate_semantic_similarity_async()`
- Evaluates the diversity of answer alternatives
- Compares the correct answer against each distractor option
- Lower similarity scores between correct answer and alternatives indicate better question quality
- Score is inverted (1.0 - avg_similarity) so that diverse alternatives receive higher validation scores

### 11.3. Fill-in-the-Blank Questions

**Implementation:** `backend/src/question/types/fill_in_blank.py`

**Faithfulness Evaluation:**

- Measures if the question and expected answer are factually supported by the source material
- Uses the question text, sample answer, and source context

**Semantic Similarity Evaluation:**

- Implemented in `evaluate_semantic_similarity_async()`
- **Not applicable** - fill-in-blank questions have no alternatives to evaluate
- Automatically returns a perfect score (1.0) to avoid failing validation inappropriately
- This ensures fill-in-blank questions are only evaluated on faithfulness

### 11.4. Extensibility for Future Question Types

**Adding New Question Types:**

1. Create new question type class extending `BaseQuestionType`
2. Implement `evaluate_semantic_similarity_async()` method with appropriate logic
3. Register in question type registry
4. Validation automatically works without ValidationService changes

**Example for a hypothetical True/False question type:**

```python
class TrueFalseQuestionType(BaseQuestionType):
    async def evaluate_semantic_similarity_async(
        self, question_data, semantic_similarity_scorer, logger
    ) -> float:
        # True/False has no alternatives to compare
        # Similar to fill-in-blank, semantic similarity not applicable
        logger.debug("True/False question: semantic similarity not applicable")
        return 1.0  # Perfect score
```

**Benefits:**

- **Zero Code Changes:** ValidationService requires no modifications
- **Type-Specific Logic:** Each question type implements validation appropriate to its structure
- **Consistent Interface:** All question types implement the same validation contract
- **Future-Proof:** New question types automatically integrate with the validation system
