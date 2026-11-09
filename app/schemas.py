# API 結構（API Schemas）：依 LAB 04 OpenAPI Contract 定義 Request／Response 與欄位驗證。
# 只看單一欄位就能判斷的規則（BR-01～BR-03、BR-05）在這裡檢查；
# 需要查其他資料的 BR-04、BR-06 由 Service 檢查（LAB 05 第 2 節「驗證責任的分工」）。

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
    field_validator,
    model_validator,
)


class Unit(str, Enum):
    """支援的單位（BR-05）。"""

    mL = "mL"
    L = "L"
    g = "g"
    kg = "kg"
    piece = "piece"


class MeasurementType(str, Enum):
    """單位所屬的 Measurement Type（BR-06）。"""

    VOLUME = "VOLUME"
    WEIGHT = "WEIGHT"
    COUNT = "COUNT"


def _to_json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


# 內部一律用 Decimal 計算（LAB 05 Design Note 4）；輸出 JSON 時轉成 number，
# 因為 Pydantic 預設會把 Decimal 輸出成字串，不符合 Contract 的 type: number。
Number = Annotated[
    Decimal,
    PlainSerializer(_to_json_number, return_type=Any, when_used="json"),
    WithJsonSchema({"type": "number"}),
]


def _require_not_blank(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise ValueError("must not be blank")
    return value


# ---------- Request ----------


class ComparisonCreate(BaseModel):
    """建立比較時 Client 可傳入的資料；可以不傳 Body。"""

    model_config = ConfigDict(extra="forbid")  # additionalProperties: false

    name: str | None = Field(default=None, min_length=1, max_length=50)


class ItemCreate(BaseModel):
    """新增商品時 Client 傳入的資料。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=50)  # BR-03
    price: Decimal = Field(gt=0)  # BR-01
    quantity: Decimal = Field(gt=0)  # BR-02
    unit: Unit  # BR-05

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        return _require_not_blank(value)


class ItemUpdate(BaseModel):
    """修改商品時的部分欄位，至少提供一個（minProperties: 1）。"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=50)
    price: Decimal | None = Field(default=None, gt=0)
    quantity: Decimal | None = Field(default=None, gt=0)
    unit: Unit | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str | None) -> str | None:
        return _require_not_blank(value)

    @model_validator(mode="after")
    def check_fields_provided(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        # Contract 中各欄位都不允許 null；有傳的欄位就必須有值
        nulls = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"{', '.join(nulls)} must not be null")
        return self


# ---------- Response ----------


class ItemRead(BaseModel):
    """Server 回傳的商品；id 與 measurement_type 由 Server 產生。"""

    id: int
    name: str
    price: Number
    quantity: Number
    unit: Unit
    measurement_type: MeasurementType


class ComparisonRead(BaseModel):
    """Server 回傳的比較，包含目前的商品（依加入順序）。"""

    id: int
    name: str | None
    measurement_type: MeasurementType | None  # 依第一個商品決定；沒有商品時為 null
    created_at: datetime
    items: list[ItemRead]


class ItemResult(BaseModel):
    """比價結果中的單一商品，含換算後數量與單位價格。"""

    item_id: int
    name: str
    price: Number
    quantity: Number
    unit: Unit
    normalized_quantity: Number  # BR-07
    unit_price: Number  # BR-08


class ComparisonResult(BaseModel):
    """比價結果（Derived Resource），每次依目前的商品即時計算。"""

    comparison_id: int
    measurement_type: MeasurementType
    base_unit: Literal["mL", "g", "piece"]
    items: list[ItemResult]
    best_choice_item_ids: list[int]  # BR-09、BR-10


class ErrorResponse(BaseModel):
    """統一錯誤格式；所有 4xx 回應皆使用此格式。"""

    code: Literal["INVALID_REQUEST", "MEASUREMENT_TYPE_MISMATCH", "INSUFFICIENT_ITEMS", "NOT_FOUND"]
    message: str
    traceId: str | None = None  # Contract 中為選填，本版尚未使用，輸出時省略
