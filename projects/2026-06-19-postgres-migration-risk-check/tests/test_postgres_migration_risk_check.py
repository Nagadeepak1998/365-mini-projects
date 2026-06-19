import unittest

from postgres_migration_risk_check import collect_findings, split_statements


class PostgresMigrationRiskCheckTests(unittest.TestCase):
    def test_risky_patterns_are_flagged(self):
        sql = """
        CREATE INDEX idx_orders_customer_id ON orders (customer_id);
        ALTER TABLE customers ADD COLUMN billing_account_id uuid NOT NULL;
        ALTER TABLE invoices ALTER COLUMN external_id SET NOT NULL;
        LOCK TABLE payments IN ACCESS EXCLUSIVE MODE;
        ALTER TABLE legacy_events DROP COLUMN raw_payload;
        DROP TABLE abandoned_carts;
        """

        findings = collect_findings(sql)
        codes = {finding.code for finding in findings}

        self.assertEqual(len(findings), 6)
        self.assertIn("non-concurrent-index", codes)
        self.assertIn("add-not-null-without-default", codes)
        self.assertIn("set-not-null", codes)
        self.assertIn("explicit-table-lock", codes)
        self.assertIn("drop-column", codes)
        self.assertIn("drop-table", codes)

    def test_safer_migration_passes(self):
        sql = """
        CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);
        ALTER TABLE customers ADD COLUMN billing_account_id uuid;
        ALTER TABLE customers ALTER COLUMN billing_account_id SET DEFAULT gen_random_uuid();
        """

        self.assertEqual(collect_findings(sql), [])

    def test_comments_are_ignored(self):
        sql = """
        -- DROP TABLE mentioned in a comment should not count.
        CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders (customer_id);
        /*
          ALTER TABLE users DROP COLUMN old_name;
        */
        SELECT 'DROP TABLE inside a string is just text';
        """

        self.assertEqual(collect_findings(sql), [])

    def test_multiline_statements_keep_start_line(self):
        sql = "\n\nALTER TABLE customers\n  ADD COLUMN owner_id uuid NOT NULL;\n"

        findings = collect_findings(sql)

        self.assertEqual(findings[0].line, 3)
        self.assertEqual(findings[0].code, "add-not-null-without-default")

    def test_split_statements_handles_multiple_statements_on_one_line(self):
        statements = split_statements("CREATE TABLE demo(id int); DROP TABLE old_demo;")

        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0][1], "CREATE TABLE demo(id int)")
        self.assertEqual(statements[1][1], "DROP TABLE old_demo")


if __name__ == "__main__":
    unittest.main()
