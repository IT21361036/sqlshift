import os
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

_client = None
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "translator.txt")


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
    return _client


def _load_prompt() -> str:
    with open(_PROMPT_PATH, "r") as f:
        return f.read()


def translate(sql: str, source_dialect: str, target_dialect: str, error_context: list = None) -> str:
    error_block = ""
    if error_context:
        lines = "\n".join(f"- {e}" for e in error_context)
        error_block = f"\nPrevious translation failed validation with these issues:\n{lines}\nFix all of these issues in your translation.\n"

    system_prompt = _load_prompt().format(
        source_dialect=source_dialect,
        target_dialect=target_dialect,
        error_context=error_block,
    )

    response = _get_client().chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sql},
        ],
        temperature=0.1,
    )

    result = response.choices[0].message.content.strip()
    if result.startswith("```"):
        lines = result.splitlines()
        result = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return result.strip()
