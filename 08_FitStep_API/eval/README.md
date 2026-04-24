# Phase 4 — RAG 평가 파이프라인

RAGAS 없이 **순수 Python + OpenAI 1회 호출**로 구현한 FitStep RAG 품질 평가 모듈입니다.

## 파일 구조

```
eval/
├── __init__.py
├── precision.py              # Retrieval 평가 (Precision@K)
├── faithfulness.py           # Faithfulness 평가 (LLM Judge)
├── requirement_coverage.py   # Requirement Coverage 평가
├── rule_check.py             # Rule 기반 평가
├── run_eval.py               # 통합 실행 스크립트
├── testset.json              # 테스트셋 (10개 케이스)
├── README.md
└── reports/                  # 리포트 저장 (자동 생성)
    ├── eval_report_YYYYMMDD_HHMMSS.json
    └── eval_report_YYYYMMDD_HHMMSS.md
```

## 평가 지표

| 지표 | 파일 | 설명 | LLM 호출 |
|------|------|------|----------|
| **Precision@K** | `precision.py` | 상위 K개 검색 청크 중 관련 키워드 포함 비율 | 없음 |
| **Faithfulness** | `faithfulness.py` | 답변이 검색 컨텍스트에 근거하는지 (hallucination 측정) | 케이스당 1회 |
| **Requirement Coverage** | `requirement_coverage.py` | `required_keywords`가 답변에 반영된 비율 | 없음 |
| **Rule Check** | `rule_check.py` | 세션 수·운동 시간·그룹 구성·강도 언급 여부 | 없음 |

> Faithfulness만 LLM을 사용합니다. `--no-faith` 옵션으로 스킵할 수 있습니다.

## 실행 방법

```bash
# 08_FitStep_API 디렉토리에서 실행
cd 08_FitStep_API

# 기본 실행 (JSON + Markdown 리포트 모두 생성)
python -m eval.run_eval

# 커스텀 테스트셋 지정
python -m eval.run_eval --testset eval/testset.json

# 리포트 형식 선택
python -m eval.run_eval --output json
python -m eval.run_eval --output md

# Faithfulness 스킵 (토큰 절약 — LLM 호출 0회)
python -m eval.run_eval --no-faith
```

> **전제 조건**
> - `.env`에 `OPENAI_API_KEY` 설정
> - `python init_public_data.py`로 ChromaDB 공공데이터 인덱싱 완료

## testset.json 형식

```json
[
  {
    "id": "tc_001",
    "description": "케이스 설명",
    "input": {
      "age": 35,
      "gender": "F",
      "bmi": 25.0,
      "age_group": "30대",
      "bmi_grade": "과체중"
    },
    "question": "질문 텍스트",
    "ground_truth": "기대 정답",
    "relevant_keywords": ["Precision@K 평가용 키워드"],
    "required_keywords": ["Coverage 평가용 필수 키워드"],
    "rules": {
      "expect_session_count": true,
      "expect_duration": true,
      "expect_group_variety": true,
      "expect_intensity": true
    }
  }
]
```

### 필드 설명

| 필드 | 설명 |
|------|------|
| `input.age_group` | 연령대 문자열 (예: `"30대"`, `"60대"`) |
| `input.bmi_grade` | BMI 등급 — ChromaDB 인덱싱값과 일치해야 함 |
| `relevant_keywords` | Precision@K 평가 기준 키워드 (ground_truth에서 자동 추출 가능) |
| `required_keywords` | 답변에 반드시 포함돼야 하는 핵심 키워드 |
| `rules.expect_*` | 해당 규칙 검사 여부 (리포트 참고용, 점수에는 미반영) |

### bmi_grade 값 기준

| BMI | bmi_grade |
|-----|-----------|
| < 18.5 | 저체중 |
| 18.5 ~ 22.9 | 정상 |
| 23 ~ 24.9 | 과체중 |
| 25 ~ 29.9 | 비만 |
| ≥ 30 | 고도비만 |

## Rule Check 규칙 상세

`rule_check.py`는 아래 4가지를 정규식·키워드로 검사합니다.

| 규칙 | 검사 내용 | 예시 |
|------|----------|------|
| `session_count` | 주당 운동 횟수 언급 | "주 3회", "매일" |
| `duration` | 운동 시간 언급 | "30분", "1시간" |
| `group_variety` | 유산소·근력·스트레칭 중 2그룹 이상 | "유산소 + 스쿼트" |
| `intensity` | 운동 강도 언급 | "저강도", "중등도" |

## 출력 예시

```
==============================================================
  FitStep RAG 평가 결과  (10개 케이스)
==============================================================
  Precision@3          (검색 청크 관련성)
    0.7333  ██████████████
  Faithfulness         (컨텍스트 근거율)
    0.8600  █████████████████
  Requirement Coverage (요구사항 반영도)
    0.9000  ██████████████████
  Rule Check           (처방 규칙 준수율)
    0.8250  ████████████████
--------------------------------------------------------------
  전체 평균: 0.8296
==============================================================
```
