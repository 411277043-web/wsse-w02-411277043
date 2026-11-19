"""LAB 08（W10）：用測試證明 UnitPriceCompare 的排名、權限與輸入驗證「真的」做對了。

每個測試都分成 Arrange（準備資料）、Act（呼叫 API）、Assert（比對結果與資料庫）。
本專案依自己的 Contract（openapi.yaml），與老師範例有兩處不同：
- 比價結果是 GET /api/v1/comparisons/{id}/result（不是 /ranking），回傳各商品單價與 Best Choice。
- 欄位驗證錯誤回 400 INVALID_REQUEST（不是 422），理由見 docs/01_requirements.md 第 3 節。
"""

from decimal import Decimal

from app.models import Item
from tests.conftest import EDITOR, VIEWER

BASE = "/api/v1/comparisons"


def create_comparison(api) -> int:
    """先由 editor 建立合法的比較，取得 comparison_id，避免把 id 寫死成 1。"""
    response = api.post(BASE, json={"name": "飲料單價比較"}, headers=EDITOR)
    assert response.status_code == 201
    return response.json()["id"]


def add_item(api, comparison_id, name, price, quantity, unit="mL", headers=EDITOR):
    return api.post(
        f"{BASE}/{comparison_id}/items",
        json={"name": name, "price": price, "quantity": quantity, "unit": unit},
        headers=headers,
    )


def count_items(Session) -> int:
    """直接查 SQLite 的 items 表，不經過 API。"""
    with Session() as db:
        return db.query(Item).count()


def test_t01_ranking_b_before_a(context):
    """T01：A 30 元／600 mL、B 45 元／1000 mL，B 比較便宜（FR-07～FR-10、BR-08、BR-09）。

    手算的預期結果（Test Oracle）：A = 30 ÷ 600 = 0.0500 元/mL；B = 45 ÷ 1000 = 0.0450 元/mL。
    """
    api, Session = context
    cid = create_comparison(api)
    ids = {}
    for name, price, quantity in [("A", 30, 600), ("B", 45, 1000)]:
        response = add_item(api, cid, name, price, quantity)
        assert response.status_code == 201
        ids[name] = response.json()["id"]

    result = api.get(f"{BASE}/{cid}/result")

    assert result.status_code == 200
    items = result.json()["items"]
    unit_prices = {item["name"]: Decimal(str(item["unit_price"])) for item in items}
    assert unit_prices == {"A": Decimal("0.0500"), "B": Decimal("0.0450")}
    # 依單價由低到高排列，應為 B → A
    ranking = sorted(items, key=lambda item: Decimal(str(item["unit_price"])))
    assert [item["name"] for item in ranking] == ["B", "A"]
    # 本專案的比價結果以 Best Choice 表示第一名
    assert result.json()["best_choice_item_ids"] == [ids["B"]]


def test_t02_viewer_cannot_add_item_and_nothing_is_written(context):
    """T02：bob（viewer）新增商品回 403，而且 items 表的筆數不變（SEC-02）。

    只看到 403 還不夠：必須證明被拒絕的請求沒有留下任何資料（沒有副作用）。
    """
    api, Session = context
    cid = create_comparison(api)
    assert add_item(api, cid, "A", 30, 600).status_code == 201
    before = count_items(Session)

    response = add_item(api, cid, "C", 10, 300, headers=VIEWER)

    after = count_items(Session)
    assert response.status_code == 403
    assert response.json() == {"code": "FORBIDDEN", "message": "editor role is required"}
    assert after == before == 1
    assert [i["name"] for i in api.get(f"{BASE}/{cid}").json()["items"]] == ["A"]


def test_t03_zero_quantity_rejected_and_nothing_is_written(context):
    """T03：alice（editor）新增 quantity=0 的商品被拒絕，而且沒有寫入（BR-02）。

    這是輸入驗證問題，不是權限問題，所以用合法的 editor 金鑰。
    老師範例預期 422；本專案 Contract 規定欄位錯誤回 400 INVALID_REQUEST。
    """
    api, Session = context
    cid = create_comparison(api)

    response = add_item(api, cid, "C", 10, 0)

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert "quantity" in body["message"] and "BR-02" in body["message"]
    assert api.get(f"{BASE}/{cid}").json()["items"] == []
    assert count_items(Session) == 0
