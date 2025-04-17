# app/agents/rag_agent.py
import os
import logging
import google.generativeai as genai
from app.tools.vector_tool import VectorRetrievalTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GENERATIVE_MODEL_NAME = os.getenv("GENERATIVE_MODEL_NAME", "gemini-1.5-flash-preview-001")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Check if API key exists

class RAGAgent:
    """
    VectorRetrievalTool을 사용하여 컨텍스트를 검색하고,
    Gemini 모델을 사용하여 사용자 질문에 답변하는 RAG 에이전트입니다.
    """
    def __init__(self):
        self.model = None
        # Initialize Gemini model only if API key is available
        if GEMINI_API_KEY:
            try:
                self.model = genai.GenerativeModel(GENERATIVE_MODEL_NAME)
                logger.info(f"Gemini 모델 로드 완료: {GENERATIVE_MODEL_NAME}")
            except Exception as e:
                logger.error(f"Gemini 모델 ({GENERATIVE_MODEL_NAME}) 로드 실패: {e}")
                # Set model to None so generate_response can handle it
                self.model = None
        else:
            logger.warning("GEMINI_API_KEY가 없어 Gemini 모델을 로드할 수 없습니다.")
            self.model = None

        # Vector Retrieval 도구 초기화
        self.vector_tool = VectorRetrievalTool()

        # n8n 워크플로우의 설명을 기반으로 시스템 프롬프트 정의
        self.system_instruction = """
너는 한국의 해수욕장 파도 예보 데이터를 분석해서 서핑 입문자나 애호가에게 "이 날, 이 곳에 가면 좋을지"에 대해 친근하고 명확하게 조언해주는 서핑 코치야.

주어진 컨텍스트 문서에는 해수욕장 이름, 날짜, 파고, 피리어드, 스웰 방향, 바람 정보 등이 들어 있어.
사용자의 질문과 검색된 컨텍스트를 바탕으로 가장 유의미한 정보만 요약해서 답변해줘.

응답은 다음을 반드시 포함해야 해:
- 언제 / 어디 해변인지 명시
- 파고 + 피리어드 정보를 단순 나열하지 말고, "힘 있는 파도", "서핑하기엔 약한 파도" 같이 의미를 해석
- 스웰 방향, 바람 방향/세기 정보를 바탕으로 "오프쇼어(해변에서 바다로)", "온쇼어(바다에서 해변으로)" 인지 분석하고 서핑 조건에 미치는 영향 설명
- 총평: "지금 조건이면 입문자에게 딱 좋아요!" / "서핑보단 산책용입니다" 처럼 최종적인 조언으로 마무리

하지 말아야 할 것:
- 단순히 컨텍스트의 수치만 나열하지 마. 의미를 부여하고 해석해줘.
- "좋은지, 나쁜지" 판단 없이 애매하게 끝내지 마. 명확한 결론을 내려줘.
- "정보가 없습니다"라고만 말하지 말고, 어떤 정보가 부족한지 또는 왜 판단이 어려운지 설명하거나 대안을 제시해줘.
- 답변에 마크다운 형식(`*`, `#` 등)을 사용하지 마. 일반 텍스트로만 답변해.

예시 응답:
> 내일 정암 해수욕장은 오전엔 파도가 거의 없지만, 오후부터는 1미터 내외의 괜찮은 파도가 8초 주기로 꾸준히 들어올 것으로 보여. 바람도 육지에서 바다로 부는 약한 오프쇼어라 파도면이 깔끔할 거야. 서핑 시작하는 분들에게는 오후 시간대가 아주 좋을 것 같아! 꼭 가봐!

주어진 컨텍스트를 충실히 활용하되, 자연스럽고 친근한 말투로 실제 서핑 코치처럼 조언해줘.
"""

    async def generate_response(self, user_query: str) -> str:
        """
        사용자 질문을 받아 RAG 프로세스를 거쳐 최종 답변을 생성합니다.
        """
        logger.info(f"RAGAgent 처리 시작: query='{user_query[:50]}...'")

        # Check if model was initialized
        if not self.model:
             logger.error("Gemini 모델이 초기화되지 않아 응답을 생성할 수 없습니다.")
             return "죄송합니다. 챗봇 엔진에 문제가 발생하여 답변을 드릴 수 없습니다." # User-friendly error

        try:
            # 1. Vector Tool을 사용하여 관련 컨텍스트 검색
            logger.info("Vector Tool 호출 시작...")
            retrieval_result = await self.vector_tool.retrieve_and_build_context(user_query)
            logger.info(f"Vector Tool 호출 완료. Context found: {bool(retrieval_result and retrieval_result.get('context'))}")
            context = retrieval_result["context"]
            # retrieved_docs = retrieval_result["retrieved_docs"] # For potential future use

            if not context:
                # If context is empty after retrieval (either failed or no docs found)
                # Try generating a response without context, or return a specific message.
                # Here, we'll try generating without context but adjust the prompt slightly.
                logger.warning("컨텍스트를 찾을 수 없어, 컨텍스트 없이 답변 생성 시도.")
                # Optional: Return a message indicating lack of specific info
                # return "죄송합니다. 질문하신 내용에 대한 구체적인 파도 정보를 찾지 못했습니다. 다른 해변이나 날짜로 질문해주시겠어요?"
                # Let's try generating a response anyway, the model might handle it.
                prompt = f"{self.system_instruction}\n\n--- 검색된 컨텍스트 없음 ---\n\n사용자 질문: {user_query}\n\n서핑 코치 답변:"
            else:
                # 2. 최종 프롬프트 구성 (시스템 지침 + 컨텍스트 + 사용자 질문)
                # Use triple-quoted f-string for multiline prompt
                prompt = f"""{self.system_instruction}

--- 검색된 컨텍스트 시작 ---
{context}
--- 검색된 컨텍스트 끝 ---

사용자 질문: {user_query}

서핑 코치 답변:"""

            logger.debug(f"Gemini 호출 프롬프트 생성 완료 (컨텍스트 포함: {bool(context)})")

            # 3. Gemini 모델 호출하여 답변 생성 (최신 방식으로 업데이트)
            logger.info("Gemini 모델 호출 시작...")
            response = await self.model.generate_content_async(prompt)
            logger.info("Gemini 모델 호출 완료.")

            # 안전 설정 등으로 인해 콘텐츠가 없을 경우 처리
            if not response or not response.text:
                 logger.warning("Gemini 응답 생성 실패 또는 안전 설정에 의해 차단됨")
                 # Provide a user-friendly message about the failure
                 return "죄송합니다. 답변을 생성하는 데 예상치 못한 문제가 발생했습니다." # More generic error

            generated_text = response.text
            logger.info("Gemini 응답 생성 완료")
            return generated_text.strip() # 앞뒤 공백 제거

        except Exception as e:
            # Log the specific exception during response generation
            logger.error(f"RAGAgent 응답 생성 중 오류 발생: {e}", exc_info=True)
            return "죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다." # Generic error for unexpected issues 