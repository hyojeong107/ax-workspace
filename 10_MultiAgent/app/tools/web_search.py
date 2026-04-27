"""Web Search — Tavily 기반 외부 정보 검색"""

import os
from typing import Optional


def search_web(query: str, max_results: int = 3) -> str:
    """Tavily를 통해 운동/재활 관련 외부 정보를 검색합니다."""
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "TAVILY_API_KEY 미설정 — 웹 검색 불가"
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results, search_depth="basic")
        results = response.get("results", [])
        if not results:
            return "웹 검색 결과 없음"
        lines = [
            f"[웹 {i+1}] {r.get('title', '')}\n{r.get('content', '')[:400]}"
            for i, r in enumerate(results)
        ]
        return "\n\n".join(lines)
    except Exception as e:
        return f"웹 검색 오류: {str(e)}"
