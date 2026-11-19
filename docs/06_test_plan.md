# 測試計畫（Test Plan）— UnitPriceCompare

> 文件版本：W10（LAB 08）。W10 不新增業務 API，只新增測試與文件，為 W08、W09 已完成的功能留下品質證據。

## 1. 測試方法

1. **先寫出可判定的預期結果（Test Oracle）**：用手算決定正確答案，而不是執行後再照抄輸出。
2. **Arrange／Act／Assert**：準備隔離的資料 → 呼叫 API → 同時比對 HTTP 回應與資料庫內容。
3. **在分支執行 pytest**，通過後以 Pull Request 說明改動、測試與風險。

HTTP 狀態碼、資料庫筆數與業務計算結果是**三種不同的證據**。例如只看到 403，並不能證明資料沒有被寫入，所以 T02、T03 都會直接查詢 SQLite。

## 2. 核心測試（`tests/test_w10_lab.py`）

| 測試 | Arrange／Act | 預期結果（Test Oracle） | 對應需求 |
|---|---|---|---|
| T01 排名 | 新增 A 30 元／600 mL、B 45 元／1000 mL，取得比價結果 | A = 30 ÷ 600 = **0.0500** 元/mL；B = 45 ÷ 1000 = **0.0450** 元/mL；依單價排序為 **B → A**；Best Choice 為 B | FR-07～FR-10、BR-08、BR-09 |
| T02 拒絕寫入 | 已有 1 個商品；bob（viewer）新增商品 C | **403** `FORBIDDEN`；items 表筆數**前後都是 1**；GET 只看得到 A | SEC-02 |
| T03 數量非法 | alice（editor）新增 `quantity: 0` 的商品 | **400** `INVALID_REQUEST`，訊息指出 `quantity` 與 BR-02；比較中沒有商品；items 表筆數為 **0** | FR-06、BR-02 |

### 與老師範例的差異

| 項目 | 老師範例 | 本專案 | 理由 |
|---|---|---|---|
| 比價結果路徑 | `GET /comparisons/{id}/ranking` | `GET /api/v1/comparisons/{id}/result` | 依自己的 LAB 03、LAB 04 Contract |
| 排名的表示方式 | 回傳已排序的清單 | 回傳各商品單價與 `best_choice_item_ids` | LAB 02 FR-09、FR-10 的設計；T01 依單價排序後驗證 B → A，並驗證 Best Choice 為 B |
| 數量非法 | 422 | **400** `INVALID_REQUEST` | LAB 03、LAB 04 規定欄位錯誤回 400，W08 起一直依此實作 |
| fixture | 新建 `tests/conftest.py` 的 `context` | 在既有 `tests/conftest.py` 加入 `context` | 老師第 89 頁：已有 fixture 時「整合而非建立重複的同名 Fixture」 |

## 3. 延伸測試（已存在於 W08、W09 的測試中）

老師列出的延伸案例，本專案先前已經寫好，不重複撰寫：

| 延伸案例 | 預期結果 | 測試 |
|---|---|---|
| quantity = -1 | 400，訊息指出 BR-02 | `tests/test_api.py::test_ac_06_02_quantity_must_be_greater_than_zero`（同時測 -1 與 0） |
| 1 L 換算 | 1 L → 1000 mL；1.5 kg → 1500 g | `tests/test_api.py::test_ac_07_01_unit_conversion`、`tests/test_service.py::test_unit_converter` |
| g 與 mL 不能混在同一個比較 | 400 `MEASUREMENT_TYPE_MISMATCH`，且資料沒有新增 | `tests/test_api.py::test_ac_06_03_measurement_type_mismatch_is_rejected` |

## 4. 隔離與可重複執行

- 每個測試都使用**全新的記憶體 SQLite**（`tests/conftest.py` 的 `database` fixture），測試結束就丟棄，不會寫入 `unitprice.db`。
- 測試使用的金鑰是 `tests/conftest.py` 中的假金鑰，由 `monkeypatch` 注入 `W09_USERS_JSON`，不依賴任何人電腦上的設定。
- 連續執行兩次 `python -m pytest -q`，結果都是 **55 passed**。T03 的「筆數為 0」也證明每個測試都從乾淨的資料庫開始。

## 5. 測試真的能抓到錯誤嗎？（故障注入）

為了確認測試不是「永遠綠燈」，在專案的**副本**中故意放進錯誤後執行測試（正式程式沒有被修改）：

| 故意放進的錯誤 | 抓到的測試 |
|---|---|
| `require_editor` 也放行 viewer | ❌ T02 失敗 |
| `quantity` 允許等於 0 | ❌ T03 失敗 |
| Best Choice 改成取最高單價 | ❌ T01 失敗 |
| 1 L 誤換算成 100 mL | T01～T03 沒有抓到（只用 mL）；**完整測試中有 8 個失敗**，包括 `test_ac_07_01_unit_conversion` |

第 4 項說明：核心三個測試各自只負責一個風險，因此需要延伸測試補足單位換算。

## 6. 執行方式

在專案根目錄：

```bash
python -m pytest -q tests/test_w10_lab.py
```

```bash
python -m pytest -q
```

預期結果：`3 passed`、`55 passed`。
