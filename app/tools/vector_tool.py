# app/tools/vector_tool.py
import logging
from typing import List, Dict, Any
from app.services.supabase_service import (
    get_gemini_embedding,
    query_supabase_vector,
    build_context_string,
)

logger = logging.getLogger(__name__)

class VectorRetrievalTool:
    """
    사용자 질문을 받아 임베딩을 생성하고, Supabase에서 관련 문서를 검색하여
    컨텍스트 문자열을 생성하는 도구입니다.
    """
    async def retrieve_and_build_context(self, query: str) -> Dict[str, Any]:
        """
        질문 처리 파이프라인: 임베딩 생성 -> 벡터 검색 -> 컨텍스트 구축
        실패 시 빈 컨텍스트와 빈 문서 목록 반환.
        """
        logger.info(f"VectorRetrievalTool 시작: query='{query[:50]}...'") # Log part of query
        context = ""
        retrieved_docs = []
        embedding = None
        similar_docs = None

        try:
            # 1. Gemini 임베딩 생성
            embedding = await get_gemini_embedding(query)
            if embedding is None:
                logger.error("임베딩 생성 실패, 빈 결과 반환")
                # 실패 시 빈 컨텍스트와 빈 문서 목록 반환 (이미 기본값)
                return {"context": context, "retrieved_docs": retrieved_docs}
            logger.debug("Gemini 임베딩 생성 완료")

            # 2. Supabase 유사 문서 검색
            similar_docs = await query_supabase_vector(embedding)
            if similar_docs is None:
                 logger.error("Supabase 벡터 검색 실패, 빈 결과 반환")
                 return {"context": context, "retrieved_docs": retrieved_docs}
            if not similar_docs:
                 logger.info("유사 문서를 찾지 못함.")
                 # 검색은 성공했지만 결과가 없으므로 빈 리스트 반환
                 return {"context": context, "retrieved_docs": []}

            logger.debug(f"{len(similar_docs)}개의 유사 문서 검색 완료")
            retrieved_docs = similar_docs # 성공 시 결과 저장

            # 3. Context 생성
            context_string = build_context_string(similar_docs)
            logger.info("컨텍스트 문자열 생성 완료")
            context = context_string # 성공 시 결과 저장

        except Exception as e:
            # Catch any unexpected error during the process
            logger.error(f"VectorRetrievalTool 처리 중 예외 발생: {e}", exc_info=True)
            # Return default empty values upon unexpected failure
            return {"context": "", "retrieved_docs": []}

        # Return the final context and documents
        return {"context": context, "retrieved_docs": retrieved_docs}

# Google ADK의 Tool 클래스를 상속받아 구현할 수도 있습니다.
# from google.ai import developerkit as adk
# class VectorRetrievalADKTool(adk.Tool):
#     ... (ADK 명세에 맞춰 구현)
# 현재는 간단한 클래스로 구현합니다. 