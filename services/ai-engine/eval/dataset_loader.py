"""Load golden dataset from ai_human_comparison into Langfuse Datasets.

Creates three Langfuse datasets:
- support-eval-golden: PERFECT_MATCH records (regression baseline)
- support-eval-good: PERFECT_MATCH + STYLISTIC_EDIT (AI was good)
- support-eval-full: All classified records (full benchmark)

Usage (inside container):
    python -m eval.dataset_loader
    python -m eval.dataset_loader --dataset golden
    python -m eval.dataset_loader --dataset full
"""

import argparse
import json

from langfuse import Langfuse
import structlog

from config import settings
from database.connection import get_client

logger = structlog.get_logger()

# Classification tiers
GOLDEN_CLASSIFICATIONS = {"PERFECT_MATCH", "no_significant_change"}
GOOD_CLASSIFICATIONS = GOLDEN_CLASSIFICATIONS | {"STYLISTIC_EDIT", "stylistic_preference"}
EXCLUDE_CLASSIFICATIONS = {"EXCL_DATA_DISCREPANCY", "EXCL_WORKFLOW_SHIFT", "HUMAN_INCOMPLETE"}

DATASET_CONFIGS = {
    "golden": {
        "name": "support-eval-golden",
        "description": "PERFECT_MATCH records — AI nailed it. Use for regression testing.",
        "filter": lambda r: r.get("change_classification") in GOLDEN_CLASSIFICATIONS,
    },
    "good": {
        "name": "support-eval-good",
        "description": "PERFECT_MATCH + STYLISTIC_EDIT — AI was good. Use for quality benchmark.",
        "filter": lambda r: r.get("change_classification") in GOOD_CLASSIFICATIONS,
    },
    "full": {
        "name": "support-eval-full",
        "description": "All classified records including errors. Use for full benchmark.",
        "filter": lambda r: r.get("change_classification") not in EXCLUDE_CLASSIFICATIONS,
    },
}


def fetch_comparison_records() -> list[dict]:
    """Fetch ai_human_comparison records from Supabase."""
    client = get_client()
    records = []
    page_size = 1000
    offset = 0

    while True:
        response = (
            client.table("ai_human_comparison")
            .select(
                "thread_id, full_request, ai_reply, human_reply, "
                "request_subtype, request_sub_subtype, change_classification, "
                "similarity_score, improvement_suggestions, root_cause, "
                "changed, email, prompt_version, is_outstanding"
            )
            .not_.is_("change_classification", "null")
            .not_.is_("full_request", "null")
            .not_.is_("human_reply", "null")
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data
        if not batch:
            break
        records.extend(batch)
        offset += page_size
        if len(batch) < page_size:
            break

    logger.info("fetched_comparison_records", count=len(records))
    return records


def load_dataset(dataset_key: str = "golden") -> dict:
    """Load records into a Langfuse dataset.

    Args:
        dataset_key: One of 'golden', 'good', 'full'.

    Returns:
        Stats dict with counts.
    """
    config = DATASET_CONFIGS[dataset_key]
    records = fetch_comparison_records()
    filtered = [r for r in records if config["filter"](r)]

    logger.info(
        "loading_dataset",
        dataset=config["name"],
        total_records=len(records),
        filtered_records=len(filtered),
    )

    langfuse = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )

    # Create or get dataset
    langfuse.create_dataset(
        name=config["name"],
        description=config["description"],
        metadata={
            "source": "ai_human_comparison",
            "classifications": list(
                GOLDEN_CLASSIFICATIONS if dataset_key == "golden"
                else GOOD_CLASSIFICATIONS if dataset_key == "good"
                else {"all except excluded"}
            ),
        },
    )

    created = 0
    for record in filtered:
        category = record.get("request_subtype") or "unknown"

        # Build input matching our /api/chat format
        item_input = {
            "message": record["full_request"],
            "contact": {"email": record.get("email")},
        }

        # Expected output = human reply (ground truth)
        expected_output = record["human_reply"]

        metadata = {
            "thread_id": record["thread_id"],
            "category": category,
            "sub_subtype": record.get("request_sub_subtype"),
            "change_classification": record["change_classification"],
            "similarity_score": record.get("similarity_score"),
            "is_outstanding": record.get("is_outstanding", False),
            "prompt_version": record.get("prompt_version"),
            "n8n_ai_reply": record.get("ai_reply"),
            "improvement_suggestions": record.get("improvement_suggestions"),
            "root_cause": record.get("root_cause"),
        }

        langfuse.create_dataset_item(
            dataset_name=config["name"],
            input=item_input,
            expected_output=expected_output,
            metadata=metadata,
        )
        created += 1

        if created % 100 == 0:
            logger.info("dataset_progress", created=created, total=len(filtered))

    langfuse.flush()

    stats = {
        "dataset": config["name"],
        "total_fetched": len(records),
        "filtered": len(filtered),
        "created": created,
    }
    logger.info("dataset_loaded", **stats)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Load eval datasets into Langfuse")
    parser.add_argument(
        "--dataset",
        choices=["golden", "good", "full", "all"],
        default="all",
        help="Which dataset to load (default: all)",
    )
    args = parser.parse_args()

    if args.dataset == "all":
        for key in ["golden", "good", "full"]:
            stats = load_dataset(key)
            print(f"{stats['dataset']}: {stats['created']} items loaded")
    else:
        stats = load_dataset(args.dataset)
        print(f"{stats['dataset']}: {stats['created']} items loaded")


if __name__ == "__main__":
    main()
