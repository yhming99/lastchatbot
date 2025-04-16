import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import sys

# Ensure the app directory is in the Python path
# This helps with imports like `from app.models...` when running from the root directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env file from the app directory
env_path = os.path.join(APP_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}. Make sure it exists and contains necessary variables.")

# Now that .env is loaded (or warning issued), import modules that depend on it
from app.models.chat import ChatRequest, ChatResponse
from app.agents.rag_agent import RAGAgent

# --- Logging Configuration ---
# Use basicConfig for simplicity, or configure using dictConfig for more complex setups
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="FindYourWave RAG Chatbot",
    description="Supabase와 Gemini를 이용한 서핑 예보 챗봇 API",
    version="1.0.0"
)

# --- CORS Middleware ---
# Read allowed origins from environment variable, default to "*" for development
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

if not allowed_origins:
    logger.warning("ALLOWED_ORIGINS environment variable is empty or invalid. Defaulting to '*'.")
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all standard methods
    allow_headers=["*"] # Allows all headers
)
logger.info(f"CORS enabled for origins: {allowed_origins}")

# --- Global State (Agent Initialization) ---
# Initialize the agent when the application starts.
# Handle potential errors during initialization.
rag_agent = None
try:
    rag_agent = RAGAgent()
    # Check if the underlying model failed to initialize
    if rag_agent and not rag_agent.model:
        logger.warning("RAG Agent initialized, but the Gemini model failed to load (likely missing API key or invalid key).")
        # Keep rag_agent instance for now, but endpoint will fail if model needed
    elif rag_agent:
        logger.info("RAG Agent 초기화 완료")
    else: # Should not happen if RAGAgent() doesn't return None, but defensive check
         logger.error("RAG Agent 초기화 실패 (에이전트 객체 생성 실패).")
except Exception as e:
    logger.critical(f"RAG Agent 초기화 중 예외 발생: {e}", exc_info=True)
    # Ensure rag_agent is None if initialization failed critically
    rag_agent = None

# --- Exception Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log the HTTP exception details
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}, # Use detail field consistently
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log any other unhandled exceptions
    logger.error(f"처리되지 않은 예외 발생: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "내부 서버 오류가 발생했습니다."},
    )

# --- API Endpoints ---
@app.get("/", summary="Health Check")
async def health_check():
    """서버 상태와 RAG 에이전트 초기화 상태를 확인합니다."""
    agent_status = "initialized_with_model" if rag_agent and rag_agent.model else \
                   "initialized_without_model" if rag_agent else \
                   "initialization_failed"
    return {"status": "ok", "agent_status": agent_status}

@app.post("/chatbot", response_model=ChatResponse, summary="Chatbot Endpoint")
async def chat_endpoint(request: ChatRequest):
    """
    사용자 메시지를 받아 RAG 챗봇 응답을 반환합니다.
    """
    # Check if agent (and its model) is ready
    if not rag_agent or not rag_agent.model:
         logger.error("RAG Agent 또는 내부 모델이 준비되지 않아 요청을 처리할 수 없습니다.")
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="챗봇 서비스가 현재 사용할 수 없습니다. 관리자에게 문의하거나 잠시 후 다시 시도해주세요."
         )

    user_message = request.message
    session_id = request.session_id # Currently unused, but available

    if not user_message or not user_message.strip():
        logger.warning("빈 메시지 또는 공백만 있는 메시지 요청 수신")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="메시지를 입력해주세요."
        )

    logger.info(f"'/chatbot' 요청 수신: session='{session_id}', message='{user_message[:50]}...'")

    try:
        # RAG Agent를 사용하여 응답 생성
        reply = await rag_agent.generate_response(user_message)
        logger.info(f"응답 생성 완료 (일부): '{reply[:50]}...'")
        return ChatResponse(reply=reply)
    except Exception as e:
        # Catch unexpected errors during response generation that weren't handled by the agent
        logger.error(f"'/chatbot' 엔드포인트 처리 중 예기치 않은 오류 발생: {e}", exc_info=True)
        # Re-raise as a standard internal server error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="챗봇 응답 생성 중 오류가 발생했습니다."
        )

# --- Uvicorn Runner (for local development) ---
# This block allows running the app directly using `python app/main.py`
if __name__ == "__main__":
    import uvicorn
    logger.info("FastAPI 애플리케이션을 Uvicorn으로 실행합니다 (개발 모드, reload=True)")
    # Run from the project root context if possible, or ensure ASGI app path is correct
    # Running `python app/main.py` makes `app.main:app` the correct path.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)