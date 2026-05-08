import os

# Set before any project module is imported so config.py reads these values
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://fake.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "fake-key")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
