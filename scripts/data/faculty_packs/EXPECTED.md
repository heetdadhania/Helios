# Faculty Demonstration Packs — Expected Results & Verification Guide

This document defines the purpose, schema, data characteristics, and verified execution results for all demonstration test packs generated for faculty evaluation of the **Helios Multi-Tenant Medallion Pipeline**.

All packs were generated with fixed seed `2026` via `scripts/data/generate_faculty_packs.py` and executed against the dedicated demonstration tenant **Faculty Demo Traders** (Tenant ID `16`) through the standard Team Member ingestion workflow (`/api/v1/uploads` -> schema preview -> confirmation -> Silver cleaning -> Gold aggregation).

---

## Master Summary Table

| File Name | Format | Total Rows | Expected Accepted (Silver) | Expected Rejected | Gold Fact Rows | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `clean_10_orders.csv` | CSV | 10 | 10 | 0 | 10 | Ingested cleanly; 100% data completeness |
| `clean_10_shipping.csv` | CSV | 10 | 10 | 0 | 0 | Companion shipping records for 10 orders |
| `clean_50_orders.csv` | CSV | 50 | 50 | 0 | 50 | Standard 50-row CSV orders benchmark |
| `clean_50_shipping.csv` | CSV | 50 | 50 | 0 | 0 | Companion shipping records for 50 orders |
| `clean_50_orders.xlsx` | Excel | 50 | 50 | 0 | 50 | OpenPyXL Excel parser validation |
| `clean_50_shipping.xlsx` | Excel | 50 | 50 | 0 | 0 | Excel parser shipping benchmark |
| `err01_blank_quantity_orders.csv` | CSV | 15 | 12 | 3 | 12 | Missing required numeric field |
| `err02_negative_quantity_orders.csv` | CSV | 15 | 12 | 3 | 12 | Value constraint (`quantity > 0`) violation |
| `err03_zero_or_negative_price_orders.csv` | CSV | 15 | 12 | 3 | 12 | Value constraint (`unit_price > 0`) violation |
| `err04_unreadable_date_orders.csv` | CSV | 15 | 12 | 3 | 12 | Unparseable / invalid date formats |
| `err05_mixed_date_formats_orders.csv` | CSV | 15 | 15 | 0 | 15 | Mixed ISO & DD/MM/YYYY standardized |
| `err06_duplicate_order_ids_orders.csv` | CSV | 15 | 12 | 3 | 12 | Line item deduplication (`order_id + product_id`) |
| `err07_missing_customer_id_orders.csv` | CSV | 15 | 12 | 3 | 12 | Mandatory foreign key null check |
| `err08_arithmetic_mismatch_orders.csv` | CSV | 15 | 12 | 3 | 12 | Arithmetic check: `total != qty * price - discount` |
| `err09_currency_text_formats_orders.csv` | CSV | 15 | 12 | 3 | 12 | Indian currency strings parsed; bad strings caught |
| `err10_renamed_headers_orders.csv` | CSV | 15 | 15 | 0 | 15 | Schema inference alias matching |
| `err11_extra_unknown_columns_orders.csv` | CSV | 15 | 15 | 0 | 15 | Schema evolution: extra unknown columns dropped |
| `err12_missing_required_column_orders.csv` | CSV | 15 | 0 | 15 | 0 | Missing mandatory canonical column |
| `err13_text_spaces_and_casing_orders.csv` | CSV | 15 | 15 | 0 | 15 | Whitespace trimming & casing normalization |
| `err14_header_only_orders.csv` | CSV | 0 | 0 | 0 | 0 | Rejected at upload boundary (HTTP 400) |

---

## Detailed Pack Breakdown & Real Rejection Reasons

### 1. Clean Benchmark Packs

#### `clean_10_orders.csv` & `clean_10_shipping.csv`
- **Purpose**: Baseline sanity check demonstrating clean ingestion and joining across Medallion layers.
- **Row Count**: 10 order rows, 10 shipping rows.
- **Accepted**: 10 orders (100%), 10 shipping (100%).
- **Rejected**: 0.
- **Gold Fact Rows**: 10 (`gold.fact_orders`).
- **Verified Batch ID**: `b54a8868-5de4-49fd-bcda-d3f370029b3a` (orders), `168a2042-b0a0-43bf-9b48-c4dc5178ade7` (shipping).

#### `clean_50_orders.csv` & `clean_50_shipping.csv`
- **Purpose**: Medium-scale CSV benchmark verifying high-throughput batching, schema inference, and fact aggregation.
- **Row Count**: 50 order rows, 50 shipping rows.
- **Accepted**: 50 orders (100%), 50 shipping (100%).
- **Rejected**: 0.
- **Gold Fact Rows**: 50 (`gold.fact_orders`).
- **Verified Batch ID**: `b11999a3-3b9a-4d64-b506-788e4ca8cf78` (orders), `43617d6c-de60-4962-9ded-6497d4a89c8f` (shipping).

