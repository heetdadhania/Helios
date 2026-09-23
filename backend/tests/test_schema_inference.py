import json
import unittest
from unittest.mock import MagicMock, patch

from pipeline.schema_inference.column_matcher import (
    match_column,
    match_columns_to_template,
    normalize_column_name,
)
from pipeline.schema_inference.date_detector import (
    detect_date_format,
    is_date_like,
    standardize_date,
)
from pipeline.schema_inference.inference_engine import (
    infer_schema_for_batch,
    infer_types_for_records,
    save_inferred_schema,
    score_template_fit,
)
from pipeline.schema_inference.template_definitions import (
    TEMPLATE_ORDERS,
    TEMPLATE_SHIPPING,
    get_template,
)
from pipeline.schema_inference.type_detector import infer_column_type


class TestDateDetector(unittest.TestCase):
    """Test date recognition and format standardization."""

    def test_is_date_like_valid(self):
        self.assertTrue(is_date_like("2024-03-15"))
        self.assertTrue(is_date_like("03/15/2024"))
        self.assertTrue(is_date_like("2024-03-15 14:30:00"))
        self.assertTrue(is_date_like("March 15, 2024"))

    def test_is_date_like_invalid_and_edge_cases(self):
        self.assertFalse(is_date_like("12345"))  # pure digits / zip codes
        self.assertFalse(is_date_like("90210"))
        self.assertFalse(is_date_like("100.50"))  # numeric amount
        self.assertFalse(is_date_like("hello world"))
        self.assertFalse(is_date_like(None))
        self.assertFalse(is_date_like(""))

    def test_detect_date_format(self):
        self.assertEqual(detect_date_format("2024-03-15"), "%Y-%m-%d")
        self.assertEqual(detect_date_format("03/15/2024"), "%m/%d/%Y")
        self.assertEqual(detect_date_format("2024-03-15 12:00:00"), "%Y-%m-%d %H:%M:%S")

    def test_standardize_date(self):
        std = standardize_date("03/15/2024 10:30:00")
        self.assertIsNotNone(std)
        self.assertTrue(std.startswith("2024-03-15T10:30:00"))
        self.assertIsNone(standardize_date("invalid_text"))


class TestTypeDetector(unittest.TestCase):
    """Test rule-based column data type inference."""

    def test_infer_currency(self):
        vals = ["$10.50", "$25.00", "$100.99"]
        self.assertEqual(infer_column_type(vals), "decimal")
        euro_vals = ["€15.00", "€30.50"]
        self.assertEqual(infer_column_type(euro_vals), "decimal")

    def test_infer_integer(self):
        vals = [1, 2, "3", "4", 5]
        self.assertEqual(infer_column_type(vals), "integer")

    def test_infer_decimal(self):
        vals = [10.5, "25.75", 100.0]
        self.assertEqual(infer_column_type(vals), "decimal")

    def test_infer_boolean(self):
        vals = ["true", "false", True, "yes"]
        self.assertEqual(infer_column_type(vals), "boolean")

    def test_infer_timestamp(self):
        vals = ["2024-01-01", "2024-01-02", "2024-01-03"]
        self.assertEqual(infer_column_type(vals), "timestamp")

    def test_infer_string_fallback(self):
        vals = ["FedEx", "DHL", "United Parcel Service"]
        self.assertEqual(infer_column_type(vals), "string")


