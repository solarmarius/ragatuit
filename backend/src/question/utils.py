"""Utility functions for question operations."""

from typing import Any


def generate_edit_log_entries(
    old_question_data: dict[str, Any], new_question_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Generate edit log entries by comparing old and new question_data dictionaries.

    Performs field-level comparison and creates log entries for changed fields only.

    Args:
        old_question_data: Original question_data dictionary
        new_question_data: Updated question_data dictionary

    Returns:
        List of edit log entries with format:
        [{"field": "field_name", "old_value": "...", "new_value": "..."}]
    """
    edit_entries = []

    # Get all unique fields from both dictionaries
    all_fields = set(old_question_data.keys()) | set(new_question_data.keys())

    for field in all_fields:
        old_value = old_question_data.get(field)
        new_value = new_question_data.get(field)

        # Only log if values are different
        if old_value != new_value:
            edit_entries.append(
                {
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )

    return edit_entries