#### `clean_50_orders.xlsx` & `clean_50_shipping.xlsx`
- **Purpose**: Spreadsheet ingestion verification ensuring OpenPyXL parsing parity with CSV parsing.
- **Row Count**: 50 order rows, 50 shipping rows.
- **Accepted**: 50 orders (100%), 50 shipping (100%).
- **Rejected**: 0.
- **Gold Fact Rows**: 50 (`gold.fact_orders`).
- **Verified Batch ID**: `2b9eac36-4c8a-42b1-8cf6-4abb5943c9c3` (orders), `434be08a-5561-4a4a-ba19-3ba4a1ec7eac` (shipping).

---

### 2. Data Quality & Rule Validation Packs

#### `err01_blank_quantity_orders.csv`
- **Purpose**: Verify that blank/empty string quantity values are caught by Silver null checks.
- **Row Count**: 15 rows (12 clean, 3 blank quantity).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `missing_required_key: quantity (original_value: )`
  - `ORD-FAC-00007`: `missing_required_key: quantity (original_value: )`
  - `ORD-FAC-00011`: `missing_required_key: quantity (original_value: )`
- **Verified Batch ID**: `3fdc5e93-b36c-44c3-b9a1-6deef42c06a0`.

#### `err02_negative_quantity_orders.csv`
- **Purpose**: Verify numeric range constraints (`quantity > 0`).
- **Row Count**: 15 rows (12 clean, 3 negative quantity).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `invalid_quantity: quantity must be greater than zero (original_value: -1)`
  - `ORD-FAC-00007`: `invalid_quantity: quantity must be greater than zero (original_value: -2)`
  - `ORD-FAC-00011`: `invalid_quantity: quantity must be greater than zero (original_value: -5)`
- **Verified Batch ID**: `27d4146d-2d18-46e5-ac88-05ac83dc5cb8`.

#### `err03_zero_or_negative_price_orders.csv`
- **Purpose**: Verify financial sanity checks requiring unit price to be positive non-zero.
- **Row Count**: 15 rows (12 clean, 3 zero/negative prices).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `invalid_unit_price: unit_price must be greater than zero (original_value: 0.00)`
  - `ORD-FAC-00007`: `invalid_unit_price: unit_price must be greater than zero (original_value: -499.00)`
  - `ORD-FAC-00011`: `invalid_unit_price: unit_price must be greater than zero (original_value: 0)`
- **Verified Batch ID**: `fd0857d3-2c18-4640-90bf-e9242b4c1497`.

#### `err04_unreadable_date_orders.csv`
- **Purpose**: Verify date parser resilience against non-date garbage text and impossible calendar dates.
- **Row Count**: 15 rows (12 clean, 3 invalid dates).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `invalid_date_fields: order_date (original_value: not-a-valid-date)`
  - `ORD-FAC-00007`: `invalid_date_fields: order_date (original_value: 32/13/2026)`
  - `ORD-FAC-00011`: `invalid_date_fields: order_date (original_value: unreadable_text)`
- **Verified Batch ID**: `31fa24ee-1568-4d01-ae11-dfdcda6d4fae`.

#### `err05_mixed_date_formats_orders.csv`
- **Purpose**: Verify that heterogeneous date formats common in Indian business files (`DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY`) are all standardized to ISO 8601 without rejection.
- **Row Count**: 15 rows.
- **Accepted**: 15 rows (100%).
- **Rejected**: 0 rows.
- **Transformation**: Mixed dates like `15/08/2026 10:30:00` and `2026-08-15 10:30:00` are standardized to `2026-08-15T10:30:00Z`.
- **Verified Batch ID**: `56f35ced-ad5b-43ff-a409-968e8bf9a21e`.

