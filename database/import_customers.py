"""Import customer data from support_threads_data into normalized tables.

ETL: Reads `user`, `subscription_info`, `tracking_info` JSON fields
from support_threads_data, deduplicates by email, and inserts into
customers, subscriptions, orders, tracking_events tables.

Usage:
    python database/import_customers.py
"""

import json
import subprocess
import sys
from datetime import datetime


def escape_sql(v):
    """Escape a value for SQL insertion."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    escaped = str(v).replace("'", "''").replace("\\", "\\\\")
    return f"'{escaped}'"


def run_sql(sql, return_id=False):
    """Execute SQL via psql and optionally return the result."""
    cmd = ["docker", "compose", "exec", "-T", "supabase-db", "psql", "-U", "postgres"]
    if return_id:
        cmd.extend(["-t", "-A", "-c", sql])
    else:
        cmd.extend(["-c", sql])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr[:300]

    if return_id:
        # psql returns the ID on the first line, then "INSERT 0 1" on the second
        first_line = result.stdout.strip().split("\n")[0].strip()
        try:
            return int(first_line), None
        except (ValueError, TypeError):
            return None, f"Could not parse ID from: {first_line}"

    return True, None


def parse_json_safe(text):
    """Parse a JSON string, returning None on failure."""
    if not text or text.strip() in ("", "null", "None"):
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def fetch_threads():
    """Fetch all support_threads_data with user or identification data."""
    cmd = [
        "docker", "compose", "exec", "-T", "supabase-db", "psql",
        "-U", "postgres", "-t", "-A", "-c",
        'SELECT row_to_json(t) FROM ('
        'SELECT thread_id, "user", identification, subscription_info, tracking_info, created_at '
        'FROM support_threads_data '
        'WHERE "user" IS NOT NULL OR identification IS NOT NULL '
        'ORDER BY created_at DESC'
        ') t;'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR fetching threads: {result.stderr[:300]}")
        sys.exit(1)

    rows = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def extract_customer(thread):
    """Extract customer info from a thread's `user` or `identification` field."""
    user_data = parse_json_safe(thread.get("user"))
    if user_data and user_data.get("email"):
        addr = user_data.get("address", {}) or {}
        return {
            "email": user_data["email"].strip().lower(),
            "name": user_data.get("name") or None,
            "phone": user_data.get("phone") or None,
            "street": addr.get("street") or None,
            "address_line_2": addr.get("address_line_2") or addr.get("address_line_3") or None,
            "city": addr.get("city") or None,
            "state": addr.get("state") or None,
            "zip_code": addr.get("zip_code") or None,
            "country": addr.get("country") or None,
            "external_id": None,
        }

    id_data = parse_json_safe(thread.get("identification"))
    if id_data and isinstance(id_data, list) and len(id_data) > 0:
        person = id_data[0]
        if person.get("email"):
            addr = person.get("address", {}) or {}
            return {
                "email": person["email"].strip().lower(),
                "name": person.get("name") or None,
                "phone": person.get("phone") or None,
                "street": addr.get("street") or None,
                "address_line_2": addr.get("address_line_2") or None,
                "city": addr.get("city") or None,
                "state": addr.get("state") or None,
                "zip_code": addr.get("zip_code") or None,
                "country": addr.get("country") or None,
                "external_id": person.get("id"),
            }

    return None


def insert_customer(cust):
    """Insert a customer and return the ID."""
    sql = (
        f"INSERT INTO customers (email, name, phone, external_id, street, address_line_2, city, state, zip_code, country) "
        f"VALUES ({escape_sql(cust['email'])}, {escape_sql(cust['name'])}, {escape_sql(cust['phone'])}, "
        f"{escape_sql(cust['external_id'])}, {escape_sql(cust['street'])}, {escape_sql(cust['address_line_2'])}, "
        f"{escape_sql(cust['city'])}, {escape_sql(cust['state'])}, {escape_sql(cust['zip_code'])}, "
        f"{escape_sql(cust['country'])}) "
        f"ON CONFLICT (email) DO UPDATE SET updated_at = NOW() "
        f"RETURNING id;"
    )
    cid, err = run_sql(sql, return_id=True)
    return cid, err


