from decimal import Decimal

from app.services.commission_service import calculate_commission


def test_calculate_commission():
    amount = Decimal("500.00")
    percent = Decimal("10.00")
    result = calculate_commission(amount, percent)
    assert result == Decimal("50.00")


def test_calculate_commission_rounding():
    amount = Decimal("333.33")
    percent = Decimal("7.5")
    result = calculate_commission(amount, percent)
    assert result == Decimal("25.00")