#### `err06_duplicate_order_ids_orders.csv`
- **Purpose**: Verify that duplicate order line items (`order_id + product_id`) within the same submission are detected and flagged.
- **Row Count**: 15 rows (12 unique lines, 3 duplicate lines).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00001`: `duplicate_order_line: duplicate line for order_id=ORD-FAC-00001, product_id=P-FAC-01`
  - `ORD-FAC-00005`: `duplicate_order_line: duplicate line for order_id=ORD-FAC-00005, product_id=P-FAC-08`
  - `ORD-FAC-00009`: `duplicate_order_line: duplicate line for order_id=ORD-FAC-00009, product_id=P-FAC-08`
- **Verified Batch ID**: `5eb41678-0e8e-43f0-a5ea-3758ba672056`.

#### `err07_missing_customer_id_orders.csv`
- **Purpose**: Verify that essential entity foreign keys cannot be null or whitespace.
- **Row Count**: 15 rows (12 clean, 3 blank customer_id).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `missing_required_key: customer_id (original_value: )`
  - `ORD-FAC-00007`: `missing_required_key: customer_id (original_value: )`
  - `ORD-FAC-00011`: `missing_required_key: customer_id (original_value: )`
- **Verified Batch ID**: `6559d17d-21b4-4bb0-bb0a-1080fe6086d4`.

#### `err08_arithmetic_mismatch_orders.csv`
- **Purpose**: Verify arithmetic reconciliation rule: `total == quantity * unit_price - discount`.
- **Row Count**: 15 rows (12 clean, 3 arithmetic mismatches).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00003`: `arithmetic_mismatch: total does not equal quantity * unit_price - discount (total=9999.0, expected=762.45, diff=9236.55)`
  - `ORD-FAC-00007`: `arithmetic_mismatch: total does not equal quantity * unit_price - discount (total=50000.0, expected=1197.0, diff=48803.0)`
  - `ORD-FAC-00011`: `arithmetic_mismatch: total does not equal quantity * unit_price - discount (total=1.0, expected=349.0, diff=348.0)`
- **Verified Batch ID**: `592425a8-bd59-4774-8f9e-ef4f6d40891b`.

#### `err09_currency_text_formats_orders.csv`
- **Purpose**: Verify that Indian rupee currency notation (`₹1,25,000.00`, `Rs. 1,250`, `Rs 1250`, `INR 899`, `1250/-`) is cleanly parsed into numeric `Decimal` values, while corrupt strings are rejected.
- **Row Count**: 15 rows (12 parseable Indian currency formats, 3 corrupt text strings).
- **Accepted**: 12 rows.
- **Rejected**: 3 rows.
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00013`: `invalid_currency_fields: unit_price could not be parsed as currency (original_value: Rs. INVALID_PRICE)`
  - `ORD-FAC-00014`: `invalid_currency_fields: total could not be parsed as currency (original_value: INR N/A)`
  - `ORD-FAC-00015`: `invalid_currency_fields: unit_price could not be parsed as currency (original_value: ₹---)`
- **Verified Batch ID**: `e7dff045-a813-4238-8168-fdf2f2ffe689`.

#### `err10_renamed_headers_orders.csv`
- **Purpose**: Verify schema inference alias matching (e.g. `order_no -> order_id`, `cust_name -> customer_name`, `qty -> quantity`, `price -> unit_price`, `total_amt -> total`).
- **Row Count**: 15 rows.
- **Accepted**: 15 rows (100%).
- **Rejected**: 0 rows.
- **Schema Mapping Confidence**: 100% exact alias matches.
- **Verified Batch ID**: `20768f5d-e765-4a58-9903-ff738e6f5db7`.

#### `err11_extra_unknown_columns_orders.csv`
- **Purpose**: Verify schema evolution and extra column resilience. Unrecognized columns (`warehouse_code`, `gift_message`) are mapped to `None` and safely ignored without pipeline failure.
- **Row Count**: 15 rows.
- **Accepted**: 15 rows (100%).
- **Rejected**: 0 rows.
- **Verified Batch ID**: `29106c46-5ea7-47ce-aae3-040f255f71b9`.

#### `err12_missing_required_column_orders.csv`
- **Purpose**: Verify behavior when an entire mandatory column (`customer_id`) is omitted from the uploaded file header.
- **Row Count**: 15 rows.
- **Accepted**: 0 rows.
- **Rejected**: 15 rows (100% of rows fail null check in Silver).
- **Logged Rejection Reason (`meta.data_quality_log`)**:
  - `ORD-FAC-00001` through `ORD-FAC-00015`: `missing_required_key: customer_id (original_value: None)`
- **Verified Batch ID**: `e8050000-653d-4bf7-ab92-e488aa232e5a`.

#### `err13_text_spaces_and_casing_orders.csv`
- **Purpose**: Verify text sanitization: trimming extraneous whitespace and normalizing mixed case category/segment strings (e.g. `"  cOnSuMeR  "` -> `"Consumer"`, `" electronics "` -> `"Electronics"`).
- **Row Count**: 15 rows.
- **Accepted**: 15 rows (100%).
- **Rejected**: 0 rows.
- **Verified Batch ID**: `71188de6-846e-4003-a158-c2d3ab40a784`.

#### `err14_header_only_orders.csv`
- **Purpose**: Verify upload boundary validation for degenerate files with headers but zero data records.
- **Row Count**: 0 data rows (header only).
- **Accepted**: 0 rows.
- **Rejected**: 0 rows (rejected at API boundary before Bronze landing).
- **HTTP Status**: `400 Bad Request`.
- **API Error Response**: `{"detail": "File contains only headers with no data rows. At least one data row is required."}`.
