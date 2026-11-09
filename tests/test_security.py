"""LAB 07 驗收：每個測試對應 docs/01_requirements.md 的安全需求 SEC-01～SEC-06。"""

import json

import pytest

from tests.conftest import EDITOR, VIEWER

BASE = "/api/v1/comparisons"
WATER_A = {"name": "WATER_A", "price": 45, "quantity": 500, "unit": "mL"}
WATER_B = {"name": "WATER_B", "price": 80, "quantity": 1, "unit": "L"}


def setup_comparison(client) -> tuple[int, int]:
    """以 editor 建立一個含 WATER_A、WATER_B 的比較，回傳 (comparison_id, WATER_A 的 item_id)。"""
    cid = client.post(BASE, json={"name": "超商瓶裝水"}).json()["id"]
    item_id = client.post(f"{BASE}/{cid}/items", json=WATER_A).json()["id"]
    client.post(f"{BASE}/{cid}/items", json=WATER_B)
    return cid, item_id


# ---------- SEC-04：缺少或錯誤的憑證 ----------


def test_sec_04_missing_key_returns_401(anonymous):
    response = anonymous.post(BASE, json={"name": "A"})
    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHENTICATED", "message": "X-API-Key is required"}


def test_sec_04_unknown_key_returns_403(anonymous):
    response = anonymous.post(BASE, json={"name": "A"}, headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    assert response.json() == {"code": "FORBIDDEN", "message": "invalid API key"}


def test_sec_04_get_endpoints_stay_public(client, anonymous):
    cid, _ = setup_comparison(client)
    assert anonymous.get(f"{BASE}/{cid}").status_code == 200
    result = anonymous.get(f"{BASE}/{cid}/result")
    assert result.status_code == 200
    assert result.json()["best_choice_item_ids"] != []


# ---------- SEC-01、SEC-02：辨識使用者，只有 editor 能新增 ----------


def test_sec_02_editor_can_create(anonymous):
    created = anonymous.post(BASE, json={"name": "A"}, headers=EDITOR)
    assert created.status_code == 201
    cid = created.json()["id"]
    item = anonymous.post(f"{BASE}/{cid}/items", json=WATER_A, headers=EDITOR)
    assert item.status_code == 201


def test_sec_02_viewer_cannot_create(client, anonymous):
    response = anonymous.post(BASE, json={"name": "A"}, headers=VIEWER)
    assert response.status_code == 403
    assert response.json() == {"code": "FORBIDDEN", "message": "editor role is required"}

    cid, _ = setup_comparison(client)
    item = anonymous.post(f"{BASE}/{cid}/items", json=WATER_A, headers=VIEWER)
    assert item.status_code == 403
    # viewer 被拒絕後，資料不應增加
    assert len(anonymous.get(f"{BASE}/{cid}").json()["items"]) == 2


def test_sec_01_role_comes_from_server_not_request_body(anonymous):
    # viewer 在 Body 自稱 editor 也沒有用：角色只由伺服器依金鑰決定
    response = anonymous.post(BASE, json={"name": "A", "role": "editor"}, headers=VIEWER)
    assert response.status_code == 403


# ---------- SEC-03：只有 editor 能修改、刪除 ----------


def test_sec_03_viewer_cannot_modify_or_delete(client, anonymous):
    cid, item_id = setup_comparison(client)

    assert anonymous.patch(f"{BASE}/{cid}/items/{item_id}", json={"price": 1}, headers=VIEWER).status_code == 403
    assert anonymous.delete(f"{BASE}/{cid}/items/{item_id}", headers=VIEWER).status_code == 403
    assert anonymous.delete(f"{BASE}/{cid}", headers=VIEWER).status_code == 403
    assert anonymous.delete(f"{BASE}/{cid}").status_code == 401

    # 資料完全沒有被改動
    items = anonymous.get(f"{BASE}/{cid}").json()["items"]
    assert [(i["id"], i["price"]) for i in items][0] == (item_id, 45)
    assert len(items) == 2


def test_sec_03_editor_can_modify_and_delete(client):
    cid, item_id = setup_comparison(client)
    assert client.patch(f"{BASE}/{cid}/items/{item_id}", json={"price": 40}).status_code == 200
    assert client.delete(f"{BASE}/{cid}/items/{item_id}").status_code == 204
    assert client.delete(f"{BASE}/{cid}").status_code == 204


# ---------- SEC-05：使用者設定由伺服器管理 ----------


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "{}",
        json.dumps({"a": {"key": "same", "role": "editor"}, "b": {"key": "same", "role": "viewer"}}),
        json.dumps({"a": {"key": "k", "role": "admin"}}),
    ],
)
def test_sec_05_invalid_server_configuration_returns_503(anonymous, monkeypatch, raw):
    monkeypatch.setenv("W09_USERS_JSON", raw)
    response = anonymous.post(BASE, json={"name": "A"}, headers={"X-API-Key": "same"})
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"


def test_sec_05_missing_server_configuration_returns_503(anonymous, monkeypatch):
    monkeypatch.delenv("W09_USERS_JSON", raising=False)
    response = anonymous.post(BASE, json={"name": "A"}, headers=EDITOR)
    assert response.status_code == 503
    # 設定錯誤只影響寫入；公開的 GET 不讀使用者設定
    assert anonymous.get(f"{BASE}/1").status_code == 404


# ---------- SEC-06：安全升級不破壞原有功能 ----------


def test_sec_06_editor_invalid_data_still_returns_400(client):
    # 老師驗收表的「欄位不合法 → 422」，在本服務的 Contract 中為 400 INVALID_REQUEST
    cid, _ = setup_comparison(client)
    response = client.post(f"{BASE}/{cid}/items", json={**WATER_A, "price": 0})
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_REQUEST"


def test_sec_06_result_unchanged_after_security_upgrade(client, anonymous):
    cid, _ = setup_comparison(client)
    result = anonymous.get(f"{BASE}/{cid}/result").json()
    assert [i["unit_price"] for i in result["items"]] == [0.09, 0.08]
