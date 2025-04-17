# FindYourWave RAG Chatbot (Python/FastAPI/Gemini/Supabase)

n8n으로 구성된 Supabase + Gemini 기반 RAG 챗봇 워크플로우를 Python, FastAPI, Google Generative AI SDK 환경에서 재현한 프로젝트입니다.

## 기능

- 사용자의 서핑 관련 질문 (예: "내일 양양 파도 어때?")을 입력받습니다.
- Google Gemini Embedding API를 사용하여 질문 텍스트를 임베딩 벡터로 변환합니다.
- Supabase PostgreSQL 데이터베이스 (pgvector 확장 기능 사용)에서 질문과 유사한 파도 예보 문서를 검색합니다.
- 검색된 문서들을 컨텍스트로 사용하여 Google Gemini Chat API (RAG 방식)를 통해 사용자 질문에 대한 답변을 생성합니다.
- 답변은 파고, 주기, 바람 등을 종합적으로 고려하여 서핑 가능 여부와 추천 사항을 포함합니다.
- FastAPI를 사용하여 `/chatbot` 엔드포인트를 제공합니다.

## 프로젝트 구조

```
lastchatbot/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI 앱, 라우팅, 초기화
│   ├── agents/           # RAG 로직 및 Gemini 모델 연동
│   │   └── rag_agent.py
│   ├── tools/            # Supabase 검색 및 컨텍스트 생성 도구
│   │   └── vector_tool.py
│   ├── services/         # 외부 서비스 연동 (Supabase, Gemini API)
│   │   └── supabase_service.py
│   ├── models/           # Pydantic 데이터 모델
│   │   └── chat.py
│   └── .env              # 환경 변수 설정 파일
├── requirements.txt      # Python 의존성 목록
└── README.md             # 프로젝트 설명
```

## 설정 방법

1.  **저장소 클론:**
    ```bash
    git clone <your-repository-url>
    cd lastchatbot
    ```

2.  **가상 환경 생성 및 활성화:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    # .venv\Scripts\activate  # Windows
    ```

3.  **의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **환경 변수 설정:**
    - `app/.env` 파일을 확인하고 Supabase URL, Supabase Key, Gemini API Key 등의 값을 올바르게 설정합니다.
    ```dotenv
    # app/.env
    GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
    
    # Supabase 설정
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
    
    # Gemini 설정
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    EMBEDDING_MODEL_NAME="models/text-embedding-004"
    GENERATIVE_MODEL_NAME="gemini-1.5-flash-latest"
    
    # 벡터 검색 설정
    PGVECTOR_MATCH_FUNCTION="match_documents"
    VECTOR_SEARCH_TOP_K=20
    
    # CORS 설정
    ALLOWED_ORIGINS="*"
    
    # Google Cloud 설정
    GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
    GOOGLE_CLOUD_LOCATION=us-central1
    GOOGLE_GENAI_USE_VERTEXAI=False
    ```
    * **주의:** Supabase Key는 보안에 유의하여 관리하세요.
    * `PGVECTOR_MATCH_FUNCTION`은 Supabase 프로젝트에 생성한 벡터 검색 함수의 이름과 일치해야 합니다. (예: `match_documents`)
    * `EMBEDDING_MODEL_NAME`과 `GENERATIVE_MODEL_NAME`은 Gemini API에서 지원하는 모델로 설정해야 합니다.

5.  **Supabase 설정 확인:**
    - Supabase 프로젝트에 `documents` 테이블이 있고, `embedding` 컬럼 (pgvector 타입) 및 `content` 컬럼 등이 있는지 확인합니다.
    - 벡터 검색을 위한 SQL 함수 (예: `match_documents`)가 Supabase SQL Editor를 통해 생성되어 있는지 확인합니다. 함수 예시는 Supabase AI 문서를 참고하세요.

## 실행 방법

```bash
python app/main.py
```

또는 uvicorn을 직접 사용하여 실행할 수도 있습니다:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 `http://localhost:8000/docs` 에서 API 문서를 확인할 수 있습니다.

## API 사용 예시

POST 요청을 `/chatbot` 엔드포인트로 보냅니다.

**Request Body:**

```json
{
  "message": "내일 모레 죽도 해수욕장 파도 어때?",
  "session_id": "user123" // 선택 사항
}
```

**Response Body (예시):**

```json
{
  "reply": "내일 모레 죽도 해수욕장은 오전에 파도가 좀 작지만 오후에는 1.2미터 정도의 힘 있는 파도가 9초 주기로 들어올 것 같아요. 바람은 약간 강한 온쇼어(바다->육지)가 예상돼서 파도 면이 조금 지저분할 수 있지만, 중급 이상 서퍼라면 충분히 즐길 수 있을 거예요. 초보자는 조금 힘들 수 있으니 참고하세요!"
}
```

## 문제 해결

- **임베딩 모델 오류:** `models/text-embedding-004`와 같은 올바른 Gemini 임베딩 모델명을 사용하고 있는지 확인하세요.
- **API 키 오류:** Gemini API 키가 올바르게 설정되어 있는지 확인하세요. Gemini API를 사용하기 위해서는 Google Cloud 콘솔에서 API를 활성화해야 할 수 있습니다.
- **모델 응답 오류:** 최신 Gemini API에 맞게 `generate_content_async` 응답을 처리하고 있는지 확인하세요.

## 추가 고려 사항

- **오류 처리:** 기본적인 오류 처리가 포함되어 있으나, 실제 운영 환경에서는 더 상세한 오류 로깅 및 모니터링이 필요합니다.
- **비동기 처리:** FastAPI와 `supabase-py` v2, `google-generativeai` 라이브러리를 사용하여 비동기적으로 처리하여 성능을 개선했습니다.
- **보안:** Supabase 키와 API 키는 환경 변수를 통해 안전하게 관리하고, CORS 설정을 통해 허용된 출처만 API를 호출할 수 있도록 제한해야 합니다.
- **테스트:** 유닛 테스트 및 통합 테스트를 추가하여 코드의 안정성을 높일 수 있습니다.
- **대화 메모리:** 현재 구현에는 대화 기록(메모리) 기능이 포함되어 있지 않습니다. 필요시 `session_id`를 활용하여 PostgreSQL 또는 다른 저장소에 대화 내용을 저장하고 검색 컨텍스트에 활용하는 기능을 추가할 수 있습니다. 