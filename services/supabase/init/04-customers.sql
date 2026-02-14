-- 04-customers.sql: Normalized customer data tables.
-- Source: support_threads_data.user (JSON), subscription_info, tracking_info.

-- Customers (from `user` JSON field)
CREATE TABLE IF NOT EXISTS customers (
    id              BIGSERIAL PRIMARY KEY,
    external_id     INTEGER,
    customer_number TEXT,
    email           TEXT NOT NULL,
    name            TEXT,
    phone           TEXT,
    street          TEXT,
    address_line_2  TEXT,
    city            TEXT,
    state           TEXT,
    zip_code        TEXT,
    country         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_external_id ON customers(external_id);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);

-- Subscriptions (from subscription_info.subscriptions[])
CREATE TABLE IF NOT EXISTS subscriptions (
    id                  BIGSERIAL PRIMARY KEY,
    customer_id         BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    customer_number     TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'Active',
    frequency           TEXT NOT NULL DEFAULT 'Monthly',
    start_date          TIMESTAMPTZ,
    first_box_price     NUMERIC(10, 2),
    regular_box_price   NUMERIC(10, 2),
    price_currency      TEXT DEFAULT 'USD',
    billing_day         INTEGER,
    no_alcohol          BOOLEAN DEFAULT false,
    no_honey            BOOLEAN DEFAULT false,
    pause_end_date      TIMESTAMPTZ,
    payer_name          TEXT,
    payer_email         TEXT,
    payment_method      TEXT,
    payment_method_id   TEXT,
    payment_expire_date TEXT,
    next_payment_date   DATE,
    next_box_sequence   INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_number ON subscriptions(customer_number);
CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

-- Orders: subscription boxes + one-time orders
CREATE TABLE IF NOT EXISTS orders (
    id                   BIGSERIAL PRIMARY KEY,
    subscription_id      BIGINT REFERENCES subscriptions(id) ON DELETE SET NULL,
    customer_id          BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    order_type           TEXT NOT NULL DEFAULT 'subscription',
    box_sequence         INTEGER,
    box_name             TEXT,
    sku                  TEXT,
    price                NUMERIC(10, 2),
    price_currency       TEXT DEFAULT 'USD',
    payment_date_planned DATE,
    payment_date_actual  TIMESTAMPTZ,
    shipping_date        TIMESTAMPTZ,
    tracking_number      TEXT,
    invoice              TEXT,
    order_status         TEXT,
    promo_code           TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_subscription ON orders(subscription_id);
CREATE INDEX IF NOT EXISTS idx_orders_tracking ON orders(tracking_number);
CREATE INDEX IF NOT EXISTS idx_orders_payment_date ON orders(payment_date_actual DESC);

-- Tracking events (from tracking_info JSON)
CREATE TABLE IF NOT EXISTS tracking_events (
    id              BIGSERIAL PRIMARY KEY,
    tracking_number TEXT NOT NULL,
    order_id        BIGINT REFERENCES orders(id) ON DELETE SET NULL,
    carrier         TEXT,
    delivery_status TEXT,
    delivery_date   TIMESTAMPTZ,
    history         JSONB DEFAULT '[]'::jsonb,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tracking_number ON tracking_events(tracking_number);
CREATE INDEX IF NOT EXISTS idx_tracking_order ON tracking_events(order_id);
