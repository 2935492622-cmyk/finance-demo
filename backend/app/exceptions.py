"""Safe, stable API errors; raw inputs and SQL errors never reach clients."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []
        super().__init__(message)


class DatabaseUnavailable(APIError):
    def __init__(self):
        super().__init__(503, "DATABASE_UNAVAILABLE", "数据库暂不可用，请检查本地数据库配置或稍后重试")


def error_response(error: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        content={"error": {"code": error.code, "message": error.message, "details": error.details}},
    )


def validation_details(errors, prefix: str | None = None) -> list[dict[str, str]]:
    details = []
    messages = {
        "amount": "金额必须是大于 0、最多八位整数及固定两位小数的字符串",
        "type": "类型仅允许 income 或 expense",
        "category": "分类须为去除首尾空白后 1～50 字符的文本",
        "note": "备注须为最多 500 字符的文本",
        "transaction_date": "记账日期必须是 1000～9999 年的有效 YYYY-MM-DD 日期",
        "start_date": "起始日期必须是 1000～9999 年的有效 YYYY-MM-DD 日期",
        "end_date": "结束日期必须是 1000～9999 年的有效 YYYY-MM-DD 日期",
        "id": "ID 必须为有效范围内的正整数",
    }
    for error in errors:
        location = list(error.get("loc", ()))
        if prefix:
            location.insert(0, prefix)
        if error.get("type") == "json_invalid":
            location = ["body"]
        field = ".".join(str(item) for item in location) or "body"
        if error.get("type") == "extra_forbidden":
            message = "不支持的字段或查询参数"
        else:
            message = messages.get(str(location[-1]) if location else "", "字段缺失或格式不合法")
        details.append({"field": field, "message": message})
    return details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error_handler(_request: Request, exc: APIError):
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        return error_response(APIError(422, "VALIDATION_ERROR", "请求参数不合法", validation_details(exc.errors())))

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(_request: Request, _exc: SQLAlchemyError):
        return error_response(DatabaseUnavailable())

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, _exc: Exception):
        return error_response(APIError(500, "INTERNAL_ERROR", "服务内部错误，请稍后重试"))
