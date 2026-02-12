"""Pinecone vector database integration for Agno Knowledge.

Creates per-namespace Knowledge instances backed by PineconeDb.
Index 'support-examples' with category-specific namespaces.
"""

from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pineconedb import PineconeDb

from config import settings


def create_knowledge(namespace: str) -> Knowledge:
    """Create a Pinecone-backed Knowledge instance for a category namespace.

    Args:
        namespace: Pinecone namespace (e.g., 'shipping', 'retention', 'outstanding-cases').

    Returns:
        Knowledge instance ready for agent consumption.
    """
    vector_db = PineconeDb(
        name=settings.pinecone_index,
        dimension=1536,
        metric="cosine",
        spec={"serverless": {"cloud": "aws", "region": "us-east-1"}},
        api_key=settings.pinecone_api_key,
        namespace=namespace,
        use_hybrid_search=True,
        hybrid_alpha=0.5,
    )

    return Knowledge(
        name=f"support-knowledge-{namespace}",
        description=f"Support knowledge base for {namespace} category",
        vector_db=vector_db,
    )
