"""Import ai_answerer_instructions JSON into local Supabase DB."""

import json
import subprocess
import sys


def escape_sql(v):
    """Escape a value for SQL insertion."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    escaped = str(v).replace("'", "''")
    return f"'{escaped}'"


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "database/ai_answerer_instructions.json"

    with open(json_path) as f:
        data = json.load(f)

    print(f"Importing {len(data)} records...")

    for row in data:
        cols = []
        vals = []
        for k, v in row.items():
            cols.append(f'"{k}"' if k in ("user",) else k)
            vals.append(escape_sql(v))

        col_str = ", ".join(cols)
        val_str = ", ".join(vals)
        sql = f"INSERT INTO ai_answerer_instructions ({col_str}) VALUES ({val_str});"

        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "supabase-db", "psql", "-U", "postgres", "-c", sql],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"ERROR id={row['id']}: {result.stderr[:300]}")
        else:
            print(f"OK id={row['id']} type={row.get('type', '?')}")


if __name__ == "__main__":
    main()
