"""Import support_threads_data JSON into local Supabase DB."""

import json
import subprocess
import sys


def escape_sql(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    escaped = str(v).replace("'", "''")
    return f"'{escaped}'"


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else "database/support_threads_data.json"

    with open(json_path) as f:
        data = json.load(f)

    print(f"Importing {len(data)} records...")

    ok = 0
    errors = 0
    for i, row in enumerate(data):
        cols = []
        vals = []
        for k, v in row.items():
            cols.append(f'"{k}"' if k == "user" else k)
            vals.append(escape_sql(v))

        col_str = ", ".join(cols)
        val_str = ", ".join(vals)
        sql = f"INSERT INTO support_threads_data ({col_str}) VALUES ({val_str}) ON CONFLICT (thread_id) DO NOTHING;"

        result = subprocess.run(
            ["docker", "compose", "exec", "-T", "supabase-db", "psql", "-U", "postgres", "-c", sql],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors += 1
            if errors <= 3:
                print(f"ERROR row {i}: {result.stderr[:200]}")
        else:
            ok += 1

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(data)}...")

    print(f"Done: {ok} imported, {errors} errors")


if __name__ == "__main__":
    main()
