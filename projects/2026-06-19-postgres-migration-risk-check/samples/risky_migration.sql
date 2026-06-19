-- A deliberately risky migration for local testing.

CREATE INDEX idx_orders_customer_id ON orders (customer_id);

ALTER TABLE customers
  ADD COLUMN billing_account_id uuid NOT NULL;

ALTER TABLE invoices
  ALTER COLUMN external_id SET NOT NULL;

LOCK TABLE payments IN ACCESS EXCLUSIVE MODE;

ALTER TABLE legacy_events
  DROP COLUMN raw_payload;

DROP TABLE abandoned_carts;
