-- A safer migration shape for local testing.

CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);

ALTER TABLE customers
  ADD COLUMN billing_account_id uuid;

UPDATE customers
SET billing_account_id = gen_random_uuid()
WHERE billing_account_id IS NULL;

ALTER TABLE customers
  ALTER COLUMN billing_account_id SET DEFAULT gen_random_uuid();
