import json
import os
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT

_client = None
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "optimizer.txt")


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
    return _client


def optimize(sql: str, target_dialect: str) -> dict:
    with open(_PROMPT_PATH) as f:
        system_prompt = f.read().format(target_dialect=target_dialect)

    response = _get_client().chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sql},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()
    result = json.loads(content)
    return {
        "optimized_sql": result.get("optimized_sql", sql),
        "changes": result.get("changes", []),
    }
