# 軟體架構與資料模型（Architecture & Data Model）— UnitPriceCompare

> 文件版本：W09（LAB 07）。W07 的完整設計見 `LAB05_411277043.md`。
> W08 的 Router／Service／Repository、資料表與比價規則都不變；W09 只新增一個安全模組。

## 1. 本週的架構變更

```text
Client（寫入請求：Header X-API-Key + JSON）
    │
    ▼
Router  app/main.py ── Security(require_editor) ──▶ app/security.py
    │                                                ├─ load_users()：讀 W09_USERS_JSON
    │                                                ├─ APIKeyHeader：取 X-API-Key
    │                                                ├─ identify_user()：金鑰 → CurrentUser
    │                                                └─ require_editor()：editor 才放行
    │                                                         │
    │                                                   401／403／503
    ▼（通過身分與權限檢查後）
Schema 驗證 → Service（BR-04、BR-06～BR-10）→ Repository → SQLite

Client（GET，不需金鑰）→ Router → Service → Repository → SQLite
```

核心原則：**沒有通過 editor 檢查，就不會進入 Service，也不會寫入資料庫。**

## 2. 模組責任

| 檔案 | 層級 | 責任 | 本週變更 |
|---|---|---|---|
| `app/security.py` | Router 的安全依賴 | `APIKeyHeader`、`CurrentUser`、`load_users`、`identify_user`、`require_editor` | **W09 新增** |
| `app/main.py` | Router | 7 條 API；5 條寫入 API 加上 `Security(require_editor)`；401／403／503 轉成 `ErrorResponse` | **W09 修改** |
| `app/schemas.py` | Router（Schema） | Request／Response 格式；`ErrorResponse` 新增 3 個錯誤代碼 | **W09 修改** |
| `app/service.py` | Service | `UnitConverter`、BR-04、BR-06～BR-10 | 沿用 W08 |
| `app/exceptions.py` | Service | 業務錯誤 | 沿用 W08 |
| `app/repository.py` | Repository | 讀寫 Comparison／Item | 沿用 W08 |
| `app/models.py`、`app/database.py` | Database | SQLite 資料表與連線 | 沿用 W08 |
| `openapi.yaml` | Contract | 加上 `ApiKeyAuth` 與寫入 API 的 401／403／503 | **W09 新增**（以 LAB 04 為基礎） |

身分與權限放在 Router 層，而不是 Service：Service 只處理比價規則，不需要知道「誰在呼叫」，這樣 W08 的 Service 單元測試完全不用修改。

## 3. 資料模型不變（這是正確的設計選擇）

- `comparisons(id PK, name, created_at)`
- `items(id PK, comparison_id FK → comparisons.id, name, price, quantity, unit)`
- 一個 Comparison 有多個 Item（1:N），刪除 Comparison 時一併刪除其 Item。
- alice／bob 的 `username`、`key`、`role` 來自伺服器環境變數 `W09_USERS_JSON`，**沒有存進上述資料表，也沒有新建 users 表**。
- 沒有記錄 `created_by`，因此**不能主張已實作資料擁有權**：任何 editor 都能修改任何比較。

## 4. 安全界線

- 角色只由伺服器依金鑰決定；Client 在 Body 自稱 `role: editor` 無效。
- 金鑰以 `secrets.compare_digest` 比對。
- 使用者設定缺漏或格式錯誤時回 503，不會默默放行。
- 課堂示範金鑰不是正式秘密；正式系統還需要 HTTPS、金鑰撤銷與輪替、存取紀錄、速率限制與資料層級授權。
