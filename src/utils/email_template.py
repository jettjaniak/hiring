"""
Email template utility functions
"""
from typing import List
from jinja2 import Environment, meta, nodes


def infer_template_variables(content: str, subject: str = "", to: str = "", cc: str = "", bcc: str = "") -> List[dict]:
    """
    Infer variables from email template content using Jinja2 AST parsing.

    Finds variables in {{ }} and determines their type based on usage:
    - Variables used in {% if %} conditions are marked as "boolean"
    - All other variables are marked as "text"

    Filters out:
    - Variables with dots (like candidate.name) - these are provided by candidate object
    - The 'candidate' variable itself

    Args:
        content: Email body template content
        subject: Email subject template (optional)
        to: To address template (optional)
        cc: CC address template (optional)
        bcc: BCC address template (optional)

    Returns:
        List of dicts with {"name": str, "type": "text"|"boolean"}
        Sorted alphabetically by name.
    """
    env = Environment()
    all_text = f"{subject} {to} {cc} {bcc} {content}"

    try:
        ast = env.parse(all_text)
    except Exception:
        # If template parsing fails, return empty list
        return []

    # Find all undeclared variables
    all_vars = meta.find_undeclared_variables(ast)

    # Find variables used in If conditions (these are booleans)
    boolean_vars = set()

    def visit_node(node):
        if isinstance(node, nodes.If):
            # Extract variable names from If test expression
            if isinstance(node.test, nodes.Name):
                boolean_vars.add(node.test.name)
            elif isinstance(node.test, nodes.Not) and isinstance(node.test.node, nodes.Name):
                boolean_vars.add(node.test.node.name)

        # Recursively visit child nodes
        for child in node.iter_child_nodes():
            visit_node(child)

    visit_node(ast)

    # Filter out variables with dots (like candidate.name) - these are provided by candidate object
    simple_vars = {var for var in all_vars if '.' not in var and var != 'candidate'}

    # Build result
    result = []
    for var in sorted(simple_vars):
        var_type = "boolean" if var in boolean_vars else "text"
        result.append({"name": var, "type": var_type})

    return result
