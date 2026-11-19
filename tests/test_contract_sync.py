"""規格一致性檢查：openapi.yaml Contract 與實際 API（/openapi.json）的路徑、方法、狀態碼、欄位與安全機制必須一致。

LAB 07 起以根目錄的 openapi.yaml 為目前的 Contract；LAB04_411277043_openapi.yaml 保留 W06 繳交時的版本。
"""

from pathlib import Path

import yaml

from app.main import API_PREFIX

CONTRACT_FILE = Path(__file__).resolve().parents[1] / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
# Contract 的 Schema 名稱 → 程式中的 Pydantic Model 名稱（只有 Response Model 的命名不同）
SCHEMA_NAMES = {"Item": "ItemRead", "Comparison": "ComparisonRead"}


def load_contract() -> dict:
    return yaml.safe_load(CONTRACT_FILE.read_text(encoding="utf-8"))


def contract_operations(contract: dict) -> set[tuple[str, str]]:
    return {
        (API_PREFIX + path, method)
        for path, path_item in contract["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    }


def test_paths_and_methods_match_contract(client):
    live = client.get("/openapi.json").json()
    live_operations = {
        (path, method)
        for path, path_item in live["paths"].items()
        for method in path_item
        if method in HTTP_METHODS
    }
    assert live_operations == contract_operations(load_contract())


def test_operation_ids_and_status_codes_match_contract(client):
    contract = load_contract()
    live = client.get("/openapi.json").json()
    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            live_operation = live["paths"][API_PREFIX + path][method]
            assert live_operation["operationId"] == operation["operationId"]
            # 包含：驗證錯誤是 400，不是 FastAPI 預設的 422
            assert set(live_operation["responses"]) == set(operation["responses"]), (method, path)


def test_schema_fields_match_contract(client):
    contract_schemas = load_contract()["components"]["schemas"]
    live_schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name, schema in contract_schemas.items():
        if "properties" not in schema:
            continue  # Unit、MeasurementType 是列舉
        live_name = SCHEMA_NAMES.get(name, name)
        assert set(live_schemas[live_name]["properties"]) == set(schema["properties"]), name


def test_security_matches_contract(client):
    """LAB 07：寫入 API 宣告 ApiKeyAuth，GET 不宣告；Security Scheme 與 Contract 相同。"""
    contract = load_contract()
    live = client.get("/openapi.json").json()

    contract_scheme = contract["components"]["securitySchemes"]["ApiKeyAuth"]
    live_scheme = live["components"]["securitySchemes"]["ApiKeyAuth"]
    for field in ("type", "in", "name"):
        assert live_scheme[field] == contract_scheme[field]

    for path, path_item in contract["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            live_operation = live["paths"][API_PREFIX + path][method]
            assert live_operation.get("security") == operation.get("security"), (method, path)
            if method == "get":
                assert "security" not in operation
