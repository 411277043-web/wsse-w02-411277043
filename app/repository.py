# 資料存取（Repository）：只負責讀寫 Comparison 與 Item（LAB 05 第 2 節）。
# 不驗證價格或數量、不換算單位、不判斷 Best Choice，這些都屬於 Service。

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def create_comparison(db: Session, name: str | None) -> models.Comparison:
    obj = models.Comparison(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_comparison(db: Session, comparison_id: int) -> models.Comparison | None:
    return db.get(models.Comparison, comparison_id)


def delete_comparison(db: Session, comparison: models.Comparison) -> None:
    # relationship 設定 cascade，會一併刪除此比較的所有 Item
    db.delete(comparison)
    db.commit()


def list_items(db: Session, comparison_id: int) -> list[models.Item]:
    # 依 id 由小到大，也就是加入順序（LAB 05 Design Note 3）
    stmt = (
        select(models.Item)
        .where(models.Item.comparison_id == comparison_id)
        .order_by(models.Item.id)
    )
    return list(db.scalars(stmt))


def get_item(db: Session, comparison_id: int, item_id: int) -> models.Item | None:
    # 商品必須屬於指定的比較，否則視為不存在
    item = db.get(models.Item, item_id)
    if item is None or item.comparison_id != comparison_id:
        return None
    return item


def create_item(
    db: Session, comparison_id: int, name: str, price: Decimal, quantity: Decimal, unit: str
) -> models.Item:
    obj = models.Item(
        comparison_id=comparison_id, name=name, price=price, quantity=quantity, unit=unit
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_item(db: Session, item: models.Item, changes: dict) -> models.Item:
    for field, value in changes.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item: models.Item) -> None:
    db.delete(item)
    db.commit()