def insert_subscription(customer_id, sub_data):
    """Insert a subscription and return the ID."""
    details = sub_data.get("details", {})
    chars = sub_data.get("subscription_characteristics", {})
    payer = sub_data.get("payer", {})
    next_box = sub_data.get("next_planned_unpaid_box") or {}

    customer_number = details.get("customer_number", "")
    if not customer_number:
        return None, "No customer_number"

    sql = (
        f"INSERT INTO subscriptions "
        f"(customer_id, customer_number, status, frequency, start_date, "
        f"first_box_price, regular_box_price, price_currency, billing_day, "
        f"no_alcohol, no_honey, pause_end_date, "
        f"payer_name, payer_email, payment_method, payment_method_id, payment_expire_date, "
        f"next_payment_date, next_box_sequence) "
        f"VALUES ("
        f"{customer_id}, {escape_sql(customer_number)}, "
        f"{escape_sql(details.get('current_status', 'Active'))}, "
        f"{escape_sql(chars.get('frequency', 'Monthly'))}, "
        f"{escape_sql(chars.get('start_date'))}, "
        f"{escape_sql(chars.get('first_box_price'))}, "
        f"{escape_sql(chars.get('regular_box_price'))}, "
        f"{escape_sql(chars.get('price_currency', 'USD'))}, "
        f"{escape_sql(chars.get('billing_day'))}, "
        f"{escape_sql(details.get('no_alcohol', False))}, "
        f"{escape_sql(details.get('no_honey', False))}, "
        f"{escape_sql(details.get('pause_end_date'))}, "
        f"{escape_sql(payer.get('name'))}, "
        f"{escape_sql(payer.get('email'))}, "
        f"{escape_sql(payer.get('payment_method'))}, "
        f"{escape_sql(payer.get('payment_method_identifier'))}, "
        f"{escape_sql(payer.get('payment_method_expire_date'))}, "
        f"{escape_sql(next_box.get('payment_date_planned'))}, "
        f"{escape_sql(next_box.get('client_box_sequence_number'))}"
        f") ON CONFLICT (customer_number) DO UPDATE SET "
        f"status = EXCLUDED.status, updated_at = NOW() "
        f"RETURNING id;"
    )
    sid, err = run_sql(sql, return_id=True)
    return sid, err


def insert_order(customer_id, subscription_id, order_data, order_type="subscription"):
    """Insert an order record."""
    if order_type == "subscription":
        sql = (
            f"INSERT INTO orders "
            f"(customer_id, subscription_id, order_type, box_sequence, box_name, sku, "
            f"payment_date_planned, payment_date_actual, shipping_date, tracking_number, invoice) "
            f"VALUES ("
            f"{customer_id}, {subscription_id or 'NULL'}, 'subscription', "
            f"{escape_sql(order_data.get('client_box_sequence_number'))}, "
            f"{escape_sql(order_data.get('box_name'))}, "
            f"{escape_sql(order_data.get('sku'))}, "
            f"{escape_sql(order_data.get('payment_date_planned'))}, "
            f"{escape_sql(order_data.get('payment_date_actual'))}, "
            f"{escape_sql(order_data.get('shipping_date_actual'))}, "
            f"{escape_sql(order_data.get('tracking_number'))}, "
            f"{escape_sql(order_data.get('invoice'))}"
            f");"
        )
    else:
        details = order_data.get("details", {})
        sql = (
            f"INSERT INTO orders "
            f"(customer_id, subscription_id, order_type, price, price_currency, "
            f"tracking_number, order_status, promo_code, payment_date_actual) "
            f"VALUES ("
            f"{customer_id}, NULL, 'one_time', "
            f"{escape_sql(details.get('price'))}, "
            f"{escape_sql(details.get('price_currency', 'USD'))}, "
            f"{escape_sql(details.get('tracking_number'))}, "
            f"{escape_sql(details.get('order_status'))}, "
            f"{escape_sql(details.get('promo'))}, "
            f"{escape_sql(details.get('paid_at'))}"
            f");"
        )
    _, err = run_sql(sql)
    return err


