# app/services/supabase_service.py
import os
import logging
from typing import List
# supabase-py v2 requires installing 'supabase' >= 2.0 and 'httpx'
# Async client is part of the main package
try:
    from supabase import create_client, Client as AsyncClient # Use Client as AsyncClient type hint
except ImportError:
    logging.error("Failed to import supabase. Ensure 'supabase>=2.0.0' is installed correctly.")
    raise

import google.generativeai as genai # Use embed_content for async

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "models/text-embedding-004")
MATCH_FUNCTION = os.getenv("PGVECTOR_MATCH_FUNCTION", "match_documents")
MATCH_COUNT = int(os.getenv("VECTOR_SEARCH_TOP_K", "20"))

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY]):
    # Log error but allow app to start, handle failure during request
    logger.error("환경 변수 SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY 중 일부 또는 전체가 설정되지 않았습니다. 앱이 정상 작동하지 않을 수 있습니다.")
    # raise ValueError("Missing environment variables") # Don't raise here, handle in agent/main

# Configure Gemini client
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API Key 구성 완료.")
    except Exception as e:
        logger.error(f"Gemini API Key 구성 실패: {e}")
        # App might still run but Gemini features will fail
else:
    logger.warning("GEMINI_API_KEY가 설정되지 않았습니다. Gemini 관련 기능이 작동하지 않습니다.")


# --- Supabase Client Initialization ---
# Client will be created on demand or managed within functions needing it
# This avoids potential issues with async event loops if created globally in some contexts
async def get_supabase_client() -> AsyncClient | None:
    """비동기 Supabase 클라이언트를 생성하고 반환합니다. 실패 시 None 반환."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase URL 또는 Key가 없어 클라이언트를 생성할 수 없습니다.")
        return None
    try:
        # For supabase-py v2+, create_client is likely synchronous, but returns an async client instance
        # The actual async operations happen when calling methods like .rpc().execute()
        # Let's adjust based on common patterns for async clients if create_client itself needs await
        # Assuming create_client is synchronous based on typical patterns:
        supabase: AsyncClient = create_client(SUPABASE_URL, SUPABASE_KEY)
        # If create_client itself is async:
        # supabase: AsyncClient = await create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase 클라이언트 생성 성공")
        return supabase
    except Exception as e:
        logger.error(f"Supabase 클라이언트 생성 실패: {e}")
        return None

# --- Core Functions ---
async def get_gemini_embedding(text: str) -> List[float] | None:
    """주어진 텍스트에 대한 Gemini 임베딩 벡터를 생성합니다. 실패 시 None 반환."""
    # Check if API key is configured *before* making the call
    if not GEMINI_API_KEY:
         logger.error("Gemini API Key가 구성되지 않아 임베딩을 생성할 수 없습니다.")
         return None
    if not text:
        logger.warning("임베딩할 텍스트가 비어있습니다.")
        return None
    try:
        # 올바른 임베딩 생성 방식으로 수정
        result = await genai.embed_content_async(
            model=EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query"
        )
        embedding = result['embedding']
        if not embedding:
            logger.error("Gemini API가 임베딩을 반환하지 않았습니다.")
            return None
        return embedding
    except Exception as e:
        # Log the specific exception during embedding
        logger.error(f"Gemini 임베딩 생성 실패 ({EMBEDDING_MODEL}): {e}", exc_info=True)
        return None

async def query_supabase_vector(embedding: List[float]) -> List[dict] | None:
    """생성된 임베딩 벡터를 사용하여 Supabase에서 유사 문서를 검색합니다. 실패 시 None 반환."""
    if not embedding:
        logger.error("유효한 임베딩 벡터가 없어 Supabase 검색을 수행할 수 없습니다.")
        return None

    supabase = await get_supabase_client()
    if not supabase:
        logger.error("Supabase 클라이언트가 없어 벡터 검색을 수행할 수 없습니다.")
        return None

    try:
        # 매개변수 수정 - Supabase의 match_documents 함수에 맞게 변경
        response = supabase.rpc(
            MATCH_FUNCTION,
            {
                'query_embedding': embedding,
                'match_count': MATCH_COUNT,
                'filter': {}  # 필요한 경우 필터 조건 추가
            }
        ).execute()

        data = response.data
        if data:
            logger.info(f"Supabase에서 {len(data)}개의 유사 문서를 찾았습니다.")
            return data
        else:
            logger.info("Supabase에서 유사 문서를 찾지 못했습니다 (match_threshold 또는 데이터 부족일 수 있음).")
            return [] # Return empty list for successful query with no results

    except Exception as e:
        # Log the specific exception during vector search RPC call
        logger.error(f"Supabase 벡터 검색 RPC 호출 실패 ({MATCH_FUNCTION}): {e}", exc_info=True)
        # Attempt to log more details if the exception object or response has them
        # Note: Accessing response might not be safe if exception occurred before response assignment
        # if 'response' in locals() and hasattr(response, 'error') and response.error:
        #     logger.error(f"Supabase RPC Response Error: {response.error}")
        if hasattr(e, 'details'): logger.error(f"Supabase Error Details: {e.details}")
        if hasattr(e, 'message'): logger.error(f"Supabase Error Message: {e.message}")
        return None # Indicate failure

def build_context_string(docs: List[dict] | None) -> str:
    """검색된 문서 리스트를 하나의 컨텍스트 문자열로 결합합니다. 입력이 None이면 빈 문자열 반환."""
    if docs is None:
        logger.warning("컨텍스트를 빌드할 문서 목록이 없습니다 (None).")
        return ""
    if not docs:
        logger.info("컨텍스트를 빌드할 문서가 없습니다 (빈 리스트).")
        return ""

    contents = [doc.get('content', '') for doc in docs if isinstance(doc, dict) and doc.get('content')]
    valid_contents = [c for c in contents if c]

    if not valid_contents:
        logger.warning("유효한 'content' 필드를 가진 문서가 없어 빈 컨텍스트 생성됨.")
        return ""
    
    # Corrected string joining
    context = "\n---\n".join(valid_contents) 
    logger.info(f"Context 문자열 생성 완료 (원본 문서 {len(docs)}개 -> 유효 내용 {len(valid_contents)}개, 길이: {len(context)})")
    return context 