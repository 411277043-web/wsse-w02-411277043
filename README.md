# wsse-w02-411277043

網際服務軟體工程（Web Service Software Engineering）個人 Engineering LAB Repository。

- Student ID: 411277043
- GitHub Username: 411277043-web
- Case: UnitPriceCompare（單位價格比較服務）

## LAB 紀錄

| LAB | 週次 | 主題 | 檔案 |
|---|---|---|---|
| LAB 01 | W02 | Web Service 操作與環境就緒檢核 | [LAB01_411277043.md](LAB01_411277043.md) |
| LAB 02 | W03 | 需求工程（Requirements Engineering） | [LAB02_411277043.md](LAB02_411277043.md) |
| LAB 03 | W04 | RESTful API 設計（RESTful API Design） | [LAB03_411277043.md](LAB03_411277043.md) |
| LAB 04 | W06 | API 契約與 OpenAPI（API Contract & OpenAPI） | [LAB04_411277043_openapi.yaml](LAB04_411277043_openapi.yaml) |
| LAB 05 | W07 | 系統架構與資料建模（Architecture & Data Modeling） | [LAB05_411277043.md](LAB05_411277043.md) |
| LAB 06 | W08 | 資料庫設計與核心功能實作（Database Design & Core Implementation） | [LAB06_411277043.md](LAB06_411277043.md)、[app/](app/)、[tests/](tests/) |
| LAB 07 | W09 | API 安全性與驗證機制（API Security & Authentication） | [LAB07_411277043.md](LAB07_411277043.md)、[docs/](docs/)、[openapi.yaml](openapi.yaml) |

## 執行 UnitPriceCompare API（LAB 06、LAB 07）

依 `openapi.yaml` Contract 實作 7 條 API，資料存在 SQLite。LAB 07 起，新增、修改、刪除需要 editor 的 `X-API-Key`；查詢比較與比價結果不需要金鑰。

### 1. 安裝套件

```bash
python -m pip install -r requirements-dev.txt
```

### 2. 啟動 API

先設定示範使用者：alice 是 editor、bob 是 viewer。金鑰只在自己的終端機設定，**不要寫進任何檔案或提交到 GitHub**（格式見 `.env.example`）。

```bash
export W09_USERS_JSON='{"alice":{"key":"classroom-editor-demo","role":"editor"},"bob":{"key":"classroom-viewer-demo","role":"viewer"}}'
```

```bash
python -m uvicorn app.main:app --reload
```

- Swagger UI：`http://127.0.0.1:8000/docs`
- 所有 API 的前綴為 `/api/v1`（LAB 04 `servers.url`）。
- 資料存在專案根目錄的 `unitprice.db`，重新啟動 API 後資料仍在；此檔已列入 `.gitignore`，不提交到 GitHub。

### 3. 執行自動化測試

```bash
python -m pytest -q
```

測試使用記憶體資料庫與測試專用的假金鑰，不會動到 `unitprice.db`，也不需要先設定 `W09_USERS_JSON`。

### 4. 在 Swagger UI 操作一次完整流程

先按右上角 **Authorize**，輸入 alice 的金鑰 `classroom-editor-demo`。用 bob 的金鑰或不輸入金鑰時，新增、修改、刪除會得到 403 或 401；完整的權限展示步驟見 [docs/05_git_submission.md](docs/05_git_submission.md)。

1. `POST /api/v1/comparisons`，Body：`{"name": "超商瓶裝水"}` → `201`，記下回傳的 `id`。
2. `POST /api/v1/comparisons/{id}/items`，Body：`{"name": "WATER_A", "price": 45, "quantity": 500, "unit": "mL"}` → `201`。
3. 再新增 `{"name": "WATER_B", "price": 80, "quantity": 1, "unit": "L"}` → `201`。
4. `GET /api/v1/comparisons/{id}/result` → `200`：WATER_A 為 0.09 元/mL、WATER_B 為 0.08 元/mL，`best_choice_item_ids` 為 WATER_B。
5. 錯誤情況：
   - 新增 `price: 0` 的商品 → `400 INVALID_REQUEST`（BR-01）
   - 在同一比較新增 `unit: "g"` 的商品 → `400 MEASUREMENT_TYPE_MISMATCH`（BR-06）
   - 對只有 1 個商品的比較取得結果 → `400 INSUFFICIENT_ITEMS`（BR-04）
   - 查詢不存在的比較 → `404 NOT_FOUND`

### 5. 專案結構（對應 LAB 05 架構）

| 檔案 | 層級 | 責任 |
|---|---|---|
| `app/main.py` | Router | 7 條 API、Status Code 與 `Location`、把錯誤轉成 `ErrorResponse` |
| `app/security.py` | Router（安全依賴） | LAB 07：以 `X-API-Key` 辨識使用者，`require_editor` 限制寫入 |
| `app/schemas.py` | Router（Schema） | Request／Response 格式與單一欄位驗證（BR-01～BR-03、BR-05） |
| `app/service.py` | Service | `UnitConverter`、BR-04、BR-06～BR-10 |
| `app/exceptions.py` | Service | 業務錯誤，不含 HTTP 細節 |
| `app/repository.py` | Repository | 讀寫 Comparison／Item |
| `app/models.py`、`app/database.py` | Database | SQLite 資料表與連線 |
| `tests/` | 測試 | 驗收測試（AC）、安全測試（SEC）、Service 單元測試、Contract 一致性檢查 |
| `openapi.yaml` | Contract | 目前的 API 契約（LAB 04 加上 LAB 07 的安全契約）；`LAB04_411277043_openapi.yaml` 保留 W06 繳交版本 |
| `docs/` | 文件 | W09 版的需求、API 設計、架構、追溯矩陣與提交指引 |

## LAB 01 Teaching Mock

根目錄的 `main.py` 是 LAB 01 的教學 Mock（`POST /compare`），保留作為紀錄。LAB 03 起改為 Resource-based 設計，由 `app/` 取代。

```bash
python -m uvicorn main:app --reload
```