class TestColumnMatcher(unittest.TestCase):
    """Test fuzzy column name matching and collision resolution."""

    def test_normalize_column_name(self):
        self.assertEqual(normalize_column_name(" Order ID "), "order_id")
        self.assertEqual(normalize_column_name("Total-Amount ($)"), "total_amount")

    def test_match_column_exact(self):
        fields = TEMPLATE_ORDERS["fields"]
        match = match_column("order_id", fields)
        self.assertIsNotNone(match)
        self.assertEqual(match["target_field"], "order_id")
        self.assertEqual(match["score"], 100.0)
        self.assertTrue(match["is_exact"])

    def test_match_column_alias(self):
        fields = TEMPLATE_ORDERS["fields"]
        match = match_column("ord_no", fields)
        self.assertIsNotNone(match)
        self.assertEqual(match["target_field"], "order_id")
        self.assertEqual(match["matched_alias"], "ord_no")

    def test_match_column_fuzzy(self):
        fields = TEMPLATE_ORDERS["fields"]
        match = match_column("client_email_addr", fields, threshold=75.0)
        self.assertIsNotNone(match)
        self.assertEqual(match["target_field"], "customer_email")

    def test_match_column_below_threshold(self):
        fields = TEMPLATE_ORDERS["fields"]
        match = match_column("unrelated_xyz_column", fields, threshold=80.0)
        self.assertIsNone(match)

    def test_match_columns_to_template_collision_resolution(self):
        cols = ["order_id", "order_num"]
        matches = match_columns_to_template(cols, TEMPLATE_ORDERS)
        # order_id is exact canonical match (100.0 score)
        self.assertIsNotNone(matches["order_id"])
        self.assertEqual(matches["order_id"]["target_field"], "order_id")
        # order_num collides on order_id, lower or equal priority should yield only one winner
        # In our implementation, best score wins, demoting duplicate
        assigned_targets = [m["target_field"] for m in matches.values() if m]
        self.assertEqual(assigned_targets.count("order_id"), 1)


class TestInferenceEngine(unittest.TestCase):
    """Test full inference engine orchestration, template scoring, and persistence."""

    def test_score_template_fit_orders(self):
        incoming_cols = ["order_id", "customer_email", "total_amount", "order_date", "status"]
        orders_score, _ = score_template_fit(incoming_cols, TEMPLATE_ORDERS)
        shipping_score, _ = score_template_fit(incoming_cols, TEMPLATE_SHIPPING)

        self.assertGreater(orders_score, 0.70)
        self.assertGreater(orders_score, shipping_score)

    def test_score_template_fit_shipping(self):
        incoming_cols = ["shipment_id", "tracking_number", "carrier", "shipped_at"]
        orders_score, _ = score_template_fit(incoming_cols, TEMPLATE_ORDERS)
        shipping_score, _ = score_template_fit(incoming_cols, TEMPLATE_SHIPPING)

        self.assertGreater(shipping_score, 0.70)
        self.assertGreater(shipping_score, orders_score)

    def test_infer_types_for_records(self):
        records = [
            {"order_id": "ORD-1", "total": "$99.50", "items": 3},
            {"order_id": "ORD-2", "total": "$149.00", "items": 5},
        ]
        types = infer_types_for_records(records)
        self.assertEqual(types["order_id"], "string")
        self.assertEqual(types["total"], "decimal")
        self.assertEqual(types["items"], "integer")

    def test_infer_schema_for_batch_success(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("batch-xyz",)

        records = [
            {
                "order_id": "ORD-101",
                "customer_email": "jane@example.com",
                "total_amount": 125.50,
                "order_date": "2024-03-01",
                "status": "completed",
            }
        ]

        result = infer_schema_for_batch(
            batch_id="batch-xyz",
            tenant_id=1,
            records=records,
            catalog="helios",
            cursor=mock_cursor,
        )

        self.assertEqual(result["detected_template"], "template_orders")
        self.assertGreaterEqual(result["confidence_score"], 0.70)
        self.assertFalse(result["flagged_for_review"])
        self.assertEqual(result["status"], "awaiting_confirmation")

        # Verify SQL writes:
        calls = mock_cursor.execute.call_args_list
        inferred_insert_found = False

        for call in calls:
            sql, params = call[0]
            if "inferred_schema" in sql:
                inferred_insert_found = True
                self.assertEqual(params["batch_id"], "batch-xyz")
                self.assertEqual(params["detected_template"], "template_orders")
                self.assertIsInstance(params["column_mapping_json"], str)
                # Confirm confirmed_by and confirmed_at are NOT set
                self.assertIn("NULL", sql)

        self.assertTrue(inferred_insert_found, "Expected platform.inferred_schema insertion")

    def test_infer_schema_flagged_for_low_confidence(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("batch-low",)

        # Batch with ambiguous/unmatched columns
        records = [{"misc_col_1": "abc", "random_notes": "foo"}]

        result = infer_schema_for_batch(
            batch_id="batch-low",
            tenant_id=1,
            records=records,
            catalog="helios",
            cursor=mock_cursor,
        )

        self.assertLess(result["confidence_score"], 0.70)
        self.assertTrue(result["flagged_for_review"])
        self.assertEqual(result["status"], "awaiting_confirmation")


if __name__ == "__main__":
    unittest.main()
