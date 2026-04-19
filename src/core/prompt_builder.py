from __future__ import annotations

from pathlib import Path
from textwrap import indent

from src.llm.client import Message
from src.models.rule_config import ContainerConfig, RuleInput

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[2] / "templates" / "system_prompt.txt"


def _load_system_prompt() -> str:
    if _SYSTEM_PROMPT_PATH.exists():
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    return "You are an expert at generating Loader ETL rules."


def _format_parameters(rule: RuleInput) -> str:
    if not rule.parameters:
        return "  (none)"
    return "\n".join(
        f"  @{rule.process}.{p.name}  ->  default: '{p.default_value}'"
        for p in rule.parameters
    )


def _format_column_mappings(container: ContainerConfig) -> str:
    if not container.column_mappings:
        return "  (not provided -- derive from SELECT columns in SOURCE SQL; key path format: '[CONTAINER].[COL_NAME]' where COL_NAME is UPPERCASE and in square brackets, value is the lowercase column alias)"
    return "\n".join(
        f"  [{container.container_name}].[{cm.target_column}]  ->  '{cm.source_expression}'"
        for cm in container.column_mappings
    )


def _format_container_block(container: ContainerConfig, index: int) -> str:
    scope_section = ""
    if container.action.upper() == "REPLACE" and container.scope_sql:
        scope_section = (
            f"\n  SCOPE SQL (for %[SCOPE] key path -- runs on target table):\n"
            f"{indent(container.scope_sql, '    ')}\n"
        )
    return (
        f"CONTAINER {index}: [{container.container_name}]\n"
        f"  ACTION       : {container.action}\n"
        f"  TARGET TABLE : {container.target_table}{scope_section}\n"
        f"  SOURCE SQL:\n{indent(container.source_sql, '    ')}\n\n"
        f"  COLUMN MAPPINGS:\n{_format_column_mappings(container)}"
    )


def _format_extra_params(rule: RuleInput) -> str:
    if not rule.extra_params:
        return "  (none)"
    return "\n".join(f"  {k}: {v}" for k, v in rule.extra_params.items())


def _format_user_task(rule: RuleInput) -> str:
    containers_section = "\n\n".join(
        _format_container_block(c, i + 1) for i, c in enumerate(rule.containers)
    )

    return f"""
Generate a Loader rule with the following specifications:

OUTPUT FILE     : {rule.rule_name}
PROCESS         : {rule.process}
OPERATION       : {rule.operation}
CREATED BY      : {rule.created_by}
COMMENTS        : {rule.comments}

PARAMETERS (shared -- declared as @{rule.process}.NAME in rule() key paths):
{_format_parameters(rule)}

{containers_section}

EXTRA PARAMETERS:
{_format_extra_params(rule)}
""".strip()


def build_messages(rule: RuleInput) -> list[Message]:
    """
    Assemble the full message list to send to the LLM.

    System message : Loader framework description + output instructions
    User message   : The rule generation task
    """
    system_text = _load_system_prompt()
    return [
        Message("system", system_text),
        Message("user", _format_user_task(rule)),
    ]
