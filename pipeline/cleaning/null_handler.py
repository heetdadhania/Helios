import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("helios.pipeline.cleaning.nulls")


def handle_nulls_orders(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Handle missing values and enforce required fields for retail orders:
    - Rejects rows missing order_id, customer_id, product_id, or order_date.
    - Rejects rows with missing, zero or negative quantity.
    - Rejects rows with missing, zero or negative unit_price.
    - Rejects rows with missing or negative total.
    - Rejects rows where total != quantity * unit_price - discount (tolerance ₹0.02).
    - Imputes default discount: 0.0 when missing.
    - Preserves row identifier, clear rejection reason, and original value for quality log.
    """
    valid: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for row in records:
        r = dict(row)
        
        # 1. Order ID required
        order_id = r.get("order_id")
        if order_id is None or str(order_id).strip() == "":
            r["rejection_reason"] = f"missing_required_key: order_id (original_value: {order_id})"
            rejected.append(r)
            continue

        # 2. Customer ID required
        cust_id = r.get("customer_id")
        if cust_id is None or str(cust_id).strip() == "":
            r["rejection_reason"] = f"missing_required_key: customer_id (original_value: {cust_id})"
            rejected.append(r)
            continue

        # 3. Product ID required
        prod_id = r.get("product_id")
        if prod_id is None or str(prod_id).strip() == "":
            r["rejection_reason"] = f"missing_required_key: product_id (original_value: {prod_id})"
            rejected.append(r)
            continue

        # 4. Order date required (unreadable dates rejected earlier by date_standardizer)
        od = r.get("order_date")
        if od is None or str(od).strip() == "":
            r["rejection_reason"] = f"missing_required_field: order_date (original_value: {od})"
            rejected.append(r)
            continue

        # 5. Quantity validation: missing, zero or negative
        qty = r.get("quantity")
        if qty is None or str(qty).strip() == "":
            r["rejection_reason"] = f"missing_required_key: quantity (original_value: {qty})"
            rejected.append(r)
            continue
        try:
            val_qty = int(float(qty))
            if val_qty <= 0:
                r["rejection_reason"] = f"invalid_quantity: quantity must be greater than zero (original_value: {qty})"
                rejected.append(r)
                continue
            r["quantity"] = val_qty
        except (ValueError, TypeError):
            r["rejection_reason"] = f"invalid_quantity: cannot parse as integer (original_value: {qty})"
            rejected.append(r)
            continue

        # 6. Unit price validation: missing, zero or negative
        unit_price = r.get("unit_price")
        if unit_price is None or str(unit_price).strip() == "":
            r["rejection_reason"] = f"missing_required_key: unit_price (original_value: {unit_price})"
            rejected.append(r)
            continue
        try:
            up_float = float(unit_price)
            if up_float <= 0:
                r["rejection_reason"] = f"invalid_unit_price: unit_price must be greater than zero (original_value: {unit_price})"
                rejected.append(r)
                continue
            r["unit_price"] = up_float
        except (ValueError, TypeError):
            r["rejection_reason"] = f"invalid_unit_price: cannot parse as decimal (original_value: {unit_price})"
            rejected.append(r)
            continue

        # 7. Total validation: missing or negative
        total = r.get("total")
        if total is None or str(total).strip() == "":
            r["rejection_reason"] = f"missing_required_key: total (original_value: {total})"
            rejected.append(r)
            continue
        try:
            tot_float = float(total)
            if tot_float < 0:
                r["rejection_reason"] = f"negative_total: total must not be negative (original_value: {total})"
                rejected.append(r)
                continue
            r["total"] = tot_float
        except (ValueError, TypeError):
            r["rejection_reason"] = f"negative_total: cannot parse as decimal (original_value: {total})"
            rejected.append(r)
            continue

        # 8. Discount default (impute 0.0 if not provided)
        disc = r.get("discount")
        if disc is None or str(disc).strip() == "":
            r["discount"] = 0.0
        else:
            try:
                r["discount"] = float(disc)
            except (ValueError, TypeError):
                r["discount"] = 0.0

        # 9. Arithmetic check: total == quantity * unit_price - discount (tolerance ₹0.02)
        try:
            final_total = float(r["total"])
            final_up = float(r["unit_price"])
            final_qty = int(r["quantity"])
            final_disc = float(r["discount"])
            expected = round(final_up * final_qty - final_disc, 4)
            diff = round(abs(final_total - expected), 4)
            if diff > 0.02:
                r["rejection_reason"] = (
                    f"arithmetic_mismatch: total does not equal quantity * unit_price - discount "
                    f"(total={final_total}, expected={expected}, diff={diff}) (original_value: {final_total})"
                )
                rejected.append(r)
                continue
        except (ValueError, TypeError) as exc:
            r["rejection_reason"] = f"arithmetic_mismatch: calculation error ({exc}) (original_value: {r.get('total')})"
            rejected.append(r)
            continue

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
            r["rejection_reason"] = f"missing_required_key: order_id (original_value: {order_id})"
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
