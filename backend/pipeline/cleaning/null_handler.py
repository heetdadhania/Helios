import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("helios.pipeline.cleaning.nulls")


def handle_nulls_orders(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Handle missing values and enforce required fields for retail orders:
    - Rejects rows missing order_id or total.
    - Imputes defaults: quantity=1, discount=0.0.
    """
    valid: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for row in records:
        r = dict(row)
        order_id = r.get("order_id")
        if not order_id or str(order_id).strip() == "":
            r["rejection_reason"] = "missing_required_key: order_id"
            rejected.append(r)
            continue

        # Quantity validation
        qty = r.get("quantity")
        if qty is None or str(qty).strip() == "":
            r["rejection_reason"] = "missing_required_key: quantity"
            rejected.append(r)
            continue
        try:
            val_qty = int(float(qty))
            if val_qty <= 0:
                r["rejection_reason"] = "invalid_quantity: quantity must be greater than zero"
                rejected.append(r)
                continue
            r["quantity"] = val_qty
        except (ValueError, TypeError):
            r["rejection_reason"] = "invalid_quantity: cannot parse as integer"
            rejected.append(r)
            continue

        # Discount default
        disc = r.get("discount")
        if disc is None or str(disc).strip() == "":
            r["discount"] = 0.0

        # Total & unit_price handling
        total = r.get("total")
        unit_price = r.get("unit_price")

        if total is not None and str(total).strip() == "":
            total = None
            r["total"] = None
        if unit_price is not None and str(unit_price).strip() == "":
            unit_price = None
            r["unit_price"] = None

        if total is None:
            if unit_price is not None:
                try:
                    r["total"] = round(float(unit_price) * r["quantity"] - float(r["discount"]), 4)
                except (ValueError, TypeError):
                    r["rejection_reason"] = "null_total: cannot calculate order total"
                    rejected.append(r)
                    continue
            else:
                r["rejection_reason"] = "null_total: cannot calculate order total"
                rejected.append(r)
                continue

        if unit_price is None and r.get("total") is not None and r["quantity"] > 0:
            try:
                r["unit_price"] = round((float(r["total"]) + float(r["discount"])) / r["quantity"], 4)
            except (ValueError, TypeError):
                pass

        valid.append(r)

    logger.info("Null handling orders: in=%d, valid=%d, rejected=%d", len(records), len(valid), len(rejected))
    return valid, rejected


def handle_nulls_shipping(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Handle missing values and enforce required fields for shipping/fulfillment:
    - Rejects rows missing order_id.
    - Imputes defaults: shipping_mode='Standard', delivery_status='Unknown'.
    """
    valid: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for row in records:
        r = dict(row)
        order_id = r.get("order_id")
        if not order_id or str(order_id).strip() == "":
            r["rejection_reason"] = "missing_required_key: order_id"
            rejected.append(r)
            continue

        if not r.get("shipping_mode"):
            r["shipping_mode"] = "Standard"

        if not r.get("delivery_status"):
            r["delivery_status"] = "Unknown"

        valid.append(r)

    logger.info("Null handling shipping: in=%d, valid=%d, rejected=%d", len(records), len(valid), len(rejected))
    return valid, rejected


def handle_nulls(
    records: List[Dict[str, Any]],
    template_name: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Dispatch null handling and schema rule enforcement based on canonical template.
    """
    if "ship" in template_name.lower():
        return handle_nulls_shipping(records)
    return handle_nulls_orders(records)
