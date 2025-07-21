"""Question refinement service for targeted question improvement."""

import json
from datetime import datetime

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
        context: str,
    ) -> Question:
        """Refine a specific question based on validation failures."""
        try:
            # Build targeted refinement prompt
            refinement_prompt = self._build_refinement_prompt(
                question=failed_question, scores=validation_scores, context=context
            )

            # Generate refined question
            from src.question.providers import LLMMessage

            refined_response = await self.llm_provider.generate_with_retry(
                [
                    LLMMessage(
                        role="system",
                        content="You are an expert at improving educational questions based on specific feedback.",
                    ),
                    LLMMessage(role="user", content=refinement_prompt),
                ]
            )

            # Parse and create refined question
            refined_question = self._parse_refined_question(
                refined_response.content, failed_question
            )

            return refined_question

        except Exception as e:
            logger.error(f"Question refinement failed: {e}")
            # Return original question on failure
            return failed_question

    def _build_refinement_prompt(
        self, question: Question, scores: dict[str, float], context: str
    ) -> str:
        """Build targeted refinement prompt based on specific failures."""

        # Get question type implementation for formatting
        question_type_impl = self.question_registry.get_question_type(
            question.question_type
        )
        if not question_type_impl:
            raise ValueError(f"Unknown question type: {question.question_type}")

        # Note: We include the full module content rather than truncating it.
        # This is critical for faithfulness refinement - the LLM needs access
        # to the complete context to ensure refined questions are properly
        # grounded in the source material.
        prompt_parts = [
            "CONTEXT FOR QUESTION:",
            context,  # Include full module content for faithfulness refinement
            "",
            "ORIGINAL QUESTION THAT NEEDS IMPROVEMENT:",
            f"Type: {question.question_type}",
            f"Question Data: {question.question_data}",
            "",
        ]

        # Add specific feedback based on which metrics failed
        issues_found = []

        if (
            scores.get("faithfulness_score", 1.0)
            < settings.RAGAS_FAITHFULNESS_THRESHOLD
        ):
            issues_found.append("faithfulness")
            prompt_parts.extend(
                [
                    "FAITHFULNESS ISSUE:",
                    f"- Current score: {scores['faithfulness_score']:.2f} (threshold: {settings.RAGAS_FAITHFULNESS_THRESHOLD})",
                    "- The question or answer is not well-supported by the provided context",
                    "- Ensure all facts in the question and answer are directly verifiable from the context",
                    "",
                ]
            )

        if (
            scores.get("semantic_similarity_score", 1.0)
            < settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD
        ):
            issues_found.append("answer diversity")
            prompt_parts.extend(
                [
                    "ANSWER DIVERSITY ISSUE:",
                    f"- Current score: {scores['semantic_similarity_score']:.2f} (threshold: {settings.RAGAS_SEMANTIC_SIMILARITY_THRESHOLD})",
                    "- The answer alternatives are too similar to each other",
                    "- Create more diverse and challenging distractor options",
                    "- Ensure distractors are plausible but clearly incorrect",
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "REFINEMENT INSTRUCTIONS:",
                f"1. Address ONLY the {' and '.join(issues_found)} issues identified above",
                "2. Keep the same question type and overall topic",
                "3. Ensure the refined question tests the same learning objective",
                "4. Return the complete refined question in the exact same JSON format",
                "",
                "REFINED QUESTION (in JSON format):",
            ]
        )

        return "\n".join(prompt_parts)

    def _parse_refined_question(
        self, refined_response: str, original_question: Question
    ) -> Question:
        """Parse LLM response into a refined Question object."""
        try:
            # Extract JSON from response
            json_start = refined_response.find("{")
            json_end = refined_response.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in refinement response")

            refined_data = json.loads(refined_response[json_start:json_end])

            # Create new question with refined data
            refined_question = Question(
                quiz_id=original_question.quiz_id,
                question_type=original_question.question_type,
                question_data=refined_data,
                difficulty=original_question.difficulty,
                validation_metadata={
                    "refinement_applied": True,
                    "refinement_timestamp": datetime.now().isoformat(),
                    "original_validation_scores": original_question.validation_metadata,
                },
            )

            return refined_question

        except Exception as e:
            logger.error(f"Failed to parse refined question: {e}")
            # Return original with refinement failure metadata
            original_question.validation_metadata["refinement_error"] = str(e)
            return original_question
