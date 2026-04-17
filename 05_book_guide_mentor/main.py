import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

SYSTEM_PROMPT = """
당신은 10년 이상의 경력을 가진 독서 큐레이터 멘토입니다.
사용자가 원하는 주제의 책을 찾을 수 있도록 체계적인 설문과
깊이 있는 대화를 통해 맞춤형 도서를 추천해주는 전문가입니다.
한국 도서와 해외 도서 모두에 정통하며, 사용자의 수준과 목적에
맞는 독서 로드맵을 설계해줍니다.

---

[대화 진행 구조]

STEP 1. 초기 설문 (반드시 순서대로 하나씩 질문)
아래 항목을 한 번에 하나씩 친절하게 질문하세요.

1. 관심 주제/장르
   - "어떤 주제나 분야의 책에 관심이 있으신가요?
     (예: 심리학, 철학, 소설, 자기계발, 역사, 과학 등)"

2. 독서 수준
   - "해당 분야에 대한 본인의 지식 수준은 어느 정도인가요?
     (입문 / 중급 / 고급)"

3. 선호 형식
   - "어떤 형식의 책을 선호하시나요?
     (얇고 읽기 쉬운 책 / 두껍고 깊이 있는 책 /
      이론 중심 / 사례·실용 중심 / 에세이형)"

4. 독서 목적
   - "이 책을 읽으려는 목적이 무엇인가요?
     (취미·교양 / 업무·공부 / 자기계발 / 특정 문제 해결)"

5. 이전에 읽은 책
   - "이 분야에서 이미 읽어보신 책이 있다면 제목을 알려주세요.
     없으시면 '없음'이라고 말씀해 주세요."

---

STEP 2. 도서 추천
설문이 완료되면 search_books 함수를 사용해 각 추천 도서를 검색하세요.
검색 결과로 받은 실제 도서 정보(제목, 저자, 출판사, 소개, 링크)를 바탕으로
아래 형식으로 추천 결과를 출력하세요.

## 📚 맞춤 도서 추천

### 👤 독자 프로필 요약
- 분야 / 수준 / 목적 / 형식 선호

### 📖 추천 도서 목록
각 도서마다:
- **제목** (저자 | 출판사)
- 책 소개
- 이 책을 추천하는 이유
- 난이도 및 예상 독서 시간
- 구매 링크

### 🗺️ 독서 로드맵
추천 순서와 단계별 안내

### 💡 추가 팁

---

[주의사항]
- 설문은 반드시 하나씩 순서대로 진행하세요.
- 모든 설문이 완료된 후에만 search_books를 호출하세요.
- 검색 결과에 책이 없으면 다른 키워드로 재검색하세요.
- 한국어로 대화하세요.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_books",
            "description": "카카오 도서 검색 API로 책을 검색합니다. 추천할 도서의 실제 정보를 가져올 때 사용하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 책 제목 또는 키워드 (예: '파친코', '사피엔스', '심리학 입문')"
                    },
                    "size": {
                        "type": "integer",
                        "description": "검색 결과 수 (기본값: 3, 최대: 10)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    }
]


def search_books(query: str, size: int = 3) -> dict:
    url = "https://dapi.kakao.com/v3/search/book"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query, "size": size, "sort": "accuracy"}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        books = []
        for doc in data.get("documents", []):
            books.append({
                "title": doc.get("title", ""),
                "authors": ", ".join(doc.get("authors", [])),
                "publisher": doc.get("publisher", ""),
                "datetime": doc.get("datetime", "")[:4],
                "contents": doc.get("contents", ""),
                "url": doc.get("url", ""),
                "thumbnail": doc.get("thumbnail", ""),
                "price": doc.get("price", 0),
            })

        return {"query": query, "total": data["meta"]["total_count"], "books": books}

    except requests.exceptions.RequestException as e:
        return {"query": query, "error": str(e), "books": []}


def process_tool_calls(tool_calls) -> list:
    results = []
    for tool_call in tool_calls:
        if tool_call.function.name == "search_books":
            args = json.loads(tool_call.function.arguments)
            result = search_books(
                query=args["query"],
                size=args.get("size", 3)
            )
            print(f"  [검색중] '{args['query']}' ... {result.get('total', 0)}건 발견")
            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": "search_books",
                "content": json.dumps(result, ensure_ascii=False)
            })
    return results


def chat(messages: list) -> str:
    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
        )

        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)
            tool_results = process_tool_calls(message.tool_calls)
            messages.extend(tool_results)
            continue

        return message.content


def main():
    print("=" * 60)
    print("   📚 독서 가이드 멘토 챗봇")
    print("   (종료하려면 'exit' 또는 'quit' 입력)")
    print("=" * 60)
    print()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    intro = chat(messages + [{"role": "user", "content": "안녕하세요, 책 추천을 받고 싶어요."}])
    print(f"[멘토] {intro}\n")
    messages.append({"role": "assistant", "content": intro})

    while True:
        user_input = input("[나] ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "종료"):
            print("\n챗봇을 종료합니다. 즐거운 독서 되세요! 📖")
            break

        messages.append({"role": "user", "content": user_input})

        response = chat(messages)
        print(f"\n[멘토] {response}\n")

        messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
