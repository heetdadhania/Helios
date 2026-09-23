import json
import unittest
from unittest.mock import MagicMock, patch

from pipeline.cleaning.currency_cleaner import clean_currency, clean_currency_fields
from pipeline.cleaning.date_standardizer import (
    standardize_date_fields,
    standardize_timestamp,
)
from pipeline.cleaning.dedup import deduplicate_records
from pipeline.cleaning.null_handler import handle_nulls, handle_nulls_orders, handle_nulls_shipping
from pipeline.cleaning.run_silver import run_silver_pipeline
from pipeline.cleaning.silver_writer import write_silver_records


class TestCurrencyCleaner(unittest.TestCase):
    """Test currency string normalization, symbol stripping, and accounting negatives."""

    def test_clean_currency_valid_symbols(self):
        self.assertEqual(clean_currency("$10.50"), 10.5)
        self.assertEqual(clean_currency("€ 1,250.75"), 1250.75)
        self.assertEqual(clean_currency("£99.99"), 99.99)
        self.assertEqual(clean_currency("¥500"), 500.0)
        self.assertEqual(clean_currency("₹ 1,000.50"), 1000.5)

    def test_clean_currency_accounting_negative(self):
        self.assertEqual(clean_currency("(15.75)"), -15.75)
        self.assertEqual(clean_currency("($25.00)"), -25.0)
        self.assertEqual(clean_currency("-$10.50"), -10.5)

    def test_clean_currency_invalid_and_empty(self):
        self.assertIsNone(clean_currency(None))
        self.assertIsNone(clean_currency(""))
        self.assertIsNone(clean_currency("N/A"))
        self.assertIsNone(clean_currency("free_shipping"))

    def test_clean_currency_fields(self):
        record = {"order_id": "O1", "total": "$100.50", "discount": "€5.00", "notes": "fast"}
        cleaned, errors = clean_currency_fields(record, ["total", "discount"])
        self.assertEqual(cleaned["total"], 100.5)
        self.assertEqual(cleaned["discount"], 5.0)
        self.assertEqual(len(errors), 0)

        bad_record = {"order_id": "O2", "total": "invalid_amount"}
        _, errs = clean_currency_fields(bad_record, ["total"])
        self.assertIn("total", errs)


class TestDateStandardizer(unittest.TestCase):
    """Test date parsing and standardization to canonical ISO-8601 strings."""

    def test_standardize_timestamp_valid(self):
        res1 = standardize_timestamp("2024-03-15")
        self.assertEqual(res1, "2024-03-15 00:00:00")

        res2 = standardize_timestamp("03/15/2024 14:30:00")
        self.assertEqual(res2, "2024-03-15 14:30:00")

    def test_standardize_timestamp_guards_numeric_ids(self):
        self.assertIsNone(standardize_timestamp("12345"))
        self.assertIsNone(standardize_timestamp("90210"))
        self.assertIsNone(standardize_timestamp(None))
        self.assertIsNone(standardize_timestamp("not_a_date"))

    def test_standardize_date_fields(self):
        rec = {"order_id": "O1", "order_date": "2024-01-01", "created_at": "01/01/2024 10:00:00"}
        cleaned, errors = standardize_date_fields(rec, ["order_date", "created_at"])
        self.assertEqual(cleaned["order_date"], "2024-01-01 00:00:00")
        self.assertEqual(cleaned["created_at"], "2024-01-01 10:00:00")
        self.assertEqual(len(errors), 0)


class TestNullHandler(unittest.TestCase):
    """Test null imputation and required field enforcement."""

    def test_orders_rejects_missing_order_id(self):
        records = [{"customer_id": "C1", "total": 100.0}]
        valid, rejected = handle_nulls_orders(records)
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(rejected), 1)
        self.assertIn("missing_required_key: order_id", rejected[0]["rejection_reason"])

    def test_orders_imputes_defaults_and_calculates_total(self):
        records = [
            {
                "order_id": "ORD-1",
                "customer_id": "C1",
                "unit_price": 25.0,
                "quantity": 4,
                "discount": 5.0,
                # total missing -> calculated 25 * 4 - 5 = 95.0
            }
        ]
        valid, rejected = handle_nulls_orders(records)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["total"], 95.0)
        self.assertEqual(valid[0]["quantity"], 4)

    def test_shipping_imputes_defaults(self):
        records = [{"order_id": "ORD-10"}]
        valid, rejected = handle_nulls_shipping(records)
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["shipping_mode"], "Standard")
        self.assertEqual(valid[0]["delivery_status"], "Unknown")


