"""Read-only SQL tools that block write operations.

Extends Agno's SQLTools with a regex guard that rejects INSERT, UPDATE,
DELETE, DROP, ALTER, CREATE, TRUNCATE, and other mutating statements.
"""

import re

from agno.tools.sql import SQLTools

_WRITE_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|"
    r"REPLACE|MERGE|UPSERT|COPY|CALL|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


class ReadOnlySQLTools(SQLTools):
    """SQLTools subclass that only allows SELECT queries."""

    def run_sql_query(self, query: str) -> str:
        """Execute a SQL query, blocking any write operations."""
        # Strip leading whitespace and parens before checking
        stripped = query.strip().lstrip("(")
        # Remove comments before pattern matching
        no_comments = stripped.split("--")[0].split("/*")[0]
        if _WRITE_PATTERNS.search(no_comments):
            return "ERROR: Only SELECT queries are allowed. This is a read-only analytics agent."
        return super().run_sql_query(query)
