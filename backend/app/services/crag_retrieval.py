"""检索后相关性评估；本地证据不足时用 Tavily 补充网页来源。"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .exercise_knowledge import retrieve_documents, tokenize

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_RELEVANCE_THRESHOLD = 0.30
_TRUSTED_DOMAINS = (
    "acsm.org", "acefitness.org", "nsca.com", "exrx.net", "pubmed.ncbi.nlm.nih.gov",
    "who.int", "cdc.gov", "nhs.uk", "mayoclinic.org", "health.gov", "sport.gov.cn",
    "chinacdc.cn", "gov.cn",
)
_STOP_WORDS = {
    "这个", "那个", "一下", "如何", "怎么", "怎样", "可以", "应该", "需要", "是否",
    "训练", "动作", "健身", "进行", "自己", "时候", "问题", "建议", "一下", "请问",
}


def _grade_local_documents(question: str, documents: list[dict]) -> float:
    """使用问题词项在候选资料中的覆盖率，判断本地证据是否值得直接回答。"""
    query_terms = {term for term in tokenize(question) if len(term) > 1 and term not in _STOP_WORDS}
    if not query_terms:
        query_terms = {term for term in tokenize(question) if term not in _STOP_WORDS}
    if not query_terms or not documents:
        return 0.0

    best_score = 0.0
    for document in documents[:5]:
        document_terms = set(tokenize(" ".join((document.get("title", ""), document.get("body", "")))))
        score = len(query_terms & document_terms) / len(query_terms)
        best_score = max(best_score, score)
    return round(best_score, 3)


def _tavily_search(question: str, top_k: int = 4) -> list[dict]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("missing_api_key")

    # 仅发送用户本轮问题；不把账号资料、训练记录或 ReAct 工具上下文拼进搜索词。
    payload = json.dumps({
        "api_key": api_key,
        "query": question[:500],
        "search_depth": "basic",
        "topic": "general",
        "max_results": max(1, min(top_k, 5)),
        "include_domains": list(_TRUSTED_DOMAINS),
        "include_answer": False,
        "include_raw_content": False,
    }).encode("utf-8")
    request = Request(_TAVILY_SEARCH_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "fitness-coach-agent/1.0",
    }, method="POST")
    with urlopen(request, timeout=8) as response:
        result = json.loads(response.read(1_000_000).decode("utf-8"))

    retrieved_at = datetime.now(timezone.utc).isoformat()
    documents = []
    for item in result.get("results", []):
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        body = str(item.get("content") or "").strip()
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not body:
            continue
        hostname = parsed.hostname.lower().rstrip(".") if parsed.hostname else ""
        if not any(hostname == domain or hostname.endswith("." + domain) for domain in _TRUSTED_DOMAINS):
            continue
        score = float(item.get("score") or 0.0)
        if score < 0.25:
            continue
        title = str(item.get("title") or parsed.netloc).strip()[:300]
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        documents.append({
            "document_key": f"tavily:{key}",
            "source_type": "web",
            "exercise_id": None,
            "title": title,
            "body": body[:3000],
            "source_name": f"Tavily · {parsed.netloc}",
            "source_url": url,
            "source_published_at": None,
            "source_retrieved_at": retrieved_at,
            "target_muscles": [],
            "equipment": [],
            "tags": ["web_search"],
            "bm25_score": None,
            "vector_score": None,
            "retrieval_channels": ["tavily"],
            "tavily_score": round(score, 4),
        })
    return documents


def retrieve_with_crag(question: str, rows: list, *, allow_semantic: bool = False,
                       allow_web_search: bool = False, consent_given: bool = False, top_k: int = 8):
    """先执行现有 BM25/向量混合检索，再按相关性触发 Tavily 回退。"""
    local_documents, retrieval_note = retrieve_documents(
        question, rows, allow_semantic=allow_semantic, top_k=top_k)
    relevance = _grade_local_documents(question, local_documents)
    details = {"status": "local_sufficient", "local_relevance": relevance, "tavily_used": False}
    if relevance >= _RELEVANCE_THRESHOLD:
        return local_documents, retrieval_note, details

    if not allow_web_search:
        details["status"] = "local_only" if consent_given else "consent_required"
        note = ("本地检索相关性偏低；本次查询仅使用本地候选资料。" if consent_given
                else "本地检索相关性偏低；未授权联网搜索，本次仅使用本地候选资料。")
        return local_documents, "；".join(value for value in (retrieval_note, note) if value), details

    if not os.getenv("TAVILY_API_KEY", "").strip():
        details["status"] = "missing_api_key"
        note = "本地检索相关性偏低；请在 .env 配置 TAVILY_API_KEY 后重启后端，启用 Tavily 联网补充。"
        return local_documents, "；".join(value for value in (retrieval_note, note) if value), details

    try:
        web_documents = _tavily_search(question, top_k=min(top_k, 4))
    except HTTPError as error:
        details["status"] = "tavily_unavailable"
        note = f"本地检索相关性偏低；Tavily 请求失败（HTTP {error.code}），已回退到本地资料。"
        return local_documents, "；".join(value for value in (retrieval_note, note) if value), details
    except (URLError, TimeoutError, OSError, ValueError, RuntimeError):
        details["status"] = "tavily_unavailable"
        note = "本地检索相关性偏低；Tavily 暂不可用，已回退到本地资料。"
        return local_documents, "；".join(value for value in (retrieval_note, note) if value), details

    if not web_documents:
        details["status"] = "no_web_results"
        note = "本地检索相关性偏低；Tavily 没有返回可用来源，已保留本地候选资料。"
        return local_documents, "；".join(value for value in (retrieval_note, note) if value), details

    details.update({"status": "tavily_used", "tavily_used": True,
                    "web_result_count": len(web_documents)})
    return local_documents + web_documents, retrieval_note, details
