import re
import html


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Cleans a string for safe storage and display.
    - Strips HTML tags (XSS prevention)
    - Escapes HTML entities
    - Trims whitespace
    - Enforces max length
    """
    if not value:
        return ""

    # Strip HTML tags
    value = re.sub(r"<[^>]+>", "", value)

    # Escape remaining HTML entities
    value = html.escape(value)

    # Normalize whitespace
    value = " ".join(value.split())

    # Enforce length
    return value[:max_length]


def sanitize_search_query(query: str) -> str:
    """
    Extra cleaning for search queries.
    Prevents SQL injection attempts from reaching the ORM.
    Note: SQLAlchemy parameterizes queries automatically, but
    we still sanitize to prevent log injection and weird behavior.
    """
    if not query:
        return ""

    # Remove SQL comment patterns
    query = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
    query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)

    # Remove semicolons (statement terminators)
    query = query.replace(";", "")

    # Trim and limit length
    return query.strip()[:200]