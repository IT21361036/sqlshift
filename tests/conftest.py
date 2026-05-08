import os

# Set before any project module is imported so config.py reads these values
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5-coder:7b")
