"""UnitPriceCompare：依 openapi.yaml Contract 實作 7 條 API，資料存在 SQLite。

本檔是 LAB 05 的 Router 層：讀取參數、呼叫 Service、組成 Response（201 + Location、200、204），
並把所有錯誤統一轉成 Contract 的 ErrorResponse。
LAB 06（W08）完成 7 條 API；LAB 07（W09）為 5 條寫入 API 加上 Security(require_editor)，2 條 GET 維持公開。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Path, Request, Response, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import service
from .database import Base, engine, get_db
from .exceptions import DomainError, NotFoundError
from .schemas import (
    ComparisonCreate,
    ComparisonRead,
    ComparisonResult,
    ErrorResponse,
    ItemCreate,
    ItemRead,
    ItemUpdate,
)
from .security import CurrentUser, require_editor

API_PREFIX = "/api/v1"  # LAB 04 servers.url

# 第一次啟動時建立資料表；之後重新啟動 API，資料仍保留在 unitprice.db
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="UnitPriceCompare API",
    version="1.0.0",
    description=(
        "LAB 07 - 單位價格比較服務（Student ID: 411277043）。"
        "新增、修改、刪除需要 editor 的 X-API-Key；查詢與比價結果不需要。"
    ),
    openapi_tags=[
        {"name": "comparisons", "description": "比較（Comparison）的建立、查詢與刪除"},
        {"name": "items", "description": "比較中的商品（Item）"},
        {"name": "results", "description": "比價結果（Derived Resource，唯讀）"},
    ],
)
router = APIRouter(prefix=API_PREFIX)

ComparisonId = Annotated[int, Path(ge=1, description="比較的 ID")]
ItemId = Annotated[int, Path(ge=1, description="商品的 ID")]

# LAB 04 components.responses：所有 4xx 都使用 ErrorResponse
BAD_REQUEST = {400: {"model": ErrorResponse, "description": "Request 不符合 Contract 或 Business Rules"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "指定的 Comparison 或 Item 不存在"}}
# LAB 07：寫入 API 的身分與權限錯誤
AUTH_ERRORS = {
    401: {"model": ErrorResponse, "description": "缺少 X-API-Key"},
    403: {"model": ErrorResponse, "description": "金鑰無效，或使用者不是 editor"},
    503: {"model": ErrorResponse, "description": "伺服器的使用者設定缺漏或格式錯誤"},
}


# ---------- 7 條 API（Method、Path、Status Code 沿用 LAB 03／LAB 04） ----------


@router.post(
    "/comparisons",
    status_code=status.HTTP_201_CREATED,
    response_model=ComparisonRead,
    responses={**BAD_REQUEST, **AUTH_ERRORS},
    tags=["comparisons"],
    operation_id="createComparison",
    summary="Create a comparison",
)
def create_comparison(
    response: Response,
    data: ComparisonCreate | None = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Security(require_editor),
):
    """建立一次尚未包含商品的比較；可以不傳 Body。（FR-01；限 editor，SEC-02）"""
    created = service.create_comparison(db, data or ComparisonCreate())
    response.headers["Location"] = f"{API_PREFIX}/comparisons/{created.id}"
    return created


@router.get(
    "/comparisons/{comparison_id}",
    response_model=ComparisonRead,
    responses=NOT_FOUND,
    tags=["comparisons"],
    operation_id="getComparison",
    summary="Get a comparison with its items",
)
def get_comparison(comparison_id: ComparisonId, db: Session = Depends(get_db)):
    """取得指定比較及其目前包含的商品。（FR-05）"""
    return service.get_comparison(db, comparison_id)


@router.delete(
    "/comparisons/{comparison_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**NOT_FOUND, **AUTH_ERRORS},
    tags=["comparisons"],
    operation_id="deleteComparison",
    summary="Delete a comparison",
)
def delete_comparison(
    comparison_id: ComparisonId,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Security(require_editor),
):
    """刪除指定比較，連同其所有商品。（FR-11；限 editor，SEC-03）"""
    service.delete_comparison(db, comparison_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/comparisons/{comparison_id}/items",
    status_code=status.HTTP_201_CREATED,
    response_model=ItemRead,
    responses={**BAD_REQUEST, **NOT_FOUND, **AUTH_ERRORS},
    tags=["items"],
    operation_id="addItem",
    summary="Add an item to a comparison",
)
def add_item(
    comparison_id: ComparisonId,
    data: ItemCreate,
    response: Response,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Security(require_editor),
):
    """在比較中新增一個商品。（FR-02、FR-06；限 editor，SEC-02）

    BR-01～BR-03、BR-05 由 Schema 檢查，BR-06 由 Service 檢查。
    """
    item = service.add_item(db, comparison_id, data)
    response.headers["Location"] = f"{API_PREFIX}/comparisons/{comparison_id}/items/{item.id}"
    return item


@router.patch(
    "/comparisons/{comparison_id}/items/{item_id}",
    response_model=ItemRead,
    responses={**BAD_REQUEST, **NOT_FOUND, **AUTH_ERRORS},
    tags=["items"],
    operation_id="updateItem",
    summary="Update part of an item",
)
def update_item(
    comparison_id: ComparisonId,
    item_id: ItemId,
    data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Security(require_editor),
):
    """修改商品的部分欄位，至少需提供一個欄位；修改後同樣須符合 BR-01～BR-06。（FR-03、FR-06；限 editor，SEC-03）"""
    return service.update_item(db, comparison_id, item_id, data)


@router.delete(
    "/comparisons/{comparison_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**NOT_FOUND, **AUTH_ERRORS},
    tags=["items"],
    operation_id="deleteItem",
    summary="Remove an item from a comparison",
)
def delete_item(
    comparison_id: ComparisonId,
    item_id: ItemId,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Security(require_editor),
):
    """從比較中移除指定商品。（FR-04；限 editor，SEC-03）"""
    service.delete_item(db, comparison_id, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/comparisons/{comparison_id}/result",
    response_model=ComparisonResult,
    responses={**BAD_REQUEST, **NOT_FOUND},
    tags=["results"],
    operation_id="getComparisonResult",
    summary="Get the comparison result",
)
def get_result(comparison_id: ComparisonId, db: Session = Depends(get_db)):
    """依目前的商品即時計算比價結果；商品少於 2 個時回傳 400 INSUFFICIENT_ITEMS。（FR-07～FR-10）"""
    return service.get_result(db, comparison_id)


app.include_router(router)


# ---------- 錯誤處理：全部轉成 LAB 04 的 ErrorResponse ----------

# 違反單一欄位規則時，在訊息中標出對應的 Business Rule（NFR-03）
ITEM_FIELD_RULES = {"price": "BR-01", "quantity": "BR-02", "name": "BR-03", "unit": "BR-05"}


def error_response(status_code: int, code: str, message: str, headers=None) -> JSONResponse:
    body = ErrorResponse(code=code, message=message).model_dump(exclude_none=True)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def describe_validation_error(error: dict, is_item_request: bool) -> str:
    parts = [str(part) for part in error["loc"] if part not in ("body", "path", "query")]
    field = ".".join(parts) or "body"
    message = f"{field}: {error['msg']}"
    rule = ITEM_FIELD_RULES.get(parts[-1]) if parts and is_item_request else None
    if rule and error["type"] not in ("missing", "extra_forbidden"):
        message += f" ({rule})"
    return message


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    """欄位缺漏、型別錯誤、違反 BR-01～BR-03、BR-05：依 Contract 回 400 INVALID_REQUEST（不是 FastAPI 預設的 422）。"""
    is_item_request = "/items" in request.url.path
    message = "; ".join(describe_validation_error(e, is_item_request) for e in exc.errors())
    return error_response(status.HTTP_400_BAD_REQUEST, "INVALID_REQUEST", message)


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    """Service 拋出的業務錯誤：NOT_FOUND → 404，其餘（BR-04、BR-06）→ 400。"""
    status_code = status.HTTP_404_NOT_FOUND if isinstance(exc, NotFoundError) else status.HTTP_400_BAD_REQUEST
    return error_response(status_code, exc.code, exc.message)


HTTP_ERROR_CODES = {
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(request: Request, exc: StarletteHTTPException):
    """app/security.py 的 401／403／503、路徑不存在（404）、Method 不支援（405），也使用相同的錯誤格式。"""
    code = HTTP_ERROR_CODES.get(exc.status_code, "INVALID_REQUEST")
    return error_response(exc.status_code, code, str(exc.detail), headers=getattr(exc, "headers", None))


# ---------- /docs 與 /openapi.json 對齊 LAB 04 Contract ----------


def custom_openapi():
    """移除 FastAPI 預設的 422 回應：本服務依 LAB 04 Contract 以 400 INVALID_REQUEST 回報驗證錯誤。"""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            operation.get("responses", {}).pop("422", None)
    for name in ("HTTPValidationError", "ValidationError"):
        schema.get("components", {}).get("schemas", {}).pop(name, None)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
