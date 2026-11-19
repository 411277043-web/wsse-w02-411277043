# 需求規格（Requirements）— UnitPriceCompare

> 文件版本：W09（LAB 07）。W03 的完整需求見 `LAB02_411277043.md`。
> 本文件保留 FR-01～FR-11、BR-01～BR-10 不變，新增 W09 安全需求 SEC-01～SEC-06。

## 1. 既有功能需求（沿用 LAB 02，不變）

| ID | 功能需求 | API |
|---|---|---|
| FR-01 | 建立一次商品比較 | `POST /comparisons` |
| FR-02 | 在比較中加入商品（名稱、價格、數量、單位） | `POST /comparisons/{comparison_id}/items` |
| FR-03 | 修改比較中既有商品 | `PATCH /comparisons/{comparison_id}/items/{item_id}` |
| FR-04 | 從比較中移除商品 | `DELETE /comparisons/{comparison_id}/items/{item_id}` |
| FR-05 | 查看比較目前包含的商品 | `GET /comparisons/{comparison_id}` |
| FR-06 | 依 Business Rules 驗證商品資料 | 新增、修改商品時檢查 |
| FR-07～FR-10 | 單位換算、計算 Unit Price、找出 Best Choice、回傳比較結果 | `GET /comparisons/{comparison_id}/result` |
| FR-11 | 刪除一次比較 | `DELETE /comparisons/{comparison_id}` |

所有路徑的前綴為 `/api/v1`。Business Rules（BR-01～BR-10）與 Acceptance Criteria 皆沿用 LAB 02，**W09 不修改任何比價規則**。

## 2. W09 新增安全需求（Security Requirements）

| ID | 需求 | 看得見的驗收結果 |
|---|---|---|
| SEC-01 | 伺服器依每位使用者不同的 API Key（`X-API-Key`）辨識身分 | alice、bob 的金鑰分別對應到不同使用者；Request Body 自稱 `role: editor` 無效 |
| SEC-02 | 只有 `editor` 能新增資料 | `POST /comparisons`、`POST /comparisons/{id}/items`：editor 回 201；viewer 回 403，且資料沒有增加 |
| SEC-03 | 只有 `editor` 能修改或刪除資料 | `PATCH` 商品、`DELETE` 商品、`DELETE` 比較：viewer 回 403，資料不變 |
| SEC-04 | 拒絕缺漏或錯誤的憑證；查詢維持公開 | 沒帶 `X-API-Key` 回 401；未知金鑰回 403；2 條 GET 不需要金鑰 |
| SEC-05 | 使用者與角色由伺服器設定管理 | `W09_USERS_JSON` 未設定或格式錯誤時，受保護的 API 回 503；Repository 中沒有真實金鑰、`.env`、`*.db` |
| SEC-06 | 安全升級不破壞原有功能 | editor 送出不合法資料仍回 400 `INVALID_REQUEST`；比價結果與 W08 相同 |

## 3. 設計決定

### 為什麼保護 5 條寫入 API，而不只 2 條 POST

老師的範例 LostFoundMatch 只有「新增」與「查詢」，所以只保護 2 條 POST。UnitPriceCompare 另外還有修改商品、移除商品、刪除比較。如果只保護 POST，viewer 雖然不能新增，卻能刪掉 editor 建立的資料，這違反「viewer 只能查詢、排序」的目的。因此所有**會改變資料**的操作都要求 editor（SEC-02、SEC-03），2 條 GET 維持公開（SEC-04）。

### 欄位錯誤是 400，不是 422

老師驗收表寫「商品資料不合法 → 422」。本服務在 LAB 03、LAB 04 已規定欄位錯誤回 `400 INVALID_REQUEST`，W08 實作也依此處理；為了與自己的 Contract 一致，W09 維持 400。驗收時「editor 送出不合法資料」對應的是 400。

### 為什麼無效金鑰是 403，缺少金鑰是 401

依課堂範例：沒帶金鑰代表「還沒表明身分」，回 401；帶了金鑰但查不到使用者，或使用者不是 editor，都是「身分不允許這個操作」，回 403。

## 4. 非功能需求

- 沿用 LAB 02 的 NFR-01～NFR-03。
- 金鑰只放在伺服器環境變數 `W09_USERS_JSON`，不寫在程式碼、README 或 GitHub；`.env.example` 只放 `change-me` 示範值。
- 比對金鑰使用 `secrets.compare_digest`。
- `openapi.yaml` 明確描述 `ApiKeyAuth` 與 401／403／503 回應，並能與 `/openapi.json` 對照。

## 5. 範圍限制

不包含帳號密碼登入、金鑰自助申請或撤銷、資料擁有者權限（沒有記錄 `created_by`，因此 editor 可以修改任何比較）、HTTPS、速率限制。`W09_USERS_JSON` 不是資料庫中的使用者資料表。
