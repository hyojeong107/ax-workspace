# 헬스장 기구 데이터를 벡터 DB에 초기 적재하는 스크립트
# 사용법: python3 seed_gym.py

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from rag.gym_rag import save_gym_to_vector_db

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def seed():
    json_files = [f for f in os.listdir(DATA_DIR) if f.startswith("gym_") and f.endswith(".json")]
    if not json_files:
        print("data/ 폴더에 gym_*.json 파일이 없습니다.")
        return

    for fname in json_files:
        path = os.path.join(DATA_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            gym_data = json.load(f)

        user_id = gym_data["user_id"]
        gym_name = gym_data["gym_name"]
        eq_count = len(gym_data["equipment"])

        print(f"[{fname}] '{gym_name}' (user_id={user_id}, 기구 {eq_count}개) 임베딩 중...")
        save_gym_to_vector_db(user_id, gym_data)
        print(f"  ✓ 완료")

    print("\n모든 헬스장 데이터가 벡터 DB에 저장되었습니다.")

if __name__ == "__main__":
    seed()
