import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("DASHSCOPE_API_KEY", "")
    base_url: str = os.getenv("BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 主项目命名（优先）+ lab 命名（兼容）
    llm_model: str = os.getenv("LLM_MODEL", os.getenv("MODEL_NAME", "qwen-turbo"))
    debate_temperature: float = float(os.getenv("DEBATE_TEMPERATURE", os.getenv("MODEL_TEMPERATURE", "0.7")))
    debate_max_tokens: int = int(os.getenv("DEBATE_MAX_TOKENS", os.getenv("MODEL_MAX_TOKENS", "1000")))
    debate_rounds_default: int = int(os.getenv("DEBATE_ROUNDS", "3"))

    auditor_model: str = os.getenv("AUDITOR_MODEL", "qwen-turbo")
    fast_model: str = os.getenv("FAST_MODEL", "qwen-flash")
    coder_model: str = os.getenv("CODER_MODEL", "qwen3-coder-plus")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    vector_dim: int = int(os.getenv("VECTOR_DIM", "1024"))
    qdrant_path: str = os.getenv("QDRANT_PATH", "./qdrant_db")
    max_messages_before_summary: int = int(os.getenv("MAX_MESSAGES_BEFORE_SUMMARY", "10"))
    max_chars_before_summary: int = int(os.getenv("MAX_CHARS_BEFORE_SUMMARY", "6000"))
    
    max_retry_count: int = int(os.getenv("MAX_RETRY_COUNT", "2"))
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
    max_memory_turns: int = int(os.getenv("MAX_MEMORY_TURNS", "5"))
    default_theory_top_k: int = int(os.getenv("DEFAULT_THEORY_TOP_K", "3"))
    default_politics_top_k: int = int(os.getenv("DEFAULT_POLITICS_TOP_K", "3"))
    
    xunfei_ppt_app_id: str = os.getenv("XUNFEI_PPT_APP_ID", "")
    xunfei_ppt_api_secret: str = os.getenv("XUNFEI_PPT_API_SECRET", "")
    xunfei_ppt_api_key: str = os.getenv("XUNFEI_PPT_API_KEY", "")
    
    # SiliconFlow API配置（AI背景生成）
    siliconflow_api_key: str = os.getenv("SILICONFLOW_API_KEY", "")

settings = Settings()

if not settings.api_key:
    raise RuntimeError("DASHSCOPE_API_KEY 未设置，请在 .env 或环境变量中配置")