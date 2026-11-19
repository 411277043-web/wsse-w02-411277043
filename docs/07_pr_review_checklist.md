# Pull Request 審查清單（PR Review Checklist）— UnitPriceCompare

> 文件版本：W10（LAB 08）。本作業是個人作業，以下為**自我審查**；沒有其他人參與時，不記為同儕審查或核准。

## 1. PR 說明範本

建立 PR 時，Description 可以直接使用：

```markdown
## 改動內容
- 新增 tests/test_w10_lab.py：T01 排名、T02 拒絕寫入、T03 數量非法
- 在 tests/conftest.py 加入 context fixture（回傳 api 與 Session）
- 新增 docs/06_test_plan.md、docs/07_pr_review_checklist.md
- 沒有修改 app/ 中的任何業務程式

## 測試與需求對應
| 測試 | 預期 | 需求 |
|---|---|---|
| T01 | A 0.0500、B 0.0450 元/mL，排名 B → A，Best Choice 為 B | FR-07～FR-10 |
| T02 | bob 新增商品回 403，items 筆數不變 | SEC-02 |
| T03 | quantity = 0 回 400 INVALID_REQUEST，沒有寫入 | BR-02 |

## 測試結果
- python -m pytest -q tests/test_w10_lab.py：3 passed
- python -m pytest -q：55 passed

## 已知限制與說明
- 本專案 Contract 規定欄位錯誤回 400（老師範例為 422）
- 比價結果路徑為 /api/v1/comparisons/{id}/result，以 Best Choice 表示第一名
```

## 2. 自我審查清單

- [ ] **Files changed** 只有 `tests/`、`docs/`、`README.md` 與 `LAB08_411277043.md`，沒有改到 `app/` 的業務程式。
- [ ] `python -m pytest -q` 全部通過，連續執行兩次結果相同。
- [ ] 測試不依賴自己電腦上的 `unitprice.db` 內容。
- [ ] T02、T03 除了 HTTP 狀態碼，也驗證了資料庫筆數。
- [ ] `git status` 中沒有 `.env`、`*.db`、`venv/` 或真實金鑰。
- [ ] PR 的方向正確：**base** 是 `main`，**compare** 是 `w10-testing`。
- [ ] PR 說明包含測試 ID、對應需求、測試結果與已知限制。
- [ ] 沒有把自我審查寫成「同儕已核准」。
