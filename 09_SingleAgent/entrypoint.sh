#!/bin/sh
set -e

# 공공데이터가 마운트된 경우 인덱싱 (08_FitStep_API 데이터 재사용)
python - <<'EOF'
import sys
sys.path.insert(0, '/app')

from dotenv import load_dotenv
load_dotenv()

from app.indexing import _get_fitness_store, _get_exercise_store

try:
    fs = _get_fitness_store()
    es = _get_exercise_store()
    fitness_count = len(fs.get()["ids"])
    exercise_count = len(es.get()["ids"])
    print(f"[init] fitness: {fitness_count}개, exercise: {exercise_count}개")
    needs_index = fitness_count == 0 or exercise_count == 0
except Exception as e:
    print(f"[init] ChromaDB 확인 실패: {e}")
    needs_index = False  # 공공데이터 없이도 에이전트는 동작

if needs_index:
    print("[init] ChromaDB 데이터 없음 — 웹 검색으로 대체됩니다.")
else:
    print("[init] ChromaDB 준비 완료.")
EOF

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
