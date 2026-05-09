import json
import os
from agents.llm_client import call_qwen

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "optimizer.txt")


def optimize(sql: str, target_dialect: str) -> dict:
    with open(_PROMPT_PATH) as f:
        system_prompt = f.read().format(target_dialect=target_dialect)

    content = call_qwen(system_prompt, sql)

    # Strip markdown fences if model wraps JSON output
    if content.startswith("```"):
        lines = content.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        content = "\n".join(lines[1:end])

    try:
        result = json.loads(content)
        return {
            "optimized_sql": result.get("optimized_sql", sql),
            "changes": result.get("changes", []),
        }
    except json.JSONDecodeError:
        return {"optimized_sql": sql, "changes": []}
