from decimal import Decimal
import pytest
from pipeline.cleaning.currency_cleaner import clean_currency, clean_currency_fields


class TestCurrencyCleanerINR:
    """Test suite covering Indian Rupee (INR) formats and edge cases as required by Requirement D."""

    # 1. Format: "₹1,25,000.00"
    def test_clean_currency_rupee_with_lakh_grouping_and_decimals(self):
        result = clean_currency("₹1,25,000.00")
        assert result == Decimal("125000.00")
        assert isinstance(result, Decimal)

    # 2. Format: "₹ 1,250.50"
    def test_clean_currency_rupee_spaced_with_decimals(self):
        result = clean_currency("₹ 1,250.50")
        assert result == Decimal("1250.50")
        assert isinstance(result, Decimal)

    # 3. Format: "Rs. 1,250"
    def test_clean_currency_rs_dot_spaced(self):
        result = clean_currency("Rs. 1,250")
        assert result == Decimal("1250")
        assert isinstance(result, Decimal)

    # 4. Format: "Rs 1250"
    def test_clean_currency_rs_no_dot(self):
        result = clean_currency("Rs 1250")
        assert result == Decimal("1250")
        assert isinstance(result, Decimal)

    # 5. Format: "INR 899"
    def test_clean_currency_inr_prefix(self):
        result = clean_currency("INR 899")
        assert result == Decimal("899")
        assert isinstance(result, Decimal)

    # 6. Format: "1,25,000"
    def test_clean_currency_lakh_grouping_without_symbol(self):
        result = clean_currency("1,25,000")
        assert result == Decimal("125000")
        assert isinstance(result, Decimal)

    # 7. Format: "1250/-"
    def test_clean_currency_trailing_slash_dash(self):
        result = clean_currency("1250/-")
        assert result == Decimal("1250")
        assert isinstance(result, Decimal)

    # 8. Format: " 899 "
    def test_clean_currency_plain_number_with_padding(self):
        result = clean_currency(" 899 ")
        assert result == Decimal("899")
        assert isinstance(result, Decimal)

    # 9. Format: "Rs 1250/-"
    def test_clean_currency_rs_with_trailing_slash_dash(self):
        result = clean_currency("Rs 1250/-")
        assert result == Decimal("1250")
        assert isinstance(result, Decimal)

    # 10. Format: Accounting negative with Rupee "(₹ 1,250.50)"
    def test_clean_currency_accounting_negative(self):
        result = clean_currency("(₹ 1,250.50)")
        assert result == Decimal("-1250.50")
        assert isinstance(result, Decimal)

    # 11. Format: Numeric input types (int and Decimal)
    def test_clean_currency_numeric_types(self):
        assert clean_currency(1250) == Decimal("1250")
        assert clean_currency(Decimal("45000.75")) == Decimal("45000.75")

    # 12. Bad value: non-numeric string "abc"
    def test_clean_currency_bad_string_letters(self):
        assert clean_currency("abc") is None

    # 13. Bad value: empty string and whitespace
    def test_clean_currency_bad_empty(self):
        assert clean_currency("") is None
        assert clean_currency("   ") is None
        assert clean_currency(None) is None

    # 14. Bad value: multiple decimal points "12.34.56"
    def test_clean_currency_bad_multiple_decimals(self):
        assert clean_currency("12.34.56") is None

    # 15. Bad value: placeholder tokens "N/A", "nan", "null"
    def test_clean_currency_bad_null_placeholders(self):
        assert clean_currency("N/A") is None
        assert clean_currency("null") is None
        assert clean_currency("nan") is None

    # 16. Bad value: currency symbols without digits
    def test_clean_currency_bad_symbols_only(self):
        assert clean_currency("₹") is None
        assert clean_currency("Rs.") is None
        assert clean_currency("/-") is None
        assert clean_currency("$$$") is None

    # 17. Record fields cleaning test
    def test_clean_currency_fields(self):
        record = {
            "order_id": "ORD-101",
            "total": "₹1,25,000.00",
            "discount": "1250/-",
            "unit_price": "invalid_amount",
        }
        updated, errors = clean_currency_fields(record, ["total", "discount", "unit_price"])
        assert updated["total"] == Decimal("125000.00")
        assert updated["discount"] == Decimal("1250")
        assert errors == ["unit_price"]
