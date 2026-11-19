"""Service 單元測試：不啟動 HTTP、不連資料庫，直接測比價規則（LAB 05 第 1 節選擇分層的理由）。"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.exceptions import InsufficientItemsError
from app.schemas import MeasurementType
from app.service import UnitConverter, calculate_result


def item(item_id, price, quantity, unit):
    return SimpleNamespace(
        id=item_id, name=f"ITEM_{item_id}", price=Decimal(price), quantity=Decimal(quantity), unit=unit
    )


@pytest.mark.parametrize(
    ("quantity", "unit", "expected", "measurement_type"),
    [
        ("500", "mL", "500", MeasurementType.VOLUME),
        ("1", "L", "1000", MeasurementType.VOLUME),
        ("1.5", "kg", "1500", MeasurementType.WEIGHT),
        ("300", "g", "300", MeasurementType.WEIGHT),
        ("6", "piece", "6", MeasurementType.COUNT),
    ],
)
def test_unit_converter(quantity, unit, expected, measurement_type):
    assert UnitConverter.normalize(Decimal(quantity), unit) == Decimal(expected)  # BR-07
    assert UnitConverter.measurement_type(unit) == measurement_type  # BR-06


def test_unit_price_and_best_choice():
    result = calculate_result(1, [item(3, "45", "500", "mL"), item(4, "80", "1", "L")])
    assert [r.unit_price for r in result.items] == [Decimal("0.09"), Decimal("0.08")]  # BR-08
    assert result.best_choice_item_ids == [4]  # BR-09


def test_tie_keeps_added_order():
    # 0.1、0.12、0.1 元/mL：7 與 9 並列最低
    items = [item(7, "60", "0.6", "L"), item(8, "12", "100", "mL"), item(9, "30", "300", "mL")]
    assert calculate_result(1, items).best_choice_item_ids == [7, 9]  # BR-10


def test_requires_two_items():
    with pytest.raises(InsufficientItemsError):  # BR-04
        calculate_result(1, [item(1, "45", "500", "mL")])
