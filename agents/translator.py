import os
from agents.llm_client import call_qwen

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "translator.txt")


def _load_prompt() -> str:
    with open(_PROMPT_PATH, "r") as f:
        return f.read()


def translate(sql: str, source_dialect: str, target_dialect: str, error_context: list = None) -> str:
    error_block = ""
    if error_context:
        lines_text = "\n".join(f"- {e}" for e in error_context)
        error_block = f"\nPrevious translation failed validation with these issues:\n{lines_text}\nFix all of these issues in your translation.\n"

    system_prompt = _load_prompt().format(
        source_dialect=source_dialect,
        target_dialect=target_dialect,
        error_context=error_block,
    )

    result = call_qwen(system_prompt, sql)
    # Strip markdown fences if model wraps output (e.g. ```sql ... ```)
    if result.startswith("```"):
        lines = result.splitlines()
        # Skip opening fence line (may include language tag like ```sql)
        # Skip closing fence line if present
        end = -1 if lines[-1].strip() == "```" else len(lines)
        result = "\n".join(lines[1:end])
    return result.strip()
