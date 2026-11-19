# 展示與提交指引（Git Submission）— UnitPriceCompare

> 文件版本：W09（LAB 07）。

## 1. 啟動

在專案根目錄：

```bash
python -m pip install -r requirements-dev.txt
```

設定兩位示範使用者（只在自己的終端機設定，**不要把真正的金鑰寫進任何檔案或提交到 GitHub**）：

```bash
export W09_USERS_JSON='{"alice":{"key":"classroom-editor-demo","role":"editor"},"bob":{"key":"classroom-viewer-demo","role":"viewer"}}'
```

```bash
python -m uvicorn app.main:app --reload
```

開啟 `http://127.0.0.1:8000/docs`。

## 2. 展示順序（Swagger UI）

| 步驟 | 操作 | 預期結果 |
|---|---|---|
| 1 | 不按 Authorize，`POST /api/v1/comparisons` | 401 `UNAUTHENTICATED` |
| 2 | Authorize 輸入 `wrong-key`，再 POST | 403 `invalid API key` |
| 3 | 改輸入 bob 的金鑰 `classroom-viewer-demo`，再 POST | 403 `editor role is required`，資料沒有新增 |
| 4 | 登出 bob，輸入 alice 的金鑰 `classroom-editor-demo`，POST `{"name": "超商瓶裝水"}` | 201，記下 `id` |
| 5 | 用 alice 新增 `{"name": "WATER_A", "price": 45, "quantity": 500, "unit": "mL"}` 與 `{"name": "WATER_B", "price": 80, "quantity": 1, "unit": "L"}` | 兩次都是 201 |
| 6 | 用 alice 新增 `price: 0` 的商品 | 400 `INVALID_REQUEST`（本服務 Contract 的驗證錯誤） |
| 7 | 用 bob 的金鑰 `DELETE /api/v1/comparisons/{id}` | 403，比較仍然存在 |
| 8 | 呼叫公開的 `GET /api/v1/comparisons/{id}/result` | 200：WATER_A 0.09、WATER_B 0.08，Best Choice 為 WATER_B |

每次切換使用者前，先在 Authorize 視窗按 Logout 清掉舊金鑰。

## 3. 自動化測試

另開一個終端機：

```bash
python -m pytest -q
```

測試會自行注入假金鑰，不需要先設定 `W09_USERS_JSON`，也不會動到 `unitprice.db`。

## 4. Git 提交

```bash
git status
git add app tests docs openapi.yaml README.md LAB07_411277043.md .gitignore .env.example
git commit -m "feat: add LAB 07 API key authentication and editor authorization"
git push -u origin feature/lab07-security
git rev-parse HEAD
```

提交前確認 `git status` 中**沒有** `.env`、`unitprice.db`、`venv/` 或任何真正的金鑰。

## 5. 驗收證據

- GitHub Repository URL、Branch `feature/lab07-security`、Commit SHA
- `/docs` 的展示結果：401、403（錯誤金鑰）、403（viewer）、201（editor）、400（不合法資料）、GET 200
- `python -m pytest -q` 全部通過
- `docs/04_traceability.md` 的安全需求追溯矩陣
