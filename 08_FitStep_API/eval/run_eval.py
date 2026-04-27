"""Phase 4 — RAG 평가 파이프라인 통합 실행 스크립트

평가 지표:
  1. Precision@K       - 검색 청크 중 관련 키워드 포함 비율 (LLM 없음)
  2. Faithfulness      - 답변이 컨텍스트에 근거하는지 (gpt-4o-mini Judge 1회)
  3. Req. Coverage     - required_keywords 커버율 (LLM 없음)
  4. Rule Check        - 운동 처방 규칙 준수율 (LLM 없음)

실행:
    cd 08_FitStep_API
    python -m eval.run_eval
    python -m eval.run_eval --testset eval/testset.json
    python -m eval.run_eval --output json
    python -m eval.run_eval --output md
    python -m eval.run_eval --output all   (기본값)
    python -m eval.run_eval --no-faith     (Faithfulness 스킵 — 토큰 절약)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openai import OpenAI

from app.retrieval import retrieve_fitness_context, retrieve_exercise_recommendation
from eval.precision import precision_at_k, extract_keywords
from eval.faithfulness import evaluate_faithfulness
from eval.requirement_coverage import evaluate_requirement_coverage, get_coverage_detail
from eval.rule_check import check_rules

TESTSET_DEFAULT = Path(__file__).parent / "testset.json"
REPORT_DIR = Path(__file__).parent / "reports"

SYSTEM_PROMPT = (
    "당신은 개인 맞춤형 운동 처방 전문가입니다. "
    "아래 컨텍스트를 최대한 활용하여 답변하세요. "
    "컨텍스트에 구체적인 운동명, 횟수, 시간, 강도가 있다면 반드시 그대로 활용하세요. "
    "컨텍스트에 없는 내용은 사용자 프로필(나이, 성별, BMI)에 맞는 일반적인 운동 원칙으로 보완하세요.\n\n"
    "## 참고 컨텍스트\n\n"
)


def _retrieve_contexts(item: dict) -> list[str]:
    inp = item["input"]
    parts: list[str] = []

    fitness_ctx = retrieve_fitness_context(
        age=inp["age"],
        gender=inp["gender"],
        bmi=inp["bmi"],
    )
    if fitness_ctx:
        parts.extend([c for c in fitness_ctx.split("\n") if c.strip()])

    exercise_ctx = retrieve_exercise_recommendation(
        age_group=inp["age_group"],
        gender=inp["gender"],
        bmi_grade=inp["bmi_grade"],
    )
    if exercise_ctx:
        parts.extend([c for c in exercise_ctx.split("\n") if c.strip()])

    return parts


def _generate_answer(client: OpenAI, question: str, contexts: list[str]) -> str:
    context_text = "\n".join(contexts) if contexts else "관련 데이터 없음"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + context_text},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def _evaluate_case(item: dict, client: OpenAI, run_faith: bool) -> dict:
    question = item["question"]
    ground_truth = item["ground_truth"]
    relevant_keywords = item.get("relevant_keywords", extract_keywords(ground_truth))
    required_keywords = item.get("required_keywords", [])

    contexts = _retrieve_contexts(item)
    answer = _generate_answer(client, question, contexts)

    precision = precision_at_k(contexts, relevant_keywords, k=3)
    faith = evaluate_faithfulness(answer, contexts, client) if run_faith else None
    coverage = evaluate_requirement_coverage(answer, required_keywords)
    coverage_detail = get_coverage_detail(answer, required_keywords)
    rules = check_rules(
        answer,
        age_group=item["input"].get("age_group", ""),
        bmi_grade=item["input"].get("bmi_grade", ""),
        personalization_keywords=required_keywords or None,
    )

    return {
        "id": item["id"],
        "description": item.get("description", ""),
        "question": question,
        "answer": answer,
        "ground_truth": ground_truth,
        "contexts": contexts,
        "scores": {
            "precision_at_3": round(precision, 4),
            "faithfulness": round(faith, 4) if faith is not None else "skipped",
            "requirement_coverage": round(coverage, 4),
            "rule_score": round(rules["score"], 4),
        },
        "coverage_detail": coverage_detail,
        "rule_detail": {k: v for k, v in rules.items() if k not in ("score", "matched_groups")},
        "matched_groups": rules.get("matched_groups", []),
    }


def _aggregate(results: list[dict]) -> dict:
    keys = ["precision_at_3", "requirement_coverage", "rule_score"]
    sums = {k: 0.0 for k in keys}
    faith_scores = [r["scores"]["faithfulness"] for r in results if r["scores"]["faithfulness"] != "skipped"]

    for r in results:
        for k in keys:
            sums[k] += r["scores"][k]

    n = len(results)
    summary = {k: round(sums[k] / n, 4) for k in keys}
    if faith_scores:
        summary["faithfulness"] = round(sum(faith_scores) / len(faith_scores), 4)
    else:
        summary["faithfulness"] = "skipped"

    scored = [v for v in summary.values() if isinstance(v, float)]
    summary["overall"] = round(sum(scored) / len(scored), 4) if scored else 0.0
    return summary


def _print_summary(summary: dict, n: int) -> None:
    labels = {
        "precision_at_3":        "Precision@3          (검색 청크 관련성)",
        "faithfulness":          "Faithfulness         (컨텍스트 근거율)",
        "requirement_coverage":  "Requirement Coverage (요구사항 반영도)",
        "rule_score":            "Rule Check           (처방 규칙 준수율)",
    }
    print(f"\n{'='*62}")
    print(f"  FitStep RAG 평가 결과  ({n}개 케이스)")
    print(f"{'='*62}")
    for key, label in labels.items():
        val = summary.get(key, 0)
        if val == "skipped":
            print(f"  {label}\n    skipped")
            continue
        bar = "█" * int(val * 20)
        print(f"  {label}\n    {val:.4f}  {bar}")
    print(f"{'-'*62}")
    print(f"  전체 평균: {summary['overall']:.4f}")
    print(f"{'='*62}\n")


def _save_json(summary: dict, results: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "cases": results,
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON 리포트: {path}")


def _save_markdown(summary: dict, results: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# FitStep RAG 평가 리포트",
        "",
        f"> 생성 일시: {now}  |  평가 케이스: {len(results)}개",
        "",
        "## 요약 점수",
        "",
        "| 지표 | 점수 |",
        "|------|------|",
        f"| Precision@3 | {summary['precision_at_3']} |",
        f"| Faithfulness | {summary['faithfulness']} |",
        f"| Requirement Coverage | {summary['requirement_coverage']} |",
        f"| Rule Check | {summary['rule_score']} |",
        f"| **전체 평균** | **{summary['overall']}** |",
        "",
        "## 지표 설명",
        "",
        "| 지표 | 설명 | 측정 방식 |",
        "|------|------|-----------|",
        "| Precision@3 | 상위 3개 검색 청크 중 관련 키워드 포함 비율 | 키워드 매칭 |",
        "| Faithfulness | 답변이 검색 컨텍스트에 근거하는지 | LLM Judge |",
        "| Requirement Coverage | required_keywords가 답변에 반영된 비율 | 키워드 매칭 |",
        "| Rule Check | 세션 수·운동 시간·그룹 구성·강도 언급 여부 | 규칙 파싱 |",
        "",
        "## 케이스별 상세 결과",
        "",
    ]

    for r in results:
        s = r["scores"]
        lines += [
            f"### {r['id']} — {r['description']}",
            "",
            f"**Q.** {r['question']}",
            "",
            f"**생성 답변**",
            "",
            r["answer"],
            "",
            f"**정답 (Ground Truth)**",
            "",
            r["ground_truth"],
            "",
            "**점수**",
            "",
            "| 지표 | 점수 |",
            "|------|------|",
            f"| Precision@3 | {s['precision_at_3']} |",
            f"| Faithfulness | {s['faithfulness']} |",
            f"| Requirement Coverage | {s['requirement_coverage']} |",
            f"| Rule Check | {s['rule_score']} |",
            "",
            f"**요구사항 커버**: {r['coverage_detail']}",
            "",
            f"**규칙 상세**: {r['rule_detail']}",
            "",
            f"**검색 컨텍스트** ({len(r['contexts'])}개)",
            "",
        ]
        for i, ctx in enumerate(r["contexts"], 1):
            lines.append(f"{i}. {ctx}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Markdown 리포트: {path}")


def main(testset_path: Path, output: str, run_faith: bool) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")

    print(f"테스트셋 로드: {testset_path}")
    items = json.loads(testset_path.read_text(encoding="utf-8"))
    print(f"총 {len(items)}개 케이스\n")

    client = OpenAI(api_key=api_key)
    results = []

    for idx, item in enumerate(items, 1):
        print(f"[{idx}/{len(items)}] {item['id']} - {item.get('description', '')}")
        result = _evaluate_case(item, client, run_faith)
        s = result["scores"]
        faith_str = f"{s['faithfulness']:.4f}" if isinstance(s["faithfulness"], float) else "skipped"
        print(f"  Precision@3={s['precision_at_3']:.4f}  Faith={faith_str}"
              f"  Coverage={s['requirement_coverage']:.4f}  Rule={s['rule_score']:.4f}")
        results.append(result)

    summary = _aggregate(results)
    _print_summary(summary, len(results))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output in ("json", "all"):
        _save_json(summary, results, REPORT_DIR / f"eval_report_{timestamp}.json")
    if output in ("md", "all"):
        _save_markdown(summary, results, REPORT_DIR / f"eval_report_{timestamp}.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitStep RAG 평가 파이프라인")
    parser.add_argument("--testset", type=Path, default=TESTSET_DEFAULT, help="테스트셋 JSON 경로")
    parser.add_argument("--output", choices=["json", "md", "all"], default="all", help="리포트 출력 형식")
    parser.add_argument("--no-faith", action="store_true", help="Faithfulness 평가 스킵 (토큰 절약)")
    args = parser.parse_args()
    main(testset_path=args.testset, output=args.output, run_faith=not args.no_faith)
