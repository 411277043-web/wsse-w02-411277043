# 業務錯誤（Domain Errors）：Service 只拋出這些例外，不知道 HTTP Status Code；
# app/main.py 的 Exception Handler 再統一轉成 LAB 04 的 ErrorResponse（LAB 05 Design Note 5）。


class DomainError(Exception):
    code = "INVALID_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "NOT_FOUND"


class MeasurementTypeMismatchError(DomainError):
    """BR-06：新商品的 Measurement Type 與同一比較中的其他商品不同。"""

    code = "MEASUREMENT_TYPE_MISMATCH"


class InsufficientItemsError(DomainError):
    """BR-04：商品少於 2 個，無法產生比較結果。"""

    code = "INSUFFICIENT_ITEMS"
