# Helios Schema Inference Engine

A lightweight, rule-based, and explainable schema detection engine that inspects ingested Bronze batches (from file uploads, database connections, or API pushes), classifies the batch into a canonical template (`template_orders` or `template_shipping`), and maps source column names to standardized Silver-layer fields.

---

## 1. Overview & Architecture

```
Bronze Ingest Batch
        │
        ├──> Type Inference (pipeline/schema_inference/type_detector.py)
        │       ├── Currency regex (₹ Rs. INR $ € £ ¥)
        │       ├── Date & Timestamp detection (dateutil + safeguards)
        │       ├── Numeric integer / decimal rules
        │       └── Boolean / String fallback
        │
        ├──> Column Fuzzy Matching (pipeline/schema_inference/column_matcher.py)
        │       ├── RapidFuzz token sort matching
        │       ├── Exact matching against canonical names & aliases
        │       └── One-to-one conflict resolution
        │
        └──> Template Scoring & Persistence (pipeline/schema_inference/inference_engine.py)
                ├── Fit score blend: Required fields (40%) + Coverage (35%) + Similarity (25%)
                ├── Review threshold: confidence_score >= 0.7 (High) vs < 0.7 (Flagged)
                ├── Registry write: platform.inferred_schema (confirmed_by = NULL)
                └── Pipeline status: updated to 'awaiting_confirmation'
```

---

## 2. Plain-Language Explanation of the Matching Algorithm

### Step 1: Column Normalization
Incoming column names are stripped of leading/trailing whitespace, converted to lowercase, and delimiters (`-`, `.`, ` `) are converted to underscores (e.g. `"Order Total ($)"` becomes `"order_total"`).

### Step 2: Canonical & Alias Matching with RapidFuzz
Each incoming column is compared against all registered fields and their domain aliases:
1. **Exact Match**: If the normalized incoming name matches a field or alias exactly, it immediately receives a 100% score.
2. **Fuzzy Match**: If not an exact match, RapidFuzz (`fuzz.token_sort_ratio`) calculates token similarity against the field's canonical name and its predefined aliases (e.g. matching `"ord_id"` to `"order_id"`).
3. **Threshold Filtering**: Only candidates with a score `>= 80%` (configurable) are considered viable matches.
4. **Collision Resolution**: If two incoming columns match the same canonical target, the column with the highest similarity score wins the target mapping.

### Step 3: Type & Format Inference
For each column, sample values from the Bronze batch are evaluated using statistical heuristics without heavy machine learning:
- **Currency Detection**: Strips currency symbols (`₹`, `Rs.`, `INR`, `/ -`, `$`, `€`, `£`, `¥`) and verifies numerical digits.
- **Date/Timestamp Detection**: Distinguishes actual calendar dates (ISO 8601, US/European formats) from numeric codes (e.g., zip codes, phone numbers, numeric IDs) and normalizes timestamps.
- **Numeric & Boolean Detection**: Detects integer, decimal/float, and true/false values.

### Step 4: Template Scoring & Confidence Rating
The engine compares the matched columns against `template_orders` and `template_shipping`:
- **Required Fields (Weight: 40%)**: Tests whether essential primary keys are present (`order_id` for orders, `shipment_id`/`tracking_number` for shipping). Missing required fields heavily penalizes the score.
- **Field Coverage (Weight: 35%)**: Fraction of template fields matched by incoming columns.
- **Average Match Similarity (Weight: 25%)**: Average fuzzy match score across all matched columns.
- **Confidence Rating**:
  - `confidence_score >= 0.7`: High-confidence match.
  - `confidence_score < 0.7`: Flagged for extra scrutiny in the Admin Portal.

---

## 3. Human Confirmation Guarantee (No Auto-Confirmation)

Automated schema inference assists the user but **never commits unreviewed transformations into Silver production tables**.
- Records written to `platform.inferred_schema` explicitly set `confirmed_by = NULL` and `confirmed_at = NULL`.
- `platform.pipeline_status` is transitioned to `awaiting_confirmation` under the `schema_inference` stage.
- Only an SMB owner or administrator in the Client/Admin Portal (Module 8) can review, modify mappings if desired, and confirm the batch for Silver transformation.
