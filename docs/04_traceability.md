# 需求、契約、程式與測試追溯矩陣（Traceability）— UnitPriceCompare

> 文件版本：W09（LAB 07）。所有 API 路徑的前綴為 `/api/v1`。

## 1. 既有功能追溯（W08 完成，本週保持）

| ID | API | Schema／資料 | 程式 | 測試（`tests/test_api.py`） |
|---|---|---|---|---|
| FR-01 | `POST /comparisons` | `ComparisonCreate` → `Comparison`；`comparisons` | `main.create_comparison` → `service.create_comparison` | `test_ac_01_01_create_empty_comparison` |
| FR-02 | `POST /comparisons/{id}/items` | `ItemCreate` → `Item`；`items` | `main.add_item` → `service.add_item` | `test_ac_02_01_add_item` |
| FR-03 | `PATCH /comparisons/{id}/items/{item_id}` | `ItemUpdate` → `Item` | `main.update_item` → `service.update_item` | `test_ac_03_01_update_price_creates_tie` |
| FR-04 | `DELETE /comparisons/{id}/items/{item_id}` | — | `main.delete_item` → `service.delete_item` | `test_ac_04_01_remove_item` |
| FR-05 | `GET /comparisons/{id}` | `Comparison` | `main.get_comparison` → `service.get_comparison` | `test_ac_05_01_view_comparison_lists_items_in_order` |
| FR-06 | 新增、修改商品 | Schema（BR-01～03、05）、Service（BR-06） | `schemas.ItemCreate`、`service._ensure_same_measurement_type` | `test_ac_06_01`～`test_ac_06_04` |
| FR-07～FR-10 | `GET /comparisons/{id}/result` | `ComparisonResult` | `service.UnitConverter`、`service.calculate_result` | `test_ac_07_01`、`test_ac_09_01`、`test_ac_10_01`、`test_ac_10_02`；`tests/test_service.py` |
| FR-11 | `DELETE /comparisons/{id}` | — | `main.delete_comparison` → `service.delete_comparison` | `test_ac_11_01_delete_comparison` |

## 2. W09 安全需求追溯（新增）

| ID | 設計／OpenAPI | Python 位置 | 測試（`tests/test_security.py`） |
|---|---|---|---|
| SEC-01 | `ApiKeyAuth`：`X-API-Key`；每位使用者不同金鑰 | `security.api_key_header`、`identify_user` | `test_sec_01_role_comes_from_server_not_request_body` |
| SEC-02 | 2 條 POST 的 operation-level `security` | `main.create_comparison`、`main.add_item`：`Security(require_editor)` | `test_sec_02_editor_can_create`、`test_sec_02_viewer_cannot_create` |
| SEC-03 | PATCH、2 條 DELETE 的 operation-level `security` | `main.update_item`、`main.delete_item`、`main.delete_comparison` | `test_sec_03_viewer_cannot_modify_or_delete`、`test_sec_03_editor_can_modify_and_delete` |
| SEC-04 | 401、403 回應；GET 沒有 `security` | `security.identify_user`、`require_editor` | `test_sec_04_missing_key_returns_401`、`test_sec_04_unknown_key_returns_403`、`test_sec_04_get_endpoints_stay_public` |
| SEC-05 | 503 回應；金鑰由伺服器設定 | `security.load_users`；`.env.example`、`.gitignore` | `test_sec_05_invalid_server_configuration_returns_503`、`test_sec_05_missing_server_configuration_returns_503` |
| SEC-06 | 400、200 回應維持 | `schemas.py`、`service.py` 不變 | `test_sec_06_editor_invalid_data_still_returns_400`、`test_sec_06_result_unchanged_after_security_upgrade` |

## 3. 契約一致性

`tests/test_contract_sync.py` 自動比對 `openapi.yaml` 與實際的 `/openapi.json`：

| 檢查項目 | 測試 |
|---|---|
| 路徑與 Method 完全相同 | `test_paths_and_methods_match_contract` |
| operationId 與每條 API 的 Status Code 相同（含 400 而非 422、寫入 API 的 401／403／503） | `test_operation_ids_and_status_codes_match_contract` |
| Schema 欄位名稱相同 | `test_schema_fields_match_contract` |
| `ApiKeyAuth` 相同；寫入 API 有 `security`、GET 沒有 | `test_security_matches_contract` |

## 4. 逐檔交叉檢查

1. `docs/01_requirements.md`：FR、SEC 都已定義。
2. `openapi.yaml`：`ApiKeyAuth`、5 條寫入 API 的 `security` 與 401／403／503；GET 沒有 `security`。
3. `app/security.py` + `app/main.py`：真的執行身分辨識與授權，不是只有文件文字。
4. `app/models.py`、`app/database.py`：W08 的 SQLite 結構沒有被改動。
5. `tests/`：`python -m pytest -q` 全部通過。
6. `/docs`：看得到 Authorize 按鈕，以及每個情境的 Status Code 與回應內容。
