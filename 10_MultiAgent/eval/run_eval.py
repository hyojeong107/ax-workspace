"""Run Eval — 멀티에이전트 통합 평가 스크립트"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.code_checks import run_code_checks
from eval.llm_judge import judge_faithfulness, judge_multi_agent_coherence


def load_testset(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_single_case(case: Dict, use_llm: bool = True) -> Dict[str, Any]:
    """테스트 케이스 1개를 평가합니다."""
    from app.tools.rag_search import search_rag
    from app.agents.orchestrator import run_orchestrator

    profile = case["input"]
    question = case["question"]

    # 파이프라인 실행
    result = run_orchestrator(
        user_message=question,
        user_profile={
            **profile,
            "age_group": f"{(profile['age'] // 10) * 10}대",
            "bmi_grade": _bmi_grade(profile["bmi"]),
        },
    )

    curriculum = result.get("curriculum", {})
    validation = result.get("validation_result", {})
    pipeline_log = result.get("pipeline_log", [])

    answer_text = json.dumps(curriculum, ensure_ascii=False) if curriculum else ""

    # RAG 검색 문서 (Precision@K용)
    rag_ctx = search_rag(
        age=profile["age"], gender=profile["gender"], bmi=profile["bmi"],
        age_group=profile.get("age_group", "30대"),
        bmi_grade=profile.get("bmi_grade", "정상"),
    )
    retrieved_docs = [line for line in rag_ctx.split("\n") if line.strip()]

    # ── 코드 검증 ──────────────────────────────────────────────────────────────
    code_result = run_code_checks(
        answer=answer_text,
        retrieved_docs=retrieved_docs,
        relevant_keywords=case.get("relevant_keywords", []),
        required_keywords=case.get("required_keywords", []),
        rules=case.get("rules", {}),
    )

    # ── 내부 코드 검증 결과 (validator.py 결과 포함) ────────────────────────
    code_result["internal_validation_passed"] = validation.get("is_valid", False)
    code_result["internal_errors"] = validation.get("errors", [])

    # ── LLM 판단 ──────────────────────────────────────────────────────────────
    llm_result: Dict[str, Any] = {}
    if use_llm and answer_text:
        llm_result["faithfulness"] = judge_faithfulness(answer_text, rag_ctx)

        # 멀티에이전트 일관성 평가
        specialists_called = result.get("specialists_called", {})
        if any(specialists_called.get(k) for k in ("strength", "cardio", "rehab")):
            llm_result["coherence"] = judge_multi_agent_coherence(
                specialist_outputs=specialists_called,
                final_curriculum=curriculum,
            )

    return {
        "case_id": case["id"],
        "description": case.get("description", ""),
        "pipeline_log": pipeline_log,
        "code_checks": code_result,
        "llm_judge": llm_result,
        "specialists_called": result.get("specialists_called", {}),
    }


def _bmi_grade(bmi: float) -> str:
    if bmi < 18.5: return "저체중"
    if bmi < 23: return "정상"
    if bmi < 25: return "과체중"
    if bmi < 30: return "비만"
    return "고도비만"


def aggregate_scores(results: List[Dict]) -> Dict[str, float]:
    """전체 케이스 점수 집계."""
    if not results:
        return {}

    code_keys = ["precision_at_k", "requirement_coverage", "rule_pass_rate"]
    llm_keys = ["faithfulness", "coherence"]

    agg: Dict[str, List[float]] = {k: [] for k in code_keys + llm_keys}
    internal_valid_count = 0

    for r in results:
        cc = r.get("code_checks", {})
        for k in code_keys:
            if k in cc:
                agg[k].append(float(cc[k]))

        if cc.get("internal_validation_passed"):
            internal_valid_count += 1

        lj = r.get("llm_judge", {})
        if "faithfulness" in lj:
            agg["faithfulness"].append(lj["faithfulness"].get("score", 0.0))
        if "coherence" in lj:
            agg["coherence"].append(lj["coherence"].get("score", 0.0))

    scores = {k: round(sum(v) / len(v), 4) for k, v in agg.items() if v}
    scores["internal_validation_rate"] = round(internal_valid_count / len(results), 4)
    return scores


def print_report(results: List[Dict], scores: Dict[str, float]):
    bar = lambda s: "█" * int(s * 20)
    print("\n" + "=" * 60)
    print(f"  FitStep Multi-Agent 평가 결과  ({len(results)}개 케이스)")
    print("=" * 60)
    print("\n[코드 검증 항목]")
    for k, label in [
        ("precision_at_k", "Precision@3       (검색 관련성)"),
        ("requirement_coverage", "Req Coverage  (필수 키워드 반영도)"),
        ("rule_pass_rate", "Rule Pass Rate    (처방 규칙 준수율)"),
        ("internal_validation_rate", "내부 검증 통과율 (validator.py)"),
    ]:
        v = scores.get(k, 0)
        print(f"  {label}\n    {v:.4f}  {bar(v)}")

    print("\n[LLM 판단 항목]")
    for k, label in [
        ("faithfulness", "Faithfulness  (컨텍스트 근거율)"),
        ("coherence", "Coherence     (멀티에이전트 일관성)"),
    ]:
        v = scores.get(k)
        if v is not None:
            print(f"  {label}\n    {v:.4f}  {bar(v)}")
        else:
            print(f"  {label}\n    (미측정 또는 --no-llm 옵션)")

    all_scores = [v for k, v in scores.items() if v is not None]
    overall = sum(all_scores) / len(all_scores) if all_scores else 0
    print(f"\n{'─' * 60}")
    print(f"  전체 평균: {overall:.4f}  {bar(overall)}")
    print("=" * 60 + "\n")


def save_report(results: List[Dict], scores: Dict[str, float], output_dir: str, fmt: str):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt in ("json", "both"):
        path = os.path.join(output_dir, f"eval_report_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"scores": scores, "results": results}, f, ensure_ascii=False, indent=2)
        print(f"JSON 저장: {path}")

    if fmt in ("md", "both"):
        path = os.path.join(output_dir, f"eval_report_{ts}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# FitStep Multi-Agent 평가 리포트\n\n생성: {ts}\n\n")
            f.write("## 집계 점수\n\n| 항목 | 점수 |\n|---|---|\n")
            for k, v in scores.items():
                f.write(f"| {k} | {v:.4f} |\n")
            f.write("\n## 케이스별 결과\n\n")
            for r in results:
                f.write(f"### {r['case_id']} — {r['description']}\n\n")
                f.write(f"**파이프라인 로그**\n")
                for log in r.get("pipeline_log", []):
                    f.write(f"- {log}\n")
                cc = r.get("code_checks", {})
                f.write(f"\n**코드 검증**: 내부 검증={'✅' if cc.get('internal_validation_passed') else '❌'}, "
                        f"규칙 통과율={cc.get('rule_pass_rate', 0):.2f}\n\n")
        print(f"Markdown 저장: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FitStep Multi-Agent 평가")
    parser.add_argument("--testset", default="eval/testset.json")
    parser.add_argument("--output", choices=["json", "md", "both"], default="both")
    parser.add_argument("--output-dir", default="eval/reports")
    parser.add_argument("--no-llm", action="store_true", help="LLM 판단 항목 스킵")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv()

    testset = load_testset(args.testset)
    print(f"테스트 케이스 {len(testset)}개 로드 완료")

    results = []
    for i, case in enumerate(testset):
        print(f"[{i+1}/{len(testset)}] {case['id']} 평가 중...")
        try:
            result = run_single_case(case, use_llm=not args.no_llm)
        except Exception as e:
            result = {"case_id": case["id"], "description": case.get("description", ""), "error": str(e), "code_checks": {}, "llm_judge": {}}
        results.append(result)

    scores = aggregate_scores(results)
    print_report(results, scores)
    save_report(results, scores, args.output_dir, args.output)
