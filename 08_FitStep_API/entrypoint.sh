#!/bin/sh
set -e

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
    print(f"[init] fitness_measurement: {fitness_count}개, exercise_recommendation: {exercise_count}개")
    needs_index = fitness_count == 0 or exercise_count == 0
except Exception as e:
    print(f"[init] ChromaDB 확인 실패: {e}")
    needs_index = True

if needs_index:
    print("[init] 공공데이터 인덱싱 시작...")
    from init_public_data import index_fitness_data, index_exercise_recommendation
    index_fitness_data()
    index_exercise_recommendation()
    print("[init] 인덱싱 완료.")
else:
    print("[init] 데이터 이미 존재 — 인덱싱 스킵.")
EOF

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
