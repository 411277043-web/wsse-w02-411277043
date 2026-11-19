# 資料模型（Database Models）：對應 LAB 05 第 4 節的 Comparison 與 Item。
# measurement_type、normalized_quantity、unit_price 都是計算結果，依 LAB 05 Design Notes 不存進資料庫。

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base


class ExactDecimal(TypeDecorator):
    """把 Decimal 以文字存進 SQLite，讀回時再轉回 Decimal。

    SQLite 沒有真正的 decimal 型別，SQLAlchemy 的 Numeric 會經過浮點數轉換。
    LAB 05 Design Note 4 要求金額與數量不使用浮點數，因此改存文字，保留輸入的精確值。
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):
        return None if value is None else Decimal(value)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    # 刪除 Comparison 時一併刪除其 Item（LAB 05 第 5 節 Cascade Delete，對應 FR-11）
    items: Mapped[list["Item"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan", order_by="Item.id"
    )


class Item(Base):
    __tablename__ = "items"
    # LAB 05 Design Note 6：unit 採「字串 + 檢查條件」，只接受 BR-05 的五種單位
    __table_args__ = (
        CheckConstraint("unit IN ('mL', 'L', 'g', 'kg', 'piece')", name="ck_items_unit"),
    )

    # 遞增的 id 同時代表加入順序（LAB 05 Design Note 3，BR-10 並列時依此排序）
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    comparison_id: Mapped[int] = mapped_column(ForeignKey("comparisons.id"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(ExactDecimal)
    quantity: Mapped[Decimal] = mapped_column(ExactDecimal)
    unit: Mapped[str] = mapped_column(String(5))
    comparison: Mapped[Comparison] = relationship(back_populates="items")
