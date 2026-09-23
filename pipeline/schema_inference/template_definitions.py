from typing import Any, Dict, List

TEMPLATE_ORDERS: Dict[str, Any] = {
    "template_name": "template_orders",
    "display_name": "Retail & E-Commerce Orders",
    "target_table": "raw_orders",
    "target_silver_table": "silver.orders",
    "primary_key": "order_id",
    "required_fields": ["order_id"],
    "fields": {
        "order_id": {
            "type": "string",
            "description": "Unique identifier for the customer order",
            "aliases": [
                "order_id",
                "order_number",
                "order_no",
                "ord_id",
                "ord_no",
                "orderid",
                "id",
                "order_reference",
                "order_num",
            ],
        },
        "customer_id": {
            "type": "string",
            "description": "Unique identifier for the purchaser",
            "aliases": [
                "customer_id",
                "cust_id",
                "customer_no",
                "client_id",
                "buyer_id",
                "user_id",
                "customerid",
            ],
        },
        "customer_email": {
            "type": "string",
            "description": "Contact email address of customer",
            "aliases": [
                "customer_email",
                "email",
                "email_address",
                "buyer_email",
                "cust_email",
                "client_email",
                "user_email",
            ],
        },
        "order_date": {
            "type": "timestamp",
            "description": "Date and timestamp when the order was placed",
            "aliases": [
                "order_date",
                "created_at",
                "ordered_at",
                "order_timestamp",
                "purchase_date",
                "date",
                "timestamp",
                "order_time",
            ],
        },
        "total_amount": {
            "type": "decimal",
            "description": "Final monetary amount paid for order",
            "aliases": [
                "total_amount",
                "total",
                "amount",
                "order_total",
                "grand_total",
                "price",
                "net_amount",
                "charge_amount",
            ],
        },
        "currency": {
            "type": "string",
            "description": "ISO currency code (USD, EUR, GBP, CAD)",
            "aliases": [
                "currency",
                "currency_code",
                "curr",
                "curr_code",
                "iso_currency",
            ],
        },
        "status": {
            "type": "string",
            "description": "Current lifecycle status of the order",
            "aliases": [
                "status",
                "order_status",
                "payment_status",
                "state",
                "fulfillment_status",
            ],
        },
        "payment_method": {
            "type": "string",
            "description": "Tender type or payment gateway",
            "aliases": [
                "payment_method",
                "payment_type",
                "gateway",
                "payment_gateway",
                "pay_method",
            ],
        },
        "line_items_count": {
            "type": "integer",
            "description": "Total quantity of items in the order",
            "aliases": [
                "line_items_count",
                "item_count",
                "quantity",
                "total_items",
                "items_count",
                "num_items",
            ],
        },
    },
}

TEMPLATE_SHIPPING: Dict[str, Any] = {
    "template_name": "template_shipping",
    "display_name": "Shipment & Delivery Fulfillment",
    "target_table": "raw_shipping",
    "target_silver_table": "silver.shipping",
    "primary_key": "shipment_id",
    "required_fields": ["shipment_id", "tracking_number"],
    "fields": {
        "shipment_id": {
            "type": "string",
            "description": "Unique identifier for the shipment record",
            "aliases": [
                "shipment_id",
                "ship_id",
                "delivery_id",
                "fulfillment_id",
                "shipping_id",
                "dispatch_id",
                "id",
            ],
        },
        "tracking_number": {
            "type": "string",
            "description": "Carrier tracking or AWB barcode number",
            "aliases": [
                "tracking_number",
                "tracking_no",
                "tracking_code",
                "tracking",
                "track_no",
                "awb",
                "waybill",
                "consignment_number",
            ],
        },
        "order_id": {
            "type": "string",
            "description": "Foreign key connecting shipment to retail order",
            "aliases": [
                "order_id",
                "order_number",
                "order_no",
                "ord_id",
                "order_ref",
            ],
        },
        "carrier": {
            "type": "string",
            "description": "Fulfillment logistics carrier (FedEx, UPS, USPS, DHL)",
            "aliases": [
                "carrier",
                "carrier_name",
                "courier",
                "shipping_carrier",
                "shipper",
                "logistics_provider",
            ],
        },
        "shipping_status": {
            "type": "string",
            "description": "Transit status (in_transit, delivered, out_for_delivery, exception)",
            "aliases": [
                "shipping_status",
                "delivery_status",
                "shipment_status",
                "status",
                "transit_status",
            ],
        },
        "shipped_at": {
            "type": "timestamp",
            "description": "Timestamp when package was picked up or dispatched",
            "aliases": [
                "shipped_at",
                "ship_date",
                "dispatched_at",
                "dispatch_date",
                "shipped_date",
                "departure_time",
            ],
        },
        "delivered_at": {
            "type": "timestamp",
            "description": "Timestamp when package arrived at destination",
            "aliases": [
                "delivered_at",
                "delivery_date",
                "received_at",
                "delivered_date",
                "actual_delivery_date",
            ],
        },
        "shipping_cost": {
            "type": "decimal",
            "description": "Freight or postal fees billed for transport",
            "aliases": [
                "shipping_cost",
                "freight_charge",
                "delivery_fee",
                "shipping_fee",
                "shipping_rate",
                "freight_cost",
            ],
        },
        "destination_country": {
            "type": "string",
            "description": "Destination country code or name",
            "aliases": [
                "destination_country",
                "country",
                "ship_country",
                "dest_country",
                "recipient_country",
            ],
        },
        "destination_postal_code": {
            "type": "string",
            "description": "Destination postal or ZIP code",
            "aliases": [
                "destination_postal_code",
                "postal_code",
                "zip_code",
                "zipcode",
                "postcode",
                "zip",
            ],
        },
    },
}

KNOWN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "template_orders": TEMPLATE_ORDERS,
    "template_shipping": TEMPLATE_SHIPPING,
}


def get_template(name: str) -> Dict[str, Any]:
    """Retrieve template definition by name."""
    cleaned = name.strip().lower()
    if cleaned in KNOWN_TEMPLATES:
        return KNOWN_TEMPLATES[cleaned]
    if "ship" in cleaned:
        return TEMPLATE_SHIPPING
    return TEMPLATE_ORDERS
