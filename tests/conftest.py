import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# 測試專用的假金鑰，只存在測試程式中，不是真正的秘密
EDITOR = {"X-API-Key": "test-editor-key"}
VIEWER = {"X-API-Key": "test-viewer-key"}


@pytest.fixture(autouse=True)
def users(monkeypatch):
    # 以 monkeypatch 注入測試使用者：alice 是 editor、bob 是 viewer（LAB 07）
    monkeypatch.setenv(
        "W09_USERS_JSON",
        json.dumps({
            "alice": {"key": EDITOR["X-API-Key"], "role": "editor"},
            "bob": {"key": VIEWER["X-API-Key"], "role": "viewer"},
        }),
    )


@pytest.fixture
def database():
    # 每個測試使用全新的記憶體資料庫：不會動到 unitprice.db，測試之間也互不影響
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(database):
    """以 editor（alice）身分送出所有請求；LAB 06 的功能測試沿用這個 client。"""
    with TestClient(app, headers=EDITOR) as test_client:
        yield test_client


@pytest.fixture
def anonymous(database):
    """不帶任何金鑰的 client；LAB 07 測試再依情境自行加上 Header。與 client 共用同一個資料庫。"""
    with TestClient(app) as test_client:
        yield test_client
