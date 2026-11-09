# 業務邏輯（Service）：LAB 05 第 2 節的 BR-04、BR-06～BR-10，以及確認資源是否存在。
# Service 只拋出業務錯誤（app/exceptions.py），不處理 HTTP Status Code 或 Header。

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from . import models, repository
from .exceptions import InsufficientItemsError, MeasurementTypeMismatchError, NotFoundError
from .schemas import (
    ComparisonCreate,
    ComparisonRead,
    ComparisonResult,
    ItemCreate,
    ItemRead,
    ItemResult,
    ItemUpdate,
    MeasurementType,
    Unit,
)


@dataclass(frozen=True)
class UnitInfo:
    measurement_type: MeasurementType
    base_unit: str
    factor: Decimal  # 換算成基準單位的倍率


class UnitConverter:
    """單位對照表：單位 → Measurement Type、基準單位與換算倍率。

    BR-06（Measurement Type 一致）與 BR-07（單位換算）共用這一份對照表，
    避免寫兩次而不一致（LAB 05 第 2 節）。
    """

    TABLE = {
        Unit.mL: UnitInfo(MeasurementType.VOLUME, "mL", Decimal("1")),
        Unit.L: UnitInfo(MeasurementType.VOLUME, "mL", Decimal("1000")),
        Unit.g: UnitInfo(MeasurementType.WEIGHT, "g", Decimal("1")),
        Unit.kg: UnitInfo(MeasurementType.WEIGHT, "g", Decimal("1000")),
        Unit.piece: UnitInfo(MeasurementType.COUNT, "piece", Decimal("1")),
    }

    @classmethod
    def info(cls, unit: str) -> UnitInfo:
        return cls.TABLE[Unit(unit)]

    @classmethod
    def measurement_type(cls, unit: str) -> MeasurementType:
        return cls.info(unit).measurement_type

    @classmethod
    def normalize(cls, quantity: Decimal, unit: str) -> Decimal:
        """BR-07：把數量換算成基準單位，例如 1 L → 1000 mL、1.5 kg → 1500 g。"""
        return quantity * cls.info(unit).factor


def calculate_result(comparison_id: int, items: Sequence[models.Item]) -> ComparisonResult:
    """依目前的商品即時計算比價結果；不需要資料庫，可以單獨做單元測試。

    items 必須依加入順序排列（id 由小到大），BR-10 並列時才會依加入順序列出。
    """
    if len(items) < 2:  # BR-04
        raise InsufficientItemsError("at least 2 items are required to calculate the result (BR-04)")

    results = []
    for item in items:
        normalized = UnitConverter.normalize(item.quantity, item.unit)  # BR-07
        results.append(
            ItemResult(
                item_id=item.id,
                name=item.name,
                price=item.price,
                quantity=item.quantity,
                unit=item.unit,
                normalized_quantity=normalized,
                unit_price=item.price / normalized,  # BR-08
            )
        )

    # BR-09、BR-10：以 Decimal 精確值比較；所有等於最低值的商品都是 Best Choice，順序沿用加入順序
    lowest = min(result.unit_price for result in results)
    info = UnitConverter.info(items[0].unit)
    return ComparisonResult(
        comparison_id=comparison_id,
        measurement_type=info.measurement_type,
        base_unit=info.base_unit,
        items=results,
        best_choice_item_ids=[r.item_id for r in results if r.unit_price == lowest],
    )


# ---------- 內部輔助 ----------


def _as_utc(value: datetime) -> datetime:
    # SQLite 讀回的時間不帶時區；系統一律以 UTC 寫入，因此補上 UTC
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _to_item_read(item: models.Item) -> ItemRead:
    return ItemRead(
        id=item.id,
        name=item.name,
        price=item.price,
        quantity=item.quantity,
        unit=item.unit,
        measurement_type=UnitConverter.measurement_type(item.unit),
    )


def _to_comparison_read(comparison: models.Comparison, items: list[models.Item]) -> ComparisonRead:
    return ComparisonRead(
        id=comparison.id,
        name=comparison.name,
        # LAB 05 Design Note 2：不儲存，由第一個商品推得；沒有商品時為 null
        measurement_type=UnitConverter.measurement_type(items[0].unit) if items else None,
        created_at=_as_utc(comparison.created_at),
        items=[_to_item_read(item) for item in items],
    )


def _get_comparison_or_404(db: Session, comparison_id: int) -> models.Comparison:
    comparison = repository.get_comparison(db, comparison_id)
    if comparison is None:
        raise NotFoundError(f"comparison {comparison_id} not found")
    return comparison


def _get_item_or_404(db: Session, comparison_id: int, item_id: int) -> models.Item:
    _get_comparison_or_404(db, comparison_id)
    item = repository.get_item(db, comparison_id, item_id)
    if item is None:
        raise NotFoundError(f"item {item_id} not found in comparison {comparison_id}")
    return item


def _ensure_same_measurement_type(unit: str, others: list[models.Item]) -> None:
    """BR-06：others 是同一比較中的其他商品；沒有其他商品時不限制。"""
    if not others:
        return
    expected = UnitConverter.measurement_type(others[0].unit)
    actual = UnitConverter.measurement_type(unit)
    if actual != expected:
        raise MeasurementTypeMismatchError(
            f"unit {Unit(unit).value} ({actual.value}) does not match "
            f"the comparison's measurement type {expected.value} (BR-06)"
        )


# ---------- 對應 7 條 API 的 Service 方法 ----------


def create_comparison(db: Session, data: ComparisonCreate) -> ComparisonRead:
    comparison = repository.create_comparison(db, data.name)
    return _to_comparison_read(comparison, [])


def get_comparison(db: Session, comparison_id: int) -> ComparisonRead:
    comparison = _get_comparison_or_404(db, comparison_id)
    return _to_comparison_read(comparison, repository.list_items(db, comparison_id))


def delete_comparison(db: Session, comparison_id: int) -> None:
    repository.delete_comparison(db, _get_comparison_or_404(db, comparison_id))


def add_item(db: Session, comparison_id: int, data: ItemCreate) -> ItemRead:
    _get_comparison_or_404(db, comparison_id)
    _ensure_same_measurement_type(data.unit, repository.list_items(db, comparison_id))
    item = repository.create_item(
        db, comparison_id, data.name, data.price, data.quantity, data.unit.value
    )
    return _to_item_read(item)


def update_item(db: Session, comparison_id: int, item_id: int, data: ItemUpdate) -> ItemRead:
    item = _get_item_or_404(db, comparison_id, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "unit" in changes:
        changes["unit"] = changes["unit"].value
        # 修改單位時，要和「自己以外」的商品比較 Measurement Type
        others = [other for other in repository.list_items(db, comparison_id) if other.id != item.id]
        _ensure_same_measurement_type(changes["unit"], others)
    return _to_item_read(repository.update_item(db, item, changes))


def delete_item(db: Session, comparison_id: int, item_id: int) -> None:
    repository.delete_item(db, _get_item_or_404(db, comparison_id, item_id))


def get_result(db: Session, comparison_id: int) -> ComparisonResult:
    _get_comparison_or_404(db, comparison_id)
    return calculate_result(comparison_id, repository.list_items(db, comparison_id))
