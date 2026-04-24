"""공공데이터(체력측정, 운동추천)를 ChromaDB에 초기 인덱싱하는 스크립트"""

import os
import json
import csv
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
FITNESS_JSON = os.path.join(os.path.dirname(__file__), "data", "체력측정 및 운동처방 종합 데이터.json")
EXERCISE_CSV = os.path.join(os.path.dirname(__file__), "data", "국민연령별추천운동정보.csv")

FITNESS_COLLECTION = "fitness_measurement"
EXERCISE_COLLECTION = "exercise_recommendation"

# MESURE_IEM 코드 → 한글 필드명
MEASUREMENT_CODE_MAP = {
    "MESURE_IEM_001_VALUE": "신장(cm)",
    "MESURE_IEM_002_VALUE": "체중(kg)",
    "MESURE_IEM_003_VALUE": "체지방률(%)",
    "MESURE_IEM_005_VALUE": "허리둘레(cm)",
    "MESURE_IEM_006_VALUE": "수축기혈압",
    "MESURE_IEM_007_VALUE": "BMI",
    "MESURE_IEM_008_VALUE": "윗몸일으키기(회)",
    "MESURE_IEM_018_VALUE": "제자리멀리뛰기(cm)",
}


def _get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _bmi_category(bmi_val) -> str:
    """BMI 수치를 카테고리 문자열로 변환"""
    try:
        bmi = float(bmi_val)
    except (TypeError, ValueError):
        return ""
    if bmi < 18.5:
        return "저체중"
    elif bmi < 23.0:
        return "정상"
    elif bmi < 25.0:
        return "과체중"
    else:
        return "비만"


def _build_fitness_sentence(row: dict) -> str:
    """체력측정 레코드를 자연어 문장으로 변환 (null 필드 제외)"""
    age = row.get("MESURE_AGE_CO")
    gender_code = row.get("SEXDSTN_FLAG_CD", "")
    gender = "남성" if gender_code == "M" else ("여성" if gender_code == "F" else gender_code)
    grade = row.get("CRTFC_FLAG_NM", "")

    parts = []
    if age is not None and age != "":
        parts.append(f"{age}세 {gender}")
    elif gender:
        parts.append(gender)

    # 신장/체중/BMI 순서로 우선 배치
    priority_fields = [
        ("MESURE_IEM_001_VALUE", "신장"),
        ("MESURE_IEM_002_VALUE", "체중"),
        ("MESURE_IEM_007_VALUE", "BMI"),
    ]
    for key, label in priority_fields:
        val = row.get(key)
        if val is not None and val != "":
            unit_map = {"신장": "cm", "체중": "kg", "BMI": ""}
            unit = unit_map.get(label, "")
            parts.append(f"{label} {val}{unit}")

    # 나머지 수치 필드
    other_fields = [
        ("MESURE_IEM_008_VALUE", "윗몸일으키기", "회"),
        ("MESURE_IEM_018_VALUE", "제자리멀리뛰기", "cm"),
        ("MESURE_IEM_003_VALUE", "체지방률", "%"),
        ("MESURE_IEM_005_VALUE", "허리둘레", "cm"),
        ("MESURE_IEM_006_VALUE", "수축기혈압", ""),
    ]
    for key, label, unit in other_fields:
        val = row.get(key)
        if val is not None and val != "":
            parts.append(f"{label} {val}{unit}")

    sentence = ", ".join(parts)
    if grade:
        sentence += f". 등급: {grade}."

    # 운동처방 내용 추가
    prescription = row.get("MVM_PRSCRPTN_CN")
    if prescription and str(prescription).strip():
        sentence += f" 운동처방: {str(prescription).strip()}"

    return sentence


