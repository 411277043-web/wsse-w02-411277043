"""LAB 06 驗收測試：每個測試對應 LAB 02 的 Acceptance Criteria（AC-xx-xx）或 Business Rule。"""

from datetime import datetime

BASE = "/api/v1/comparisons"


def create_comparison(client, **body) -> int:
    response = client.post(BASE, json=body) if body else client.post(BASE)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def add_item(client, comparison_id, name, price, quantity, unit):
    return client.post(
        f"{BASE}/{comparison_id}/items",
        json={"name": name, "price": price, "quantity": quantity, "unit": unit},
    )


def add_item_ok(client, comparison_id, name, price, quantity, unit) -> int:
    response = add_item(client, comparison_id, name, price, quantity, unit)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def get_result(client, comparison_id):
    return client.get(f"{BASE}/{comparison_id}/result")


# ---------- FR-01、FR-05：建立與查看比較 ----------


def test_ac_01_01_create_empty_comparison(client):
    response = client.post(BASE)  # Contract：可以不傳 Body
    assert response.status_code == 201
    body = response.json()
    assert body["items"] == []
    assert body["measurement_type"] is None
    assert body["name"] is None
    assert response.headers["Location"] == f"{BASE}/{body['id']}"
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None  # 帶時區的 date-time


def test_create_comparison_with_name(client):
    response = client.post(BASE, json={"name": "超商瓶裝水"})
    assert response.status_code == 201
    assert response.json()["name"] == "超商瓶裝水"


def test_ac_05_01_view_comparison_lists_items_in_order(client):
    cid = create_comparison(client)
    add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    add_item_ok(client, cid, "WATER_B", 80, 1, "L")

    response = client.get(f"{BASE}/{cid}")
    assert response.status_code == 200
    body = response.json()
    assert body["measurement_type"] == "VOLUME"
    assert [(i["name"], i["price"], i["quantity"], i["unit"]) for i in body["items"]] == [
        ("WATER_A", 45, 500, "mL"),
        ("WATER_B", 80, 1, "L"),
    ]


# ---------- FR-02：新增商品 ----------


def test_ac_02_01_add_item(client):
    cid = create_comparison(client)
    response = add_item(client, cid, "WATER_A", 45, 500, "mL")
    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "name": "WATER_A",
        "price": 45,
        "quantity": 500,
        "unit": "mL",
        "measurement_type": "VOLUME",
    }
    assert response.headers["Location"] == f"{BASE}/{cid}/items/{body['id']}"


def test_add_item_to_missing_comparison_returns_404(client):
    response = add_item(client, 999, "WATER_A", 45, 500, "mL")
    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "comparison 999 not found"}


# ---------- FR-06：輸入驗證（BR-01～BR-03、BR-05、BR-06） ----------


def test_ac_06_01_price_must_be_greater_than_zero(client):
    cid = create_comparison(client)
    response = add_item(client, cid, "WATER_A", 0, 500, "mL")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert "price" in body["message"] and "BR-01" in body["message"]


def test_ac_06_02_quantity_must_be_greater_than_zero(client):
    cid = create_comparison(client)
    for quantity in (-1, 0):
        response = add_item(client, cid, "WATER_A", 45, quantity, "mL")
        assert response.status_code == 400
        assert "quantity" in response.json()["message"]
        assert "BR-02" in response.json()["message"]


def test_br_03_name_must_not_be_blank(client):
    cid = create_comparison(client)
    for name in ("", "   "):
        response = add_item(client, cid, name, 45, 500, "mL")
        assert response.status_code == 400
        assert "BR-03" in response.json()["message"]


def test_ac_06_03_measurement_type_mismatch_is_rejected(client):
    cid = create_comparison(client)
    add_item_ok(client, cid, "WATER_A", 45, 500, "mL")

    response = add_item(client, cid, "RICE", 100, 1, "g")
    assert response.status_code == 400
    assert response.json() == {
        "code": "MEASUREMENT_TYPE_MISMATCH",
        "message": "unit g (WEIGHT) does not match the comparison's measurement type VOLUME (BR-06)",
    }
    # 被拒絕的商品不應存進資料庫
    assert len(client.get(f"{BASE}/{cid}").json()["items"]) == 1


