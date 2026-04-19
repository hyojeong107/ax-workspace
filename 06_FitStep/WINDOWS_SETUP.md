# Windows 환경 세팅 가이드

Mac에서 작업한 FitStep을 Windows에서 실행하기 위한 순서입니다.  
위에서부터 순서대로 따라하면 됩니다.

---

## 사전 확인

아래 두 가지가 설치되어 있어야 합니다. 없으면 먼저 설치하세요.

- **Python 3.9+** → https://www.python.org/downloads/ (설치 시 "Add to PATH" 반드시 체크)
- **MySQL** → https://dev.mysql.com/downloads/installer/ (MySQL Community Server)

---

## Step 1. 코드 받기

```bash
git clone <저장소_URL>
cd 06_FitStep
```

또는 이미 clone 되어 있다면:

```bash
cd 06_FitStep
git pull
```

---

## Step 2. 가상환경 생성 및 패키지 설치

> Mac에서 쓰던 venv는 Windows에서 사용 불가. 반드시 새로 만들어야 합니다.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

설치 완료 후 프롬프트 앞에 `(venv)` 가 붙으면 정상입니다.

---

## Step 3. .env 파일 작성

`.env` 파일은 gitignore 처리되어 있어 자동으로 받아지지 않습니다.  
아래 내용을 복사해서 `06_FitStep` 폴더 안에 `.env` 파일로 저장하세요.

```env
OPENAI_API_KEY=sk-여기에_본인_키_입력

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=여기에_MySQL_비밀번호_입력
DB_NAME=fitstep
```

> `.env.example` 파일이 참고용으로 있습니다.

---

## Step 4. MySQL 확인

MySQL이 실행 중인지 확인합니다.

```bash
mysql -u root -p
```

접속이 되면 OK입니다. 데이터베이스와 테이블은 **앱 첫 실행 시 자동 생성**되므로 따로 만들 필요 없습니다.

---

## Step 5. 헬스장 기구 데이터 적재

`data/` 폴더는 gitignore 처리되어 있어 Mac에서 만든 헬스장 데이터가 없습니다.  
두 가지 방법 중 선택하세요.

### 방법 A. 샘플 데이터 사용 (빠름)

`data/gym_1.json` 파일을 Mac에서 직접 복사해서 `06_FitStep/data/` 폴더 안에 붙여넣기 후:

```bash
python seed_gym.py
```

### 방법 B. 앱 실행 후 직접 입력

앱 실행 → 메뉴 `4` 선택 → 헬스장 이름과 기구 목록 직접 입력  
(입력한 내용이 자동으로 JSON 저장 + 벡터 DB 임베딩됩니다)

---

## Step 6. 앱 실행

```bash
python main.py
```

---

## Mac 기록을 Windows에서 이어가고 싶다면

기본 설정은 **각 PC마다 별도 DB**를 사용합니다.  
Mac에서 쌓은 운동 기록을 Windows에서도 이어가려면 **클라우드 MySQL**을 사용하면 됩니다.

### 클라우드 MySQL 설정 방법 (Railway 기준)

1. https://railway.app 에서 무료 계정 생성
2. New Project → MySQL 선택
3. 생성된 DB의 접속 정보를 `.env`에 입력

```env
DB_HOST=여기에_railway_호스트
DB_PORT=여기에_포트번호
DB_USER=여기에_유저명
DB_PASSWORD=여기에_비밀번호
DB_NAME=railway
```

4. Mac의 `.env`도 동일하게 수정하면 두 기기가 같은 DB를 바라봅니다.

---

## 자주 발생하는 오류

| 오류 메시지 | 원인 | 해결 방법 |
|------------|------|----------|
| `No module named 'rich'` | 패키지 미설치 | `pip install -r requirements.txt` |
| `Access denied for user 'root'` | MySQL 비밀번호 틀림 | `.env`의 `DB_PASSWORD` 확인 |
| `Can't connect to MySQL server` | MySQL 미실행 | MySQL 서비스 시작 |
| `No module named 'chromadb'` | chromadb 미설치 | `pip install chromadb` |
| `venv\Scripts\activate` 오류 | PowerShell 보안 정책 | `Set-ExecutionPolicy RemoteSigned` 실행 후 재시도 |
