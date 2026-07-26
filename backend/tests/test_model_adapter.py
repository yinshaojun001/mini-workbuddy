import httpx
import pytest

from app.errors import AppError
from app.runtime.model_adapter import raise_for_model_status


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (400, "MODEL_REQUEST_INVALID", "模型名称或请求参数不兼容"),
        (401, "MODEL_AUTH_FAILED", "模型鉴权失败"),
        (403, "MODEL_AUTH_FAILED", "模型鉴权失败"),
        (402, "MODEL_BALANCE_INSUFFICIENT", "模型账户余额不足"),
        (429, "MODEL_RATE_LIMITED", "模型请求达到限流"),
    ],
)
def test_model_statuses_are_mapped_to_actionable_public_errors(status, code, message):
    response = httpx.Response(status, request=httpx.Request("POST", "https://model.example/chat/completions"))

    with pytest.raises(AppError) as captured:
        raise_for_model_status(response)

    assert captured.value.code == code
    assert captured.value.message == message


def test_successful_model_status_is_accepted():
    raise_for_model_status(
        httpx.Response(200, request=httpx.Request("POST", "https://model.example/chat/completions"))
    )
