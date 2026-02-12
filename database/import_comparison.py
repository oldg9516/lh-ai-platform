"""Import ai_human_comparison JSON into local Supabase DB."""

import json
import subprocess
import sys


# Fields that are JSONB in the schema — need json.dumps() before SQL escape
JSONB_FIELDS = {"subscription_info", "tracking_info", "changes", "improvement_suggestions"}

# Fields from JOIN that don't exist in ai_human_comparison table — skip them
SKIP_FIELDS = {"identification", "box_contents_info", "user_info"}


def escape_sql(v, is_jsonb: bool = False):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)

    if is_jsonb:
        # Ensure value is valid JSON string
        if isinstance(v, (dict, list)):
            json_str = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, str):
            # Validate and re-serialize to ensure proper JSON
            try:
                parsed = json.loads(v)
                json_str = json.dumps(parsed, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                return "NULL"
        else:
            return "NULL"
        escaped = json_str.replace("'", "''")
        return f"'{escaped}'::jsonb"

    s = str(v)
    escaped = s.replace("'", "''")
    return f"'{escaped}'"


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "database/ai_human_comparison.json"

    with open(json_path) as f:
        data = json.load(f)

    print(f"Importing {len(data)} records into ai_human_comparison...")

    ok = 0
    errors = 0
    for i, row in enumerate(data):
        cols = []
        vals = []
        for k, v in row.items():
            if k in SKIP_FIELDS:
                continue
            cols.append(k)
            vals.append(escape_sql(v, is_jsonb=(k in JSONB_FIELDS)))

        col_str = ", ".join(cols)
        val_str = ", ".join(vals)
        sql = f"INSERT INTO ai_human_comparison ({col_str}) VALUES ({val_str}) ON CONFLICT (thread_id) DO NOTHING;"

        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "supabase-db", "psql", "-U", "postgres", "-c", sql],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors += 1
            if errors <= 5:
                print(f"ERROR row {i}: {result.stderr[:300]}")
        else:
            ok += 1

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(data)}...")

    print(f"Done: {ok} imported, {errors} errors")


if __name__ == "__main__":
    main()
