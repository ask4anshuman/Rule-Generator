from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Known Loader DML actions. Extended as new actions are introduced.
KNOWN_ACTIONS: list[str] = [
    "APPEND",
    "REPLACE",
    "EXPIRE",
    "TRANSACTIONAL APPEND",
    "TRANSACTIONAL REPLACE",
]


class Parameter(BaseModel):
    """
    A Loader source parameter.

    Appears in the rule as:
        rule(PROCESS, OPERATION, '@PROCESS.NAME', 'DEFAULT_VALUE')

    The word PROCESS in the key path is the same string as the rule's
    PROCESS argument (argument 1 of every rule() call).
    """

    name: str = Field(..., description="Parameter name (without @PROCESS. prefix)")
    default_value: str = Field(..., description="Default / example value for this parameter")

    @field_validator("name", "default_value", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ColumnMapping(BaseModel):
    """
    Maps a target table column to a source expression.

    Appears in the rule as:
        rule(PROCESS, OPERATION, '[CONTAINER].[TARGET_COL]', 'SOURCE_EXPR')
    """

    target_column: str = Field(..., description="Target table column name")
    source_expression: str = Field(..., description="Source column name or SQL expression")

    @field_validator("target_column", "source_expression", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ContainerConfig(BaseModel):
    """
    Configuration for a single container (target table) within a rule.

    One container produces a complete block of rule() entries in order:
        %[ACTION] -> %[SOURCE] -> [CONTAINER] -> [CONTAINER].[COL] mappings
    """

    container_name: str = Field(
        ..., description="Short tag used in key paths, e.g. CONTAINER -> '[CONTAINER]'"
    )
    target_table: str = Field(
        ..., description="Actual table name that [CONTAINER] resolves to"
    )
    action: str = Field(
        ..., description="Loader DML action (e.g. APPEND, REPLACE, EXPIRE)"
    )
    source_sql: str = Field(
        ..., description="Full source SQL query (may reference @PROCESS.PARAM)"
    )
    scope_sql: Optional[str] = Field(
        default=None,
        description="SQL scoping the target rows for REPLACE action (required when action=REPLACE)",
    )
    column_mappings: list[ColumnMapping] = Field(
        default_factory=list,
        description="Target-to-source column mappings",
    )

    @field_validator("container_name", "target_table", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @field_validator("source_sql", mode="before")
    @classmethod
    def strip_sql(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def scope_required_for_replace(self) -> "ContainerConfig":
        if self.action.upper() == "REPLACE" and not (self.scope_sql or "").strip():
            raise ValueError(
                "scope_sql is required when action is REPLACE. "
                "Provide the SQL that scopes the target rows to be replaced."
            )
        return self


class RuleInput(BaseModel):
    """All inputs required to generate a Loader rule."""

    # Tool-internal — used as output filename only
    rule_name: str = Field(..., description="Output filename (saved to output/)")

    # Loader identifiers — argument 1 & 2 in every rule() call
    process: str = Field(..., description="PROCESS argument for all rule() calls")
    operation: str = Field(..., description="OPERATION argument for all rule() calls")

    # persist_rules() metadata
    created_by: str = Field(..., description="Email / ID of the rule author")
    comments: str = Field(..., description="Human-readable description of the rule set")

    # Shared source parameters — declared once at top, referenced in any container's SQL
    parameters: list[Parameter] = Field(
        default_factory=list,
        description="Source parameters declared as @PROCESS.PARAM_NAME in key paths",
    )

    # Ordered list of containers (target tables) for this rule
    containers: list[ContainerConfig] = Field(
        default_factory=list,
        description="Ordered list of container configurations",
    )

    # Reserved for future %[KEY] modifiers and other Loader features
    extra_params: Optional[dict[str, str]] = Field(
        default=None,
        description="Future: additional key-value parameters for new Loader features",
    )

    @field_validator("rule_name", "process", "operation", "created_by", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

class ContainerConfig(BaseModel):
    container_name: str        # Short ID used in key path: [ORDERS], [CUSTOMERS], etc.
    target_table: str          # The actual table name that [CONTAINER] resolves to
    action: str
    source_sql: str
    scope_sql: Optional[str] = None
    column_mappings: list[ColumnMapping] = Field(default_factory=list)

    @model_validator(mode="after")
    def scope_required_for_replace(self) -> "ContainerConfig":
        if self.action.upper() == "REPLACE" and not (self.scope_sql or "").strip():
            raise ValueError("scope_sql is required when action is REPLACE.")
        return self

class RuleInput(BaseModel):
    rule_name: str
    process: str
    operation: str
    created_by: str
    comments: str
    parameters: list[Parameter] = Field(default_factory=list)   # shared/global
    containers: list[ContainerConfig] = Field(default_factory=list)  # ordered
    extra_params: Optional[dict[str, str]] = None
