import os
from openai import OpenAI

_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

client = OpenAI(base_url=_OLLAMA_BASE_URL, api_key="ollama")


def call_qwen(system_prompt: str, user_message: str) -> str:
    response = client.chat.completions.create(
        model=_OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()
