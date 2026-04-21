# FitStep - Mac 세팅 가이드

## 사전 준비 (설치)

### 1. Homebrew 설치 (없으면)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Python 설치 (없으면)
```bash
brew install python@3.11
python3 --version  # 확인
```

### 3. MySQL 설치
```bash
brew install mysql
brew services start mysql

# root 비밀번호 설정
mysql_secure_installation
# 비밀번호: khj570832!  (기존 .env와 동일하게)
```

### 4. MySQL DB 생성
```bash
mysql -u root -p
```
```sql
CREATE DATABASE fitstep CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

---

## 코드 받기

```bash
git clone [레포 주소]
cd ax-workspace
```
> 이미 있으면 `git pull` 만 해도 됨

---

## API 서버 세팅 (08_FitStep_API)

### 1. 가상환경 생성 및 패키지 설치
```bash
cd 08_FitStep_API
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install httpx python-dotenv
```

### 2. .env 파일 확인
`08_FitStep_API/.env` 파일이 있는지 확인하고, 없으면 아래 내용으로 새로 만들기:
```
OPENAI_API_KEY=REDACTED
RAG_API_KEY=khj570832!
MYSQL_ROOT_PASSWORD=khj570832!
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=khj570832!
DB_NAME=fitstep
RAPIDAPI_KEY=f4fb53b5e0msh572e80979b2b726p1fe91cjsnda237c723240
```

### 3. API 서버 실행
```bash
cd 08_FitStep_API
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 4. 운동 목록 동기화 (처음 한 번만)
서버 실행 후 새 터미널에서:
```bash
curl -X POST "http://localhost:8000/db/exercises/sync" -H "X-API-Key: khj570832!"
```
> `{"synced": 1300}` 같은 응답 오면 성공. 30초 정도 걸림.

---

## 웹 서버 세팅 (07_FitStep_Web)

### 1. 가상환경 생성 및 패키지 설치
```bash
cd 07_FitStep_Web
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install httpx
```

### 2. 웹 서버 실행
```bash
cd 07_FitStep_Web
source venv/bin/activate
streamlit run app.py
```
> 브라우저에서 `http://localhost:8501` 열기

---

## 실행 순서 요약

매번 작업할 때 이 순서로 실행하면 돼요:

**터미널 1 - API 서버**
```bash
cd 08_FitStep_API
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**터미널 2 - 웹 서버**
```bash
cd 07_FitStep_Web
source venv/bin/activate
streamlit run app.py
```

---

## 자주 나오는 에러

| 에러 | 원인 | 해결 |
|------|------|------|
| `mysql.connector.errors.DatabaseError` | MySQL 안 켜져 있음 | `brew services start mysql` |
| `ModuleNotFoundError` | 패키지 설치 안 됨 | `pip install -r requirements.txt` |
| `Connection refused` | API 서버 안 켜져 있음 | 터미널 1 먼저 실행 |
| GIF 안 나옴 | 운동 목록 sync 안 됨 | sync curl 명령어 다시 실행 |
