"""Load knowledge into Dash PgVector knowledge base.

Run after dash-db is up:
    docker compose exec dash python scripts/load_knowledge.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import create_knowledge  # noqa: E402

KNOWLEDGE_DIR = Path(__file__).parent.parent / "dash" / "knowledge"

knowledge = create_knowledge("Dash Knowledge", "dash_knowledge")


def load_tables() -> int:
    """Load table metadata JSON files."""
    tables_dir = KNOWLEDGE_DIR / "tables"
    if not tables_dir.exists():
        print(f"Tables directory not found: {tables_dir}")
        return 0

    count = 0
    for filepath in sorted(tables_dir.glob("*.json")):
        with open(filepath) as f:
            table = json.load(f)

        content = json.dumps(table, ensure_ascii=False, indent=2)
        knowledge.insert(
            name=f"table_{table['table_name']}",
            text_content=content,
            upsert=True,
        )
        print(f"  Loaded table: {table['table_name']}")
        count += 1

    return count


def load_business_rules() -> int:
    """Load business rules JSON files."""
    business_dir = KNOWLEDGE_DIR / "business"
    if not business_dir.exists():
        return 0

    count = 0
    for filepath in sorted(business_dir.glob("*.json")):
        with open(filepath) as f:
            data = json.load(f)

        content = json.dumps(data, ensure_ascii=False, indent=2)
        knowledge.insert(
            name=f"rules_{filepath.stem}",
            text_content=content,
            upsert=True,
        )
        print(f"  Loaded rules: {filepath.stem}")
        count += 1

    return count


def load_queries() -> int:
    """Load validated SQL query files."""
    queries_dir = KNOWLEDGE_DIR / "queries"
    if not queries_dir.exists():
        return 0

    count = 0
    for filepath in sorted(queries_dir.glob("*.sql")):
        with open(filepath) as f:
            content = f.read()

        knowledge.insert(
            name=f"queries_{filepath.stem}",
            text_content=content,
            upsert=True,
        )
        print(f"  Loaded queries: {filepath.stem}")
        count += 1

    return count


if __name__ == "__main__":
    print("Loading knowledge into Dash PgVector...")
    print()

    tables = load_tables()
    rules = load_business_rules()
    queries = load_queries()

    total = tables + rules + queries
    print(f"\nDone: {tables} tables, {rules} rule sets, {queries} query files = {total} total")
