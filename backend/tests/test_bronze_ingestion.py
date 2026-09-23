import io
import json
import unittest
from unittest.mock import MagicMock, patch

import openpyxl
import pandas as pd

from pipeline.ingestion.bronze_loader import load_bronze_records
from pipeline.ingestion.read_source import detect_target_table, read_source
from pipeline.ingestion.run_bronze import run_bronze_ingestion


class TestReadSource(unittest.TestCase):
    """Test source normalization across CSV, Excel, DB queries, and API push."""

    def test_read_csv_bytes(self):
        csv_bytes = b"order_id,amount,status\nORD-1,100.50,completed\nORD-2,75.00,pending\n"
        records = read_source(csv_bytes)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["order_id"], "ORD-1")
        self.assertEqual(records[0]["amount"], "100.50")
        self.assertEqual(records[1]["order_id"], "ORD-2")

    def test_read_excel_bytes(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["shipment_id", "tracking_number", "carrier"])
        ws.append(["SHP-101", "TRK-9901", "FedEx"])
        ws.append(["SHP-102", "TRK-9902", "UPS"])
        buf = io.BytesIO()
        wb.save(buf)

        records = read_source(buf.getvalue())
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["shipment_id"], "SHP-101")
        self.assertEqual(records[0]["carrier"], "FedEx")

    def test_read_db_tuples_with_headers(self):
        columns = ["order_id", "customer_id", "total"]
        rows = [("ORD-1", "CUST-A", 150.0), ("ORD-2", "CUST-B", 250.0)]
        records = read_source((columns, rows))
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0], {"order_id": "ORD-1", "customer_id": "CUST-A", "total": 150.0})
        self.assertEqual(records[1], {"order_id": "ORD-2", "customer_id": "CUST-B", "total": 250.0})

    def test_read_api_push_dict_list(self):
        payload_records = [
            {"order_id": "ORD-501", "amount": 99.0},
            {"order_id": "ORD-502", "amount": 149.0},
        ]
        records = read_source(payload_records)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["order_id"], "ORD-501")

    def test_read_pandas_dataframe(self):
        df = pd.DataFrame([{"sku": "SKU-1", "qty": 10}, {"sku": "SKU-2", "qty": 20}])
        records = read_source(df)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["sku"], "SKU-1")

    def test_detect_target_table(self):
        orders_data = [{"order_id": "O1", "customer_id": "C1", "amount": 100}]
        shipping_data = [{"shipment_id": "S1", "tracking_number": "TRK123", "carrier": "DHL"}]

        self.assertEqual(detect_target_table(orders_data), "raw_orders")
        self.assertEqual(detect_target_table(shipping_data), "raw_shipping")
        # Explicit hints override
        self.assertEqual(detect_target_table(orders_data, hint="shipping"), "raw_shipping")
        self.assertEqual(detect_target_table(shipping_data, hint="orders"), "raw_orders")


class TestBronzeLoader(unittest.TestCase):
    """Test loading records into raw Bronze Delta tables with immutable JSON."""

    def test_load_bronze_records_raw_orders(self):
        mock_cursor = MagicMock()
        records = [
            {"order_id": "ORD-1", "amount": 100, "customer": "Alice"},
            {"order_id": "ORD-2", "amount": 200, "customer": "Bob"},
        ]

        count = load_bronze_records(
            cursor=mock_cursor,
            tenant_id=7,
            batch_id="batch-uuid-123",
            source_type="upload",
            records=records,
            target_table="raw_orders",
            catalog="helios",
        )

        self.assertEqual(count, 2)
        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO `helios`.`bronze`.`raw_orders`", sql)
        self.assertEqual(params["tenant_id"], 7)
        self.assertEqual(params["batch_id"], "batch-uuid-123")
        self.assertEqual(params["source_type"], "upload")

        # Verify raw JSON preservation
        row_0 = json.loads(params["row_json_0"])
        self.assertEqual(row_0["order_id"], "ORD-1")
        self.assertEqual(row_0["customer"], "Alice")

    def test_load_bronze_records_raw_shipping(self):
        mock_cursor = MagicMock()
        records = [{"tracking_number": "TRK-1", "carrier": "UPS"}]

        count = load_bronze_records(
            cursor=mock_cursor,
            tenant_id=7,
            batch_id="batch-uuid-456",
            source_type="api_push",
            records=records,
            target_table="raw_shipping",
        )

        self.assertEqual(count, 1)
        mock_cursor.execute.assert_called_once()
        sql, params = mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO `helios`.`bronze`.`raw_shipping`", sql)
        self.assertEqual(params["source_type"], "api_push")


class TestRunBronzeOrchestration(unittest.TestCase):
    """Test orchestration entry point, audit logging, and error handling."""

    def test_run_bronze_success(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("batch-uuid-999",)  # batch already exists in pipeline_status

        records = [
            {"order_id": "ORD-1", "amount": 50.0},
            {"order_id": "ORD-2", "amount": 75.0},
        ]

        result = run_bronze_ingestion(
            tenant_id=42,
            batch_id="batch-uuid-999",
            source_type="db_connection",
            data=records,
            target_table="raw_orders",
            cursor=mock_cursor,
        )

        self.assertEqual(result["status"], "ingested")
        self.assertEqual(result["records_loaded"], 2)
        self.assertEqual(result["source_type"], "db_connection")

        # Verify calls to execute: bronze insert, pipeline_status update, audit log insert
        self.assertEqual(mock_cursor.execute.call_count, 4)

    def test_run_bronze_failure_updates_pipeline_status(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # batch does not exist

        # Simulate exception during load_bronze_records
        with patch(
            "pipeline.ingestion.run_bronze.load_bronze_records",
            side_effect=RuntimeError("Delta Lake storage write failure"),
        ):
            with self.assertRaises(RuntimeError):
                run_bronze_ingestion(
                    tenant_id=42,
                    batch_id="batch-uuid-fail",
                    source_type="upload",
                    data=[{"order_id": "ORD-FAIL"}],
                    cursor=mock_cursor,
                )

        # Verify that failure state was written to pipeline_status with stage='bronze' and status='failed'
        calls = mock_cursor.execute.call_args_list
        found_failure_update = False
        found_audit_failure = False

        for call in calls:
            sql, params = call[0]
            if params and params.get("status") == "failed":
                if "pipeline_status" in sql:
                    found_failure_update = True
                    self.assertEqual(params["stage"], "bronze")
                    self.assertIn("Delta Lake storage write failure", params["error_message"])
                elif "etl_audit_log" in sql:
                    found_audit_failure = True
                    self.assertEqual(params["status"], "failed")

        self.assertTrue(found_failure_update, "Expected pipeline_status update to failed")
        self.assertTrue(found_audit_failure, "Expected etl_audit_log failure record")


if __name__ == "__main__":
    unittest.main()