class TestDeduplication(unittest.TestCase):
    """Test natural key deduplication and rejection logging."""

    def test_deduplicate_records_by_order_id(self):
        records = [
            {"order_id": "ORD-1", "total": 100.0},
            {"order_id": "ORD-2", "total": 200.0},
            {"order_id": "ORD-1", "total": 150.0},  # duplicate
        ]
        unique, duplicates = deduplicate_records(records, key_fields=("order_id",))
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]["order_id"], "ORD-1")
        self.assertIn("duplicate_natural_key", duplicates[0]["rejection_reason"])


class TestSilverWriter(unittest.TestCase):
    """Test inserting valid rows to Silver and logging rejections to meta.data_quality_log."""

    def test_write_silver_orders_and_rejections(self):
        mock_cursor = MagicMock()
        valid = [
            {"order_id": "O1", "customer_id": "C1", "quantity": 2, "unit_price": 50.0, "total": 100.0, "discount": 0.0}
        ]
        rejected = [
            {"order_id": "O2", "rejection_reason": "missing_required_key: order_id"}
        ]

        result = write_silver_records(
            cursor=mock_cursor,
            catalog="helios",
            batch_id="batch-123",
            tenant_id=5,
            template_name="template_orders",
            valid_records=valid,
            rejected_records=rejected,
        )

        self.assertEqual(result["valid_written"], 1)
        self.assertEqual(result["rejected_logged"], 1)

        # Verify SQL executions
        executed_sqls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        self.assertTrue(any("silver`.`orders_clean" in sql for sql in executed_sqls))
        self.assertTrue(any("meta`.`data_quality_log" in sql for sql in executed_sqls))


class TestRunSilverOrchestration(unittest.TestCase):
    """Test full Silver pipeline orchestration and status progression."""

    def test_run_silver_pipeline_success(self):
        mock_cursor = MagicMock()
        # Mock metadata query: (tenant_id, template_name, column_mapping_json)
        mock_cursor.fetchone.return_value = (
            5,
            "template_orders",
            json.dumps({"ord_num": {"target_field": "order_id"}, "amt": {"target_field": "total"}}),
        )

        # Mock Bronze raw fetch:
        mock_cursor.fetchall.return_value = [
            (json.dumps({"ord_num": "ORD-100", "amt": "$150.00", "qty": 2}),),
            (json.dumps({"ord_num": "ORD-101", "amt": "$75.00"}),),
        ]

        result = run_silver_pipeline(batch_id="batch-abc", catalog="helios", cursor=mock_cursor)

        self.assertEqual(result["status"], "gold_running")
        self.assertEqual(result["clean_rows"], 2)
        self.assertEqual(result["rejected_rows"], 0)

        # Verify pipeline_status update to gold_running
        calls = mock_cursor.execute.call_args_list
        found_gold_status = False
        found_audit_log = False

        for call in calls:
            sql, params = call[0]
            if "pipeline_status" in sql and params.get("status") == "gold_running":
                found_gold_status = True
                self.assertEqual(params["stage"], "gold_transform")
            if "etl_audit_log" in sql and params.get("status") == "completed":
                found_audit_log = True
                self.assertEqual(params["stage"], "silver_clean")

        self.assertTrue(found_gold_status, "Expected status to be updated to gold_running")
        self.assertTrue(found_audit_log, "Expected audit log record with stage silver_clean")

    def test_run_silver_pipeline_failure_updates_status(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5, "template_orders", "{}")

        with patch("pipeline.cleaning.run_silver._fetch_bronze_records", side_effect=RuntimeError("Bronze read failure")):
            with self.assertRaises(RuntimeError):
                run_silver_pipeline(batch_id="batch-fail", catalog="helios", cursor=mock_cursor)

        # Verify failure recorded in pipeline_status with stage='silver'
        calls = mock_cursor.execute.call_args_list
        found_failure = False

        for call in calls:
            sql, params = call[0]
            if "pipeline_status" in sql and params.get("status") == "failed":
                found_failure = True
                self.assertEqual(params["stage"], "silver")
                self.assertIn("Bronze read failure", params["error_message"])

        self.assertTrue(found_failure, "Expected failure status in pipeline_status")


if __name__ == "__main__":
    unittest.main()
