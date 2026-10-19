"""薄荷科学.AI 食物搜索服务端适配。"""
from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.boohee.com/open-apis/v1/food"


class BooheeFoodServiceError(RuntimeError):
    """薄荷接口错误的安全、可读描述。"""


def _extract_items(data: Any) -> list[dict[str, Any]]:
    """兼容常见的食物数组包装字段，原样保留上游字段。"""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("foods", "food_list", "foodList", "items", "results", "list", "records"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if any(key in data for key in ("food_name", "name", "food_id", "id")):
        return [data]
    return []


def _request_food_api(endpoint: str, params: dict[str, str]) -> Any:
    """通过后端访问薄荷食物接口，避免把 API Key 暴露给浏览器。"""
    api_key = os.getenv("BOOHEE_API_KEY", "").strip()
    if not api_key:
        raise BooheeFoodServiceError("尚未配置薄荷食物 API Key。请在项目 .env 中设置 BOOHEE_API_KEY。")

    url = f"{BASE_URL}/{endpoint}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "X-Api-Key": api_key})
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise BooheeFoodServiceError("薄荷接口拒绝了请求，请检查 API Key 和接口权限。") from exc
        if exc.code == 429:
            raise BooheeFoodServiceError("薄荷接口调用次数较多，请稍后再搜索。") from exc
        raise BooheeFoodServiceError("薄荷食物服务暂时无法处理请求，请稍后重试。") from exc
    except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BooheeFoodServiceError("暂时无法连接薄荷食物服务，请检查网络后重试。") from exc

    if not isinstance(payload, dict) or payload.get("code", 0) not in (0, "0", None):
        raise BooheeFoodServiceError("薄荷食物服务返回异常，请稍后重试。")
    return payload.get("data")


def search_foods(keyword: str) -> list[dict[str, Any]]:
    """通过薄荷官方食物搜索 API 查询。"""
    return _extract_items(_request_food_api("search", {"keyword": keyword}))


def get_food_detail(food_code: str) -> dict[str, Any]:
    """按薄荷食物 code 获取营养详情。"""
    data = _request_food_api("detail", {"code": food_code})
    if not isinstance(data, dict):
        raise BooheeFoodServiceError("薄荷食物详情暂不可用，请稍后重试。")
    return data
