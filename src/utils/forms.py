"""
Form processing utility functions
"""
import json
from typing import List, Dict, Set


def parse_checklist_items(items_text: str) -> str:
    """
    Parse checklist items from newline-separated text to JSON array.

    Converts text like:
        Item 1
        Item 2
        Item 3

    To JSON: ["Item 1", "Item 2", "Item 3"]

    Args:
        items_text: Newline-separated checklist items

    Returns:
        JSON string representation of the items array
    """
    if not items_text or not items_text.strip():
        return json.dumps([])

    items = [line.strip() for line in items_text.strip().split('\n') if line.strip()]
    return json.dumps(items)


def checklist_items_to_text(items_json: str) -> str:
    """
    Convert checklist items from JSON array to newline-separated text.

    Converts JSON: ["Item 1", "Item 2", "Item 3"]

    To text:
        Item 1
        Item 2
        Item 3

    Args:
        items_json: JSON string representation of items array

    Returns:
        Newline-separated text
    """
    if not items_json:
        return ""

    try:
        items = json.loads(items_json)
        if not isinstance(items, list):
            return ""
        return '\n'.join(items)
    except (json.JSONDecodeError, TypeError):
        return ""


def build_document_replacements(form_data: Dict, exclude_keys: Set[str]) -> Dict[str, str]:
    """
    Build document replacement dictionary from form data.

    Extracts key-value pairs from form data, excluding specified keys.
    Useful for building variable replacement maps for document generation.

    Args:
        form_data: Dictionary of form field names to values
        exclude_keys: Set of keys to exclude from replacements

    Returns:
        Dictionary of replacement key-value pairs
    """
    replacements = {}

    for key, value in form_data.items():
        if key not in exclude_keys and value:
            replacements[key] = value

    return replacements
