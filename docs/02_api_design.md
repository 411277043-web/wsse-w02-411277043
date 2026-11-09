# API 設計（API Design）— UnitPriceCompare

> 文件版本：W09（LAB 07）。W04 的完整設計見 `LAB03_411277043.md`。
> Method、Path、成功 Status Code 與 LAB 03 相同；W09 只為寫入 API 加上身分與權限。

## 1. 端點與存取政策

所有路徑的前綴為 `/api/v1`。

| Method／Path | 需求 | 身分與權限 | 成功 | 其他回應 |
|---|---|---|---|---|
| `POST /comparisons` | FR-01、SEC-02 | `X-API-Key` 必填，限 editor | 201 + `Location` | 400、401、403、503 |
| `GET /comparisons/{comparison_id}` | FR-05、SEC-04 | 公開 | 200 | 404 |
| `DELETE /comparisons/{comparison_id}` | FR-11、SEC-03 | `X-API-Key` 必填，限 editor | 204 | 401、403、404、503 |
| `POST /comparisons/{comparison_id}/items` | FR-02、FR-06、SEC-02 | `X-API-Key` 必填，限 editor | 201 + `Location` | 400、401、403、404、503 |
| `PATCH /comparisons/{comparison_id}/items/{item_id}` | FR-03、FR-06、SEC-03 | `X-API-Key` 必填，限 editor | 200 | 400、401、403、404、503 |
| `DELETE /comparisons/{comparison_id}/items/{item_id}` | FR-04、SEC-03 | `X-API-Key` 必填，限 editor | 204 | 401、403、404、503 |
| `GET /comparisons/{comparison_id}/result` | FR-07～FR-10、SEC-04 | 公開 | 200 | 400、404 |

## 2. 錯誤回應

所有錯誤都使用同一個 `ErrorResponse` 格式：`{"code": "...", "message": "..."}`。

| Status | code | 情境 |
|---|---|---|
| 400 | `INVALID_REQUEST` | 欄位缺漏、型別錯誤、違反 BR-01～BR-03、BR-05 |
| 400 | `MEASUREMENT_TYPE_MISMATCH` | 違反 BR-06 |
| 400 | `INSUFFICIENT_ITEMS` | 違反 BR-04 |
| 401 | `UNAUTHENTICATED` | **W09 新增**：沒帶 `X-API-Key` |
| 403 | `FORBIDDEN` | **W09 新增**：金鑰無效（`invalid API key`），或使用者不是 editor（`editor role is required`） |
| 404 | `NOT_FOUND` | Comparison 或 Item 不存在 |
| 503 | `SERVICE_UNAVAILABLE` | **W09 新增**：伺服器的 `W09_USERS_JSON` 未設定或格式錯誤 |

## 3. OpenAPI 安全契約（`openapi.yaml`）

- `components.securitySchemes.ApiKeyAuth`：`type: apiKey`、`in: header`、`name: X-API-Key`。
- 只在 5 條寫入 API 加上 `security: [{ApiKeyAuth: []}]`；2 條 GET 不加，也沒有全域 `security`。
- 寫入 API 加上 `401`、`403`、`503` 回應，分別引用 `Unauthorized`、`Forbidden`、`ServiceUnavailable`。
- OpenAPI 只能說明「這個請求需要金鑰」；**editor／viewer 的權限由後端 `require_editor()` 真正執行**，並由測試驗證。
- FastAPI 的 `APIKeyHeader` 使用 `scheme_name="ApiKeyAuth"`，讓 `/openapi.json` 的名稱與 `openapi.yaml` 相同。

## 4. 檢查順序

先檢查身分與權限，再檢查欄位內容：viewer 送出不合法資料，得到的是 403，而不是 400。只有通過 editor 檢查後，才會依 Schema 與 Business Rules 檢查資料。

## 5. Swagger UI 展示順序

1. 不按 Authorize，呼叫 `POST /comparisons` → 401。
2. Authorize 輸入錯誤金鑰 → 403 `invalid API key`。
3. 改輸入 bob（viewer）的金鑰 → 403 `editor role is required`。
4. 登出 bob，輸入 alice（editor）的金鑰 → 201，記下 `id`。
5. 用 alice 新增 WATER_A、WATER_B → 201；新增 `price: 0` 的商品 → 400 `INVALID_REQUEST`。
6. 呼叫公開的 `GET /comparisons/{id}/result` → 200，WATER_B 為 Best Choice。
