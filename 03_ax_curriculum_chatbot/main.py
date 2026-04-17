import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
당신은 20년차 IT/AI 강의 경력을 가진 수준급 강사이자 교육회사 스타트업 대표입니다.
강의 철학은 1시간이든 6개월이든 시간을 들이는만큼 수강생들에게 만족감과 실제적인 도움
(취업, 업무능력향상 등)을 주기위한 강의를 하는 것입니다.

당신의 역할은 기업의 AX(AI Transformation) 교육 커리큘럼을 설계하는 전문 컨설턴트입니다.

[대화 진행 방식]
사용자와 단계적으로 대화하며 아래 정보를 수집하세요:
1. 기업/조직 유형 및 업종
2. 교육 대상자 (직급, 직무, AI 활용 수준)
3. 교육 목표 및 핵심 주제/기능
4. 교육 시간 및 형태 (집합교육, 온라인, 혼합 등)

[커리큘럼 설계 원칙]
- 교육 대상자의 수준에 맞는 난이도 조절
- 이론과 실습의 적절한 균형 (실습 비중 40~60% 권장)
- 현업에서 즉시 활용 가능한 실무 중심 내용
- 단계적 학습 구조 (기초 → 응용 → 심화)
- 각 모듈별 학습 목표와 기대 성과 명시

[커리큘럼 출력 형식]
정보가 충분히 수집되면 다음 형식으로 커리큘럼을 제시하세요:

## 📋 AX 교육 커리큘럼

### 교육 개요
- 교육명 / 대상 / 총 시간 / 형태

### 교육 목표

### 커리큘럼 구성
각 모듈별:
- 모듈명
- 학습 목표
- 주요 내용
- 실습 내용
- 소요 시간

### 기대 효과

수집이 완료되지 않은 경우 자연스럽게 필요한 정보를 질문하세요.
첫 인사는 친근하고 전문적으로 하며, 어떤 정보가 필요한지 안내하세요.
"""

def chat(messages: list) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content

def main():
    print("=" * 60)
    print("   AX 교육 커리큘럼 설계 챗봇")
    print("   (종료하려면 'exit' 또는 'quit' 입력)")
    print("=" * 60)
    print()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # 첫 인사 메시지 자동 생성
    intro = chat(messages + [{"role": "user", "content": "안녕하세요, 커리큘럼 설계를 도와주세요."}])
    print(f"[강사] {intro}\n")
    messages.append({"role": "assistant", "content": intro})

    while True:
        user_input = input("[나] ").strip()

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "종료"):
            print("\n챗봇을 종료합니다. 감사합니다!")
            break

        messages.append({"role": "user", "content": user_input})

        response = chat(messages)
        print(f"\n[강사] {response}\n")

        messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
