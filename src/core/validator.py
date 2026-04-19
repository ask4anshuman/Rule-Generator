from __future__ import annotations

import re
from typing import Optional

from pydantic import ValidationError

from src.models.rule_config import RuleInput

_MANDATORY_RULE_FIELDS = ["rule_name", "process", "operation", "created_by"]
_MANDATORY_CONTAINER_FIELDS = ["container_name", "target_table", "action", "source_sql"]


def validate_rule_input(data: dict) -> tuple[Optional[RuleInput], list[str]]:
    """
    Validate *data* against the RuleInput model.

    Returns (RuleInput, []) on success.
    Returns (None, [error_message, ...]) on failure.
    """
    try:
        rule = RuleInput(**data)
        return rule, []
    except ValidationError as exc:
        errors: list[str] = []
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            errors.append(f"{field}: {err['msg']}")
        return None, errors


def check_missing_mandatory(data: dict) -> list[str]:
    """Return a list of mandatory field names that are missing or empty."""
    missing: list[str] = []
    for field in _MANDATORY_RULE_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    containers = data.get("containers") or []
    if not containers:
        missing.append("containers")
        return missing

    for i, container in enumerate(containers):
        cdata: dict = (
            container.model_dump() if hasattr(container, "model_dump") else container
        )
        for field in _MANDATORY_CONTAINER_FIELDS:
            value = cdata.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(f"containers[{i}].{field}")
        # scope_sql is mandatory when action is REPLACE
        if (cdata.get("action") or "").upper() == "REPLACE":
            scope = cdata.get("scope_sql")
            if scope is None or (isinstance(scope, str) and not scope.strip()):
                missing.append(f"containers[{i}].scope_sql")

    return missing


def detect_parameters_from_sql(process: str, source_sql: str) -> list[str]:
    """
    Scan *source_sql* for @PROCESS.PARAM_NAME references and return
    unique parameter names (uppercased, without the @PROCESS. prefix).

    Example:
        detect_parameters_from_sql("MY_PROC", "WHERE COB = @MY_PROC.COB_DATE")
        # -> ["COB_DATE"]
    """
    pattern = re.compile(rf'@{re.escape(process)}\.([\w]+)', re.IGNORECASE)
    # dict.fromkeys preserves insertion order and deduplicates
    seen = dict.fromkeys(m.group(1).upper() for m in pattern.finditer(source_sql))
    return list(seen)
