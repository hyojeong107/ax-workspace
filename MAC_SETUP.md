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
# 비밀번호: .env 파일의 MYSQL_ROOT_PASSWORD와 동일하게 설정
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

## 가상환경 구조 (Windows vs Mac)

폴더마다 가상환경을 **각자 따로** 가지고 있어요. Windows용(Scripts/)과 Mac용(bin/)이 다르기 때문에 **절대 공유하지 않고 각각 따로 씁니다.**

| 폴더 | Windows 가상환경 | Mac 가상환경 |
|------|-----------------|-------------|
| `07_FitStep_Web` | `07_FitStep_Web/venv/Scripts/activate` | `07_FitStep_Web/venv/bin/activate` |
| `08_FitStep_API` | `08_FitStep_API/venv/Scripts/activate` | `08_FitStep_API/venv/bin/activate` |

### Windows에서 활성화
```bash
# 07_FitStep_Web
cd 07_FitStep_Web
venv\Scripts\activate

# 08_FitStep_API
cd 08_FitStep_API
venv\Scripts\activate
```
> `start.bat` (루트 폴더)으로 한 번에 둘 다 실행 가능

### Mac에서 활성화
```bash
# 07_FitStep_Web
cd 07_FitStep_Web
source venv/bin/activate

# 08_FitStep_API
cd 08_FitStep_API
source venv/bin/activate
```

### 처음 맥 세팅 시 가상환경 새로 만드는 법
```bash
# 07_FitStep_Web
cd ~/ax-workspace/07_FitStep_Web
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 08_FitStep_API
cd ~/ax-workspace/08_FitStep_API
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
> Windows에서 만든 venv는 맥에서 안 됨 (반대도 마찬가지). 새로 만들어야 해요.

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
OPENAI_API_KEY=여기에_실제_키_입력
RAG_API_KEY=여기에_비밀번호_입력
MYSQL_ROOT_PASSWORD=여기에_비밀번호_입력
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=여기에_비밀번호_입력
DB_NAME=fitstep
RAPIDAPI_KEY=여기에_실제_키_입력
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
curl -X POST "http://localhost:8000/db/exercises/sync" -H "X-API-Key: [RAG_API_KEY 값]"
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
