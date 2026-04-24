"""공공데이터(체력측정, 운동추천)를 ChromaDB에 초기 인덱싱하는 스크립트 (Contextual Retrieval 적용)"""

import os
import json
import csv
import sys
import pickle
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
import anthropic
from rank_bm25 import BM25Okapi

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FITNESS_JSON = os.path.join(DATA_DIR, "체력측정 및 운동처방 종합 데이터.json")
EXERCISE_CSV = os.path.join(DATA_DIR, "국민연령별추천운동정보.csv")
BM25_FITNESS_PATH = os.path.join(DATA_DIR, "bm25_fitness.pkl")
BM25_EXERCISE_PATH = os.path.join(DATA_DIR, "bm25_exercise.pkl")

FITNESS_COLLECTION = "fitness_measurement"
EXERCISE_COLLECTION = "exercise_recommendation"

FITNESS_DATASET_DESC = (
    "국민체력100 체력측정 및 운동처방 종합 데이터셋으로, "
    "연령대·성별·BMI 등급별 체력 측정 결과(신장, 체중, BMI, 윗몸일으키기, 제자리멀리뛰기, "
    "체지방률, 허리둘레, 수축기혈압)와 운동처방 내용을 포함합니다."
)
EXERCISE_DATASET_DESC = (
    "국민 연령대별 추천 운동 정보 데이터셋으로, "
    "연령대·BMI등급·성별·상장등급·운동단계 조합에 따른 추천 운동 목록을 포함합니다."
)

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


def _get_claude_client():
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _generate_context(claude_client, dataset_desc: str, chunk_text: str) -> str:
    """Claude Haiku로 청크에 대한 컨텍스트 설명을 생성합니다."""
    prompt = (
        f"다음은 데이터셋 설명입니다:\n{dataset_desc}\n\n"
        f"다음 청크에 대해 간결한 컨텍스트 설명을 한 문장으로 작성하세요. "
        f"형식: '이 청크는 [내용 요약].'\n\n청크:\n{chunk_text}"
    )
    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _make_contextual_text(dataset_desc: str, context: str, chunk_text: str) -> str:
    """컨텍스트 설명을 청크 앞에 붙인 최종 텍스트를 반환합니다."""
    return f"이 문서는 {dataset_desc} {context}\n{chunk_text}"


def _tokenize(text: str) -> list[str]:
    """BM25용 단순 공백/자모 토크나이저."""
    return text.split()


def _bmi_category(bmi_val) -> str:
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
    age = row.get("MESURE_AGE_CO")
    gender_code = row.get("SEXDSTN_FLAG_CD", "")
    gender = "남성" if gender_code == "M" else ("여성" if gender_code == "F" else gender_code)
    grade = row.get("CRTFC_FLAG_NM", "")

    parts = []
    if age is not None and age != "":
        parts.append(f"{age}세 {gender}")
    elif gender:
        parts.append(gender)

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

    prescription = row.get("MVM_PRSCRPTN_CN")
    if prescription and str(prescription).strip():
        sentence += f" 운동처방: {str(prescription).strip()}"

    return sentence


def index_fitness_data(force_reindex: bool = False):
    print("체력측정 데이터 인덱싱 시작 (Contextual Retrieval)...")
    embeddings = _get_embeddings()
    claude_client = _get_claude_client()

    store = Chroma(
        collection_name=FITNESS_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )

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
    contextual_texts = []  # BM25 인덱싱용

    for i, row in enumerate(data):
        text = _build_fitness_sentence(row)
        if not text.strip():
            continue

        # Claude로 컨텍스트 생성
        context = _generate_context(claude_client, FITNESS_DATASET_DESC, text)
        contextual_text = _make_contextual_text(FITNESS_DATASET_DESC, context, text)

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
            "original_text": text,
        }
        # Contextual Embedding: 컨텍스트가 붙은 텍스트로 임베딩
        documents.append(Document(page_content=contextual_text, metadata=metadata))
        contextual_texts.append(contextual_text)

        if (i + 1) % 50 == 0:
            print(f"  컨텍스트 생성 중... {i + 1}/{len(data)}")

    # ChromaDB 저장 (배치)
    batch_size = 50
    total = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        ids = [f"fitness_{start + j}" for j in range(len(batch))]
        store.add_documents(documents=batch, ids=ids)
        total += len(batch)
        print(f"  ChromaDB 저장: {total}/{len(documents)}")

    # BM25 인덱스 저장
    tokenized_corpus = [_tokenize(t) for t in contextual_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_data = {"bm25": bm25, "texts": contextual_texts}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BM25_FITNESS_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    print(f"체력측정 데이터 인덱싱 완료: {total}개 문서, BM25 저장: {BM25_FITNESS_PATH}")


def index_exercise_recommendation(force_reindex: bool = False):
    print("운동추천 데이터 인덱싱 시작 (Contextual Retrieval)...")
    embeddings = _get_embeddings()
    claude_client = _get_claude_client()

    store = Chroma(
        collection_name=EXERCISE_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PATH,
        collection_metadata={"hnsw:space": "cosine"},
    )

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
    contextual_texts = []

    for i, ((age, bmi_grade, gender_code, award_grade, step), exercises) in enumerate(grouped.items()):
        gender_str = "남성" if gender_code == "M" else ("여성" if gender_code == "F" else gender_code)
        exercises_str = ", ".join(exercises)
        text = f"{age} {gender_str} {bmi_grade} {award_grade} {step}: {exercises_str}"

        # Claude로 컨텍스트 생성
        context = _generate_context(claude_client, EXERCISE_DATASET_DESC, text)
        contextual_text = _make_contextual_text(EXERCISE_DATASET_DESC, context, text)

        metadata = {
            "source": "exercise_recommendation",
            "age_group": age,
            "gender": gender_str,
            "bmi_grade": bmi_grade,
            "award_grade": award_grade,
            "exercise_step": step,
            "exercise_count": len(exercises),
            "original_text": text,
        }
        documents.append(Document(page_content=contextual_text, metadata=metadata))
        contextual_texts.append(contextual_text)

        if (i + 1) % 50 == 0:
            print(f"  컨텍스트 생성 중... {i + 1}/{len(grouped)}")

    batch_size = 50
    total = 0
    for start in range(0, len(documents), batch_size):
        batch = documents[start:start + batch_size]
        ids = [f"exercise_{start + j}" for j in range(len(batch))]
        store.add_documents(documents=batch, ids=ids)
        total += len(batch)
        print(f"  ChromaDB 저장: {total}/{len(documents)}")

    tokenized_corpus = [_tokenize(t) for t in contextual_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_data = {"bm25": bm25, "texts": contextual_texts}
    with open(BM25_EXERCISE_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    print(f"운동추천 데이터 인덱싱 완료: {total}개 문서, BM25 저장: {BM25_EXERCISE_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="공공데이터 ChromaDB 인덱싱 (Contextual Retrieval)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 데이터를 삭제하고 강제 재인덱싱",
    )
    args = parser.parse_args()

    index_fitness_data(force_reindex=args.force)
    index_exercise_recommendation(force_reindex=args.force)
    print("\n모든 공공데이터 인덱싱 완료!")