def insert_tracking(tracking_number, tracking_data_str):
    """Insert a tracking event from tracking_info."""
    data = parse_json_safe(tracking_data_str)
    if not data:
        return

    history = data.get("history", [])
    history_json = json.dumps(history).replace("'", "''")

    sql = (
        f"INSERT INTO tracking_events "
        f"(tracking_number, delivery_status, delivery_date, history, raw_data) "
        f"VALUES ("
        f"{escape_sql(tracking_number)}, "
        f"{escape_sql(data.get('delivery_status'))}, "
        f"{escape_sql(data.get('delivery_date'))}, "
        f"'{history_json}'::jsonb, "
        f"'{json.dumps(data).replace(chr(39), chr(39)+chr(39))}'::jsonb"
        f") ON CONFLICT (tracking_number) DO NOTHING;"
    )
    run_sql(sql)


def main():
    print("Fetching threads from support_threads_data...")
    threads = fetch_threads()
    print(f"Found {len(threads)} threads with customer data")

    # Deduplicate by email: group threads, take first (most recent) for customer info
    customers_by_email = {}
    subs_by_email = {}
    tracking_by_email = {}

    for thread in threads:
        cust = extract_customer(thread)
        if not cust:
            continue

        email = cust["email"]

        # Take most recent customer identity
        if email not in customers_by_email:
            customers_by_email[email] = cust

        # Accumulate subscriptions (merge from all threads)
        sub_info = parse_json_safe(thread.get("subscription_info"))
        if sub_info:
            if email not in subs_by_email:
                subs_by_email[email] = {"subscriptions": [], "one_time_orders": []}
            for sub in sub_info.get("subscriptions", []):
                cn = sub.get("details", {}).get("customer_number", "")
                existing_cns = [
                    s.get("details", {}).get("customer_number", "")
                    for s in subs_by_email[email]["subscriptions"]
                ]
                if cn and cn not in existing_cns:
                    subs_by_email[email]["subscriptions"].append(sub)
            for oto in sub_info.get("one_time_orders", []):
                subs_by_email[email]["one_time_orders"].append(oto)

        # Accumulate tracking
        track_info = parse_json_safe(thread.get("tracking_info"))
        if track_info and isinstance(track_info, dict):
            if email not in tracking_by_email:
                tracking_by_email[email] = {}
            tracking_by_email[email].update(track_info)

    print(f"Unique customers: {len(customers_by_email)}")
    print(f"Customers with subscriptions: {len(subs_by_email)}")
    print(f"Customers with tracking: {len(tracking_by_email)}")

    # Insert customers
    customer_ids = {}
    ok = 0
    errors = 0

    for email, cust in customers_by_email.items():
        cid, err = insert_customer(cust)
        if cid:
            customer_ids[email] = cid
            ok += 1
        else:
            errors += 1
            if errors <= 5:
                print(f"  ERROR customer {email}: {err}")

    print(f"Customers: {ok} inserted, {errors} errors")

    # Insert subscriptions and orders
    sub_count = 0
    order_count = 0

    for email, sub_data in subs_by_email.items():
        cid = customer_ids.get(email)
        if not cid:
            continue

        # Update customer_number from first subscription
        subs = sub_data.get("subscriptions", [])
        if subs:
            first_cn = subs[0].get("details", {}).get("customer_number", "")
            if first_cn:
                run_sql(
                    f"UPDATE customers SET customer_number = {escape_sql(first_cn)} WHERE id = {cid};"
                )

        for sub in subs:
            sid, err = insert_subscription(cid, sub)
            if sid:
                sub_count += 1
                # Insert subscription history as orders
                for order in sub.get("subscription_history", []):
                    err = insert_order(cid, sid, order, "subscription")
                    if not err:
                        order_count += 1
            else:
                if sub_count == 0:
                    print(f"  ERROR sub {email}: {err}")

        # Insert one-time orders
        for oto in sub_data.get("one_time_orders", []):
            err = insert_order(cid, None, oto, "one_time")
            if not err:
                order_count += 1

    print(f"Subscriptions: {sub_count} inserted")
    print(f"Orders: {order_count} inserted")

    # Insert tracking events
    track_count = 0
    for email, tracks in tracking_by_email.items():
        for tn, track_data in tracks.items():
            insert_tracking(tn, track_data)
            track_count += 1

    print(f"Tracking events: {track_count} inserted")
    print("Done!")


if __name__ == "__main__":
    main()
