"""W09（LAB 07）：以每位使用者不同的 API Key 辨識身分，再判斷能不能寫入資料。

Authentication（你是誰）：identify_user 由 X-API-Key 查出使用者。
Authorization（你能做什麼）：require_editor 只讓 editor 通過。
這是課堂用的輕量方案，不是帳號密碼登入，也沒有實作「每筆資料的擁有者」。
"""

import json  # 把 W09_USERS_JSON 這段 JSON 字串轉回 Python dict
import os  # 從伺服器環境變數讀取設定，不把秘密寫在程式碼裡
import secrets  # compare_digest：比較金鑰時不因內容不同而洩漏時間差
from dataclasses import dataclass

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

USERS_ENV = "W09_USERS_JSON"
ROLES = ("editor", "viewer")

# 從 HTTP Header 讀取 X-API-Key；auto_error=False，缺少時由 identify_user 自己回 401
api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",  # 與 openapi.yaml 的 securitySchemes 名稱相同
    auto_error=False,
)


@dataclass(frozen=True)
class CurrentUser:
    """驗證成功後的使用者；role 由伺服器設定決定，不是 Client 自己宣稱的。"""

    username: str
    role: str  # editor（可寫入）或 viewer（只能查詢）


def load_users() -> dict:
    """讀取並檢查伺服器的「使用者 → 金鑰、角色」對照表；設定有問題時回 503，不默默放行。"""
    raw = os.getenv(USERS_ENV)
    if not raw:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "server user configuration missing")
    try:
        users = json.loads(raw)
        if not isinstance(users, dict) or not users:
            raise ValueError("user table must be a non-empty JSON object")
        keys = []
        for name, info in users.items():
            if not name or not isinstance(info, dict):
                raise ValueError("invalid user record")
            if not isinstance(info.get("key"), str) or not info["key"]:
                raise ValueError("invalid API key")
            if info.get("role") not in ROLES:
                raise ValueError("unknown role")
            keys.append(info["key"])
        if len(keys) != len(set(keys)):  # 兩個使用者不可共用同一把金鑰
            raise ValueError("duplicate API keys")
        return users
    except (ValueError, TypeError):  # json.JSONDecodeError 是 ValueError 的子類別
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "invalid server user configuration")


def identify_user(api_key: str | None = Security(api_key_header)) -> CurrentUser:
    """Authentication：由金鑰查出使用者。"""
    users = load_users()  # 先確認伺服器設定正常，避免把設定錯誤誤判成使用者打錯 Key
    if not api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-API-Key is required")
    for username, info in users.items():
        if secrets.compare_digest(api_key, info["key"]):
            return CurrentUser(username=username, role=info["role"])
    raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid API key")


def require_editor(user: CurrentUser = Security(identify_user)) -> CurrentUser:
    """Authorization：只有 editor 能新增、修改、刪除；viewer 的金鑰雖然正確，仍回 403。"""
    if user.role != "editor":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "editor role is required")
    return user
