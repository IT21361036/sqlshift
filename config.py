import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/modernizer.db")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
VALIDATION_THRESHOLD = int(os.getenv("VALIDATION_THRESHOLD", "70"))
DEFAULT_SOURCE_DIALECT = os.getenv("DEFAULT_SOURCE_DIALECT", "tsql")
DEFAULT_TARGET_DIALECT = os.getenv("DEFAULT_TARGET_DIALECT", "postgresql")