def test_ac_06_04_unsupported_unit_is_rejected(client):
    cid = create_comparison(client)
    response = add_item(client, cid, "WATER_A", 45, 16, "oz")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert "unit" in body["message"] and "BR-05" in body["message"]


def test_extra_and_missing_fields_are_rejected(client):
    cid = create_comparison(client)
    extra = client.post(
        f"{BASE}/{cid}/items",
        json={"name": "A", "price": 1, "quantity": 1, "unit": "mL", "color": "red"},
    )
    missing = client.post(f"{BASE}/{cid}/items", json={"name": "A", "price": 1})
    assert extra.status_code == missing.status_code == 400
    assert "color" in extra.json()["message"]
    assert "quantity" in missing.json()["message"] and "unit" in missing.json()["message"]


# ---------- FR-03、FR-04：修改與移除商品 ----------


def test_ac_03_01_update_price_creates_tie(client):
    cid = create_comparison(client)
    water_a = add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    water_b = add_item_ok(client, cid, "WATER_B", 80, 1, "L")

    response = client.patch(f"{BASE}/{cid}/items/{water_a}", json={"price": 40})
    assert response.status_code == 200
    assert response.json()["price"] == 40

    result = get_result(client, cid).json()
    assert result["items"][0]["unit_price"] == 0.08
    assert result["best_choice_item_ids"] == [water_a, water_b]


def test_update_item_follows_business_rules(client):
    cid = create_comparison(client)
    water_a = add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    add_item_ok(client, cid, "WATER_B", 80, 1, "L")
    url = f"{BASE}/{cid}/items/{water_a}"

    assert client.patch(url, json={}).status_code == 400  # 至少一個欄位
    assert client.patch(url, json={"price": None}).status_code == 400  # 不可為 null
    assert client.patch(url, json={"quantity": 0}).status_code == 400  # BR-02
    mismatch = client.patch(url, json={"unit": "kg"})  # BR-06
    assert mismatch.status_code == 400
    assert mismatch.json()["code"] == "MEASUREMENT_TYPE_MISMATCH"
    assert client.patch(url, json={"unit": "L", "quantity": 0.5}).status_code == 200


def test_only_item_can_change_measurement_type(client):
    # 比較中只有一個商品時，沒有「其他商品」可比，因此允許改成別的 Measurement Type
    cid = create_comparison(client)
    item = add_item_ok(client, cid, "RICE", 100, 500, "mL")
    assert client.patch(f"{BASE}/{cid}/items/{item}", json={"unit": "g"}).status_code == 200
    assert client.get(f"{BASE}/{cid}").json()["measurement_type"] == "WEIGHT"


def test_item_must_belong_to_comparison(client):
    first = create_comparison(client)
    second = create_comparison(client)
    item = add_item_ok(client, first, "WATER_A", 45, 500, "mL")
    assert client.patch(f"{BASE}/{second}/items/{item}", json={"price": 1}).status_code == 404
    assert client.delete(f"{BASE}/{second}/items/{item}").status_code == 404


def test_ac_04_01_remove_item(client):
    cid = create_comparison(client)
    first = add_item_ok(client, cid, "A", 10, 100, "mL")
    second = add_item_ok(client, cid, "B", 20, 100, "mL")
    third = add_item_ok(client, cid, "C", 30, 100, "mL")

    response = client.delete(f"{BASE}/{cid}/items/{second}")
    assert response.status_code == 204
    assert response.content == b""

    result = get_result(client, cid).json()
    assert [i["item_id"] for i in result["items"]] == [first, third]


def test_measurement_type_resets_after_all_items_removed(client):
    cid = create_comparison(client)
    item = add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    client.delete(f"{BASE}/{cid}/items/{item}")
    assert client.get(f"{BASE}/{cid}").json()["measurement_type"] is None
    assert add_item(client, cid, "RICE", 100, 1, "kg").status_code == 201


# ---------- FR-07～FR-10：比價結果 ----------


def test_ac_10_01_normal_comparison(client):
    cid = create_comparison(client)
    water_a = add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    water_b = add_item_ok(client, cid, "WATER_B", 80, 1, "L")

    response = get_result(client, cid)
    assert response.status_code == 200
    assert response.json() == {
        "comparison_id": cid,
        "measurement_type": "VOLUME",
        "base_unit": "mL",
        "items": [
            {"item_id": water_a, "name": "WATER_A", "price": 45, "quantity": 500, "unit": "mL",
             "normalized_quantity": 500, "unit_price": 0.09},
            {"item_id": water_b, "name": "WATER_B", "price": 80, "quantity": 1, "unit": "L",
             "normalized_quantity": 1000, "unit_price": 0.08},
        ],
        "best_choice_item_ids": [water_b],
    }


def test_ac_07_01_unit_conversion(client):
    volume = create_comparison(client)
    add_item_ok(client, volume, "A", 30, 1, "L")
    add_item_ok(client, volume, "B", 20, 500, "mL")
    assert get_result(client, volume).json()["items"][0]["normalized_quantity"] == 1000

    weight = create_comparison(client)
    add_item_ok(client, weight, "RICE_A", 150, 1.5, "kg")
    add_item_ok(client, weight, "RICE_B", 60, 500, "g")
    result = get_result(client, weight).json()
    assert result["base_unit"] == "g"
    assert result["items"][0]["normalized_quantity"] == 1500


def test_count_measurement_type(client):
    cid = create_comparison(client)
    add_item_ok(client, cid, "EGG_6", 60, 6, "piece")
    egg_10 = add_item_ok(client, cid, "EGG_10", 90, 10, "piece")
    result = get_result(client, cid).json()
    assert result["measurement_type"] == "COUNT"
    assert result["base_unit"] == "piece"
    assert result["best_choice_item_ids"] == [egg_10]


def test_ac_09_01_tie_lists_all_best_choices_in_added_order(client):
    cid = create_comparison(client)
    juice_a = add_item_ok(client, cid, "JUICE_A", 30, 300, "mL")
    juice_b = add_item_ok(client, cid, "JUICE_B", 60, 0.6, "L")

    result = get_result(client, cid).json()
    assert [i["unit_price"] for i in result["items"]] == [0.1, 0.1]
    assert result["best_choice_item_ids"] == [juice_a, juice_b]


def test_decimal_avoids_floating_point_false_mismatch(client):
    # 浮點數計算 0.3 / 3 會得到 0.09999999999999999，誤判兩者不同（LAB 05 Design Note 4）
    cid = create_comparison(client)
    a = add_item_ok(client, cid, "A", 0.3, 3, "piece")
    b = add_item_ok(client, cid, "B", 0.1, 1, "piece")
    assert get_result(client, cid).json()["best_choice_item_ids"] == [a, b]


def test_ac_10_02_result_requires_at_least_two_items(client):
    cid = create_comparison(client)
    assert get_result(client, cid).json()["code"] == "INSUFFICIENT_ITEMS"  # 0 個
    add_item_ok(client, cid, "WATER_A", 45, 500, "mL")
    response = get_result(client, cid)  # 1 個
    assert response.status_code == 400
    assert response.json() == {
        "code": "INSUFFICIENT_ITEMS",
        "message": "at least 2 items are required to calculate the result (BR-04)",
    }


# ---------- FR-11：刪除比較 ----------


def test_ac_11_01_delete_comparison(client):
    cid = create_comparison(client)
    add_item_ok(client, cid, "WATER_A", 45, 500, "mL")

    response = client.delete(f"{BASE}/{cid}")
    assert response.status_code == 204
    after = client.get(f"{BASE}/{cid}")
    assert after.status_code == 404
    assert after.json() == {"code": "NOT_FOUND", "message": f"comparison {cid} not found"}
    assert client.delete(f"{BASE}/{cid}").status_code == 404


def test_unknown_path_uses_error_format(client):
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
