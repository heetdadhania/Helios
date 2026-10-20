import csv
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import openpyxl
import pandas as pd

logger = logging.getLogger("helios.pipeline.read_source")

SHIPPING_KEYWORDS = {
    "tracking",
    "carrier",
    "shipment",
    "shipping",
    "shipped_at",
    "delivery",
    "delivered_at",
    "freight",
    "waybill",
    "consignee",
}


def _read_csv_content(content_stream: io.StringIO) -> List[Dict[str, Any]]:
    """Read CSV stream preserving raw values without type truncation."""
    reader = csv.DictReader(content_stream)
    return [dict(row) for row in reader if any(v is not None and str(v).strip() != "" for v in row.values())]


def _read_excel_stream(file_stream: io.BytesIO) -> List[Dict[str, Any]]:
    """Read Excel stream with openpyxl preserving raw cell representations."""
    wb = openpyxl.load_workbook(file_stream, data_only=True, read_only=True)
    sheet = wb.active
    if sheet is None:
        wb.close()
        return []

    rows_iter = sheet.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if not header_row:
        wb.close()
        return []

    headers = [str(col) if col is not None else f"col_{idx}" for idx, col in enumerate(header_row)]
    results: List[Dict[str, Any]] = []

    for row in rows_iter:
        if any(cell is not None and str(cell).strip() != "" for cell in row):
            record = {headers[i]: row[i] if i < len(row) else None for i in range(len(headers))}
            results.append(record)

    wb.close()
    return results


def _read_file_from_disk(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load tabular data from disk using extension-specific parser."""
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Source file not found at path: {file_path}")

    ext = path_obj.suffix.lower()
    if ext == ".csv":
        with open(path_obj, "r", encoding="utf-8-sig", errors="replace") as f:
            return _read_csv_content(io.StringIO(f.read()))
    elif ext in (".xlsx", ".xls"):
        with open(path_obj, "rb") as f:
            return _read_excel_stream(io.BytesIO(f.read()))
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Must be .csv or .xlsx.")


def read_source(
    source: Union[
        str,
        Path,
        bytes,
        io.IOBase,
        List[Dict[str, Any]],
        Tuple[List[str], List[Sequence[Any]]],
        pd.DataFrame,
    ],
    columns: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Universal reader normalizing files, query tuples, and API payloads into List[Dict[str, Any]].
    
    Preserves raw data as-is without premature type coercion or cleaning.
    """
    if isinstance(source, list):
        if not source:
            return []
        if isinstance(source[0], dict):
            # Already normalized API push or dictionary rows
            return [dict(item) for item in source]
        elif columns:
            return [dict(zip(columns, row)) for row in source]
        raise ValueError("List of rows provided without required 'columns' definition.")

    if isinstance(source, tuple) and len(source) == 2:
        # Tuple of (column_headers, row_tuples) from database query result
        cols, rows = source
        return [dict(zip(cols, row)) for row in rows]

    if isinstance(source, pd.DataFrame):
        return source.where(pd.notnull(source), None).to_dict(orient="records")

    if isinstance(source, (str, Path)):
        return _read_file_from_disk(source)

    if isinstance(source, bytes):
        # Attempt decoding as CSV; fallback to Excel BytesIO
        try:
            text = source.decode("utf-8-sig")
            return _read_csv_content(io.StringIO(text))
        except UnicodeDecodeError:
            return _read_excel_stream(io.BytesIO(source))

    if isinstance(source, io.StringIO):
        return _read_csv_content(source)

    if isinstance(source, io.BytesIO):
        return _read_excel_stream(source)

    raise TypeError(f"Unsupported source input type: {type(source)}")


def detect_target_table(
    records: List[Dict[str, Any]],
    hint: Optional[str] = None,
) -> str:
    """Infer target table ('raw_orders' or 'raw_shipping') based on column keywords or explicit hint."""
    if hint:
        normalized_hint = hint.strip().lower()
        if "ship" in normalized_hint:
            return "raw_shipping"
        if "order" in normalized_hint:
            return "raw_orders"

    if not records:
        return "raw_orders"

    sample_keys = {str(k).lower().strip() for k in records[0].keys()}
    is_shipping = any(any(kw in key for kw in SHIPPING_KEYWORDS) for key in sample_keys)

    return "raw_shipping" if is_shipping else "raw_orders"
