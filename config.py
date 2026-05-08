import os
from dotenv import load_dotenv

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/modernizer.db")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
VALIDATION_THRESHOLD = int(os.getenv("VALIDATION_THRESHOLD", "70"))
DEFAULT_SOURCE_DIALECT = os.getenv("DEFAULT_SOURCE_DIALECT", "tsql")
DEFAULT_TARGET_DIALECT = os.getenv("DEFAULT_TARGET_DIALECT", "postgresql")
