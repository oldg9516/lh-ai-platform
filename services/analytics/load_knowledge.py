"""Load knowledge base content into PgVector.

This script loads table schemas, sample queries, and business rules
into the analytics agent's knowledge base for RAG-powered SQL generation.

Run once after database setup:
    python load_knowledge.py
"""

import json
import os
from pathlib import Path

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

from config import settings

# Initialize knowledge base (using Pinecone instead of PgVector)
vector_db = PineconeDb(
    name=settings.pinecone_index,
    dimension=1024,  # Match existing support-examples index dimension
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
    api_key=settings.pinecone_api_key,
    namespace="analytics-knowledge",
    use_hybrid_search=True,
)
knowledge = Knowledge(vector_db=vector_db)

def load_schemas():
    """Load table schema descriptions from JSON files."""
    schemas_dir = Path("knowledge/schemas")
    if not schemas_dir.exists():
        print(f"❌ Schemas directory not found: {schemas_dir}")
        return 0

    count = 0
    for schema_file in schemas_dir.glob("*.json"):
        with open(schema_file) as f:
            schema = json.load(f)

        knowledge.add_content(
            text_content=json.dumps(schema, indent=2),
            metadata={
                "type": "table_schema",
                "table": schema["table"],
                "source": schema_file.name,
            },
        )
        print(f"✅ Loaded schema: {schema['table']}")
        count += 1

    return count


def load_sample_queries():
    """Load sample SQL queries from .sql files."""
    queries_dir = Path("knowledge/queries")
    if not queries_dir.exists():
        print(f"❌ Queries directory not found: {queries_dir}")
        return 0

    count = 0
    for query_file in queries_dir.glob("*.sql"):
        with open(query_file) as f:
            query = f.read()

        query_name = query_file.stem  # filename without extension
        knowledge.add_content(
            text_content=query,
            metadata={
                "type": "sample_query",
                "name": query_name,
                "source": query_file.name,
            },
        )
        print(f"✅ Loaded query: {query_name}")
        count += 1

    return count


def load_business_rules():
    """Load business rules and metrics definitions from JSON files."""
    rules_dir = Path("knowledge/rules")
    if not rules_dir.exists():
        print(f"❌ Rules directory not found: {rules_dir}")
        return 0

    count = 0
    for rules_file in rules_dir.glob("*.json"):
        with open(rules_file) as f:
            rules = json.load(f)

        knowledge.add_content(
            text_content=json.dumps(rules, indent=2),
            metadata={
                "type": "business_rules",
                "source": rules_file.name,
            },
        )
        print(f"✅ Loaded rules: {rules_file.stem}")
        count += 1

    return count


if __name__ == "__main__":
    print("🚀 Loading knowledge base into PgVector...")
    print(f"📊 Database: {settings.analytics_db_url.split('@')[1]}\n")  # Hide password

    try:
        schemas_count = load_schemas()
        queries_count = load_sample_queries()
        rules_count = load_business_rules()

        total = schemas_count + queries_count + rules_count
        print(f"\n✨ Knowledge base loaded successfully!")
        print(f"   - {schemas_count} table schemas")
        print(f"   - {queries_count} sample queries")
        print(f"   - {rules_count} business rules")
        print(f"   - {total} total items")

    except Exception as e:
        print(f"\n❌ Error loading knowledge base: {e}")
        raise