def index_fitness_data(force_reindex: bool = False):
    print("체력측정 데이터 인덱싱 시작...")
    embeddings = _get_embeddings()
    store = Chroma(
        collection_name=FITNESS_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )

    # 증분 인덱싱: 데이터가 있으면 스킵
    existing = store.get()
    if existing["ids"]:
        if not force_reindex:
            print(f"  이미 {len(existing['ids'])}개 문서가 있습니다. 스킵 (--force로 재인덱싱)")
            return
        store.delete(ids=existing["ids"])
        print(f"  기존 {len(existing['ids'])}개 문서 삭제 후 재인덱싱")

    with open(FITNESS_JSON, encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for i, row in enumerate(data):
        text = _build_fitness_sentence(row)
        if not text.strip():
            continue

        bmi_raw = row.get("MESURE_IEM_007_VALUE")
        try:
            bmi_float = float(bmi_raw) if bmi_raw not in (None, "") else None
        except (ValueError, TypeError):
            bmi_float = None

        try:
            age_int = int(row.get("MESURE_AGE_CO", 0)) if row.get("MESURE_AGE_CO") not in (None, "") else None
        except (ValueError, TypeError):
            age_int = None

        gender_code = row.get("SEXDSTN_FLAG_CD", "")
        gender_str = "남성" if gender_code == "M" else ("여성" if gender_code == "F" else gender_code)

        metadata = {
            "source": "fitness_measurement",
            "age_group": str(row.get("AGRDE_FLAG_NM", "")),
            "gender": gender_str,
            "grade": str(row.get("CRTFC_FLAG_NM", "")),
            "bmi": str(bmi_float) if bmi_float is not None else "",
            "bmi_category": _bmi_category(bmi_float),
            "age": age_int if age_int is not None else 0,
        }
        documents.append(Document(page_content=text, metadata=metadata))

    batch_size = 50
    total = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        ids = [f"fitness_{start + j}" for j in range(len(batch))]
        store.add_documents(documents=batch, ids=ids)
        total += len(batch)
        print(f"  {total}/{len(documents)} 완료")

    print(f"체력측정 데이터 인덱싱 완료: {total}개 문서")


def index_exercise_recommendation(force_reindex: bool = False):
    print("운동추천 데이터 인덱싱 시작...")
    embeddings = _get_embeddings()
    store = Chroma(
        collection_name=EXERCISE_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )

    # 증분 인덱싱: 데이터가 있으면 스킵
    existing = store.get()
    if existing["ids"]:
        if not force_reindex:
            print(f"  이미 {len(existing['ids'])}개 문서가 있습니다. 스킵 (--force로 재인덱싱)")
            return
        store.delete(ids=existing["ids"])
        print(f"  기존 {len(existing['ids'])}개 문서 삭제 후 재인덱싱")

    with open(EXERCISE_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # (연령대+BMI등급+성별+상장등급+운동단계) 조합 → 추천운동 묶기
    grouped: dict[tuple, list] = {}
    for row in rows:
        key = (
            row.get("AGRDE_FLAG_NM", "").strip(),
            row.get("BMI_IDEX_GRAD_NM", "").strip(),
            row.get("MBER_SEXDSTN_FLAG_CD", "").strip(),
            row.get("COAW_FLAG_NM", "").strip(),
            row.get("SPORTS_STEP_NM", "").strip(),
        )
        exercise = row.get("RECOMEND_MVM_NM", "").strip()
        if exercise:
            grouped.setdefault(key, []).append(exercise)

    documents = []
    for i, ((age, bmi_grade, gender_code, award_grade, step), exercises) in enumerate(grouped.items()):
        gender_str = "남성" if gender_code == "M" else ("여성" if gender_code == "F" else gender_code)
        exercises_str = ", ".join(exercises)
        text = f"{age} {gender_str} {bmi_grade} {award_grade} {step}: {exercises_str}"

        metadata = {
            "source": "exercise_recommendation",
            "age_group": age,
            "gender": gender_str,
            "bmi_grade": bmi_grade,
            "award_grade": award_grade,
            "exercise_step": step,
            "exercise_count": len(exercises),
        }
        documents.append(Document(page_content=text, metadata=metadata))

    batch_size = 50
    total = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        ids = [f"exercise_{start + j}" for j in range(len(batch))]
        store.add_documents(documents=batch, ids=ids)
        total += len(batch)
        print(f"  {total}/{len(documents)} 완료")

    print(f"운동추천 데이터 인덱싱 완료: {total}개 문서")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="공공데이터 ChromaDB 인덱싱")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 데이터를 삭제하고 강제 재인덱싱",
    )
    args = parser.parse_args()

    index_fitness_data(force_reindex=args.force)
    index_exercise_recommendation(force_reindex=args.force)
    print("\n모든 공공데이터 인덱싱 완료!")
