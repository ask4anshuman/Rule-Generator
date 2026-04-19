from __future__ import annotations

import logging
from pathlib import Path

from src.core.prompt_builder import build_messages
from src.llm import get_llm_client
from src.models.rule_config import RuleInput

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def generate_rule(rule: RuleInput) -> str:
    """
    Core orchestration:
      1. Build the LLM message list.
      2. Call the configured LLM.
      3. Return the generated rule text.
    """
    messages = build_messages(rule)

    client = get_llm_client()
    logger.info("Calling LLM for rule: %s", rule.rule_name)
    generated = client.generate(messages)
    logger.info("Rule generated successfully.")
    return generated.strip()


def save_rule(rule_name: str, content: str) -> Path:
    """
    Persist *content* to output/<rule_name>.sql.
    Creates the output directory if it does not exist.
    Returns the path of the saved file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = rule_name.replace(" ", "_")
    if not safe_name.endswith(".sql"):
        safe_name += ".sql"

    output_path = OUTPUT_DIR / safe_name
    output_path.write_text(content, encoding="utf-8")
    logger.info("Rule saved to: %s", output_path)
    return output_path
