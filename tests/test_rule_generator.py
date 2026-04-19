from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.prompt_builder import build_messages
from src.core.rule_generator import generate_rule, save_rule
from src.core.validator import check_missing_mandatory, detect_parameters_from_sql, validate_rule_input
from src.loaders.prototype_loader import Prototype, load_prototypes
from src.models.rule_config import ColumnMapping, ContainerConfig, Parameter, RuleInput


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def minimal_rule() -> RuleInput:
    return RuleInput(
        rule_name="TEST_RULE",
        process="MY_PROCESS",
        operation="MY_OPERATION",
        created_by="dev@example.com",
        comments="Test rule for unit tests",
        parameters=[Parameter(name="COB_DATE", default_value="20260101")],
        containers=[
            ContainerConfig(
                container_name="CUSTOMER",
                target_table="DWH_CUSTOMER",
                action="APPEND",
                source_sql="SELECT CUST_ID, CUST_NAME FROM STG_CUSTOMER WHERE COB = @MY_PROCESS.COB_DATE",
                column_mappings=[
                    ColumnMapping(target_column="CUSTOMER_ID", source_expression="CUST_ID"),
                    ColumnMapping(target_column="CUSTOMER_NAME", source_expression="CUST_NAME"),
                ],
            )
        ],
    )


@pytest.fixture
def replace_rule() -> RuleInput:
    return RuleInput(
        rule_name="REPLACE_RULE",
        process="MY_PROCESS",
        operation="MY_OPERATION",
        created_by="dev@example.com",
        comments="Test REPLACE rule",
        containers=[
            ContainerConfig(
                container_name="CUSTOMER",
                target_table="DWH_CUSTOMER",
                action="REPLACE",
                scope_sql="SELECT CUST_ID FROM DWH_CUSTOMER WHERE COB = '20260101'",
                source_sql="SELECT CUST_ID, CUST_NAME FROM STG_CUSTOMER WHERE COB = '20260101'",
                column_mappings=[
                    ColumnMapping(target_column="CUSTOMER_ID", source_expression="CUST_ID"),
                ],
            )
        ],
    )


# ── prototype_loader tests ────────────────────────────────────────────────────

class TestPrototypeLoader:
    def test_load_from_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        result = load_prototypes(tmp_path)
        assert result == []

    def test_load_from_nonexistent_dir_returns_empty(self) -> None:
        result = load_prototypes(Path("/nonexistent/path/xyz"))
        assert result == []

    def test_loads_sql_files(self, tmp_path: Path) -> None:
        (tmp_path / "rule1.sql").write_text("SELECT 1;", encoding="utf-8")
        (tmp_path / "rule2.sql").write_text("SELECT 2;", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("ignore me", encoding="utf-8")

        result = load_prototypes(tmp_path)
        assert len(result) == 2
        filenames = {p.filename for p in result}
        assert filenames == {"rule1.sql", "rule2.sql"}

    def test_ignores_empty_sql_files(self, tmp_path: Path) -> None:
        (tmp_path / "empty.sql").write_text("   \n  ", encoding="utf-8")
        result = load_prototypes(tmp_path)
        assert result == []

    def test_loads_nested_sql_files(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.sql").write_text("SELECT 3;", encoding="utf-8")
        result = load_prototypes(tmp_path)
        assert len(result) == 1
        assert result[0].filename == "nested.sql"


# ── validator tests ───────────────────────────────────────────────────────────

class TestValidator:
    def test_valid_data_returns_rule(self, minimal_rule: RuleInput) -> None:
        rule, errors = validate_rule_input(minimal_rule.model_dump())
        assert rule is not None
        assert errors == []

    def test_missing_action_returns_error(self) -> None:
        data = {
            "rule_name": "X",
            "process": "P",
            "operation": "O",
            "created_by": "x@x.com",
            "comments": "test",
            "containers": [
                {"container_name": "C", "target_table": "T", "source_sql": "SELECT 1"},
            ],
        }
        rule, errors = validate_rule_input(data)
        assert rule is None
        assert any("action" in e for e in errors)

    def test_check_missing_mandatory_all_present(self, minimal_rule: RuleInput) -> None:
        missing = check_missing_mandatory(minimal_rule.model_dump())
        assert missing == []

    def test_check_missing_mandatory_detects_empty_strings(self) -> None:
        data = {
            "rule_name": "",
            "process": "P",
            "operation": "O",
            "created_by": "x@x.com",
            "containers": [
                {"container_name": "C", "target_table": "", "action": "APPEND", "source_sql": "SELECT 1"},
            ],
        }
        missing = check_missing_mandatory(data)
        assert "rule_name" in missing
        assert "containers[0].target_table" in missing

    def test_missing_scope_for_replace(self) -> None:
        data = {
            "rule_name": "X",
            "process": "P",
            "operation": "O",
            "created_by": "x@x.com",
            "comments": "test",
            "containers": [
                {"container_name": "C", "target_table": "T", "action": "REPLACE", "source_sql": "SELECT 1"},
            ],
        }
        rule, errors = validate_rule_input(data)
        assert rule is None
        assert any("scope_sql" in e for e in errors)

    def test_replace_with_scope_is_valid(self) -> None:
        data = {
            "rule_name": "X",
            "process": "P",
            "operation": "O",
            "created_by": "x@x.com",
            "comments": "test",
            "containers": [
                {
                    "container_name": "C",
                    "target_table": "T",
                    "action": "REPLACE",
                    "scope_sql": "SELECT ID FROM T WHERE COB = '20260101'",
                    "source_sql": "SELECT 1",
                }
            ],
        }
        rule, errors = validate_rule_input(data)
        assert rule is not None
        assert errors == []

    def test_check_missing_scope_for_replace(self) -> None:
        data = {
            "rule_name": "X", "process": "P", "operation": "O",
            "created_by": "x@x.com",
            "containers": [
                {"container_name": "C", "target_table": "T", "action": "REPLACE", "source_sql": "SELECT 1"},
            ],
        }
        missing = check_missing_mandatory(data)
        assert "containers[0].scope_sql" in missing


# ── detect_parameters_from_sql tests ──────────────────────────────────────────

class TestDetectParameters:
    def test_single_param_detected(self) -> None:
        result = detect_parameters_from_sql("MY_PROC", "WHERE COB = @MY_PROC.COB_DATE")
        assert result == ["COB_DATE"]

    def test_multiple_params_detected(self) -> None:
        sql = "WHERE COB = @MY_PROC.COB_DATE AND REGION = @MY_PROC.REGION"
        result = detect_parameters_from_sql("MY_PROC", sql)
        assert "COB_DATE" in result
        assert "REGION" in result
        assert len(result) == 2

    def test_duplicate_params_deduplicated(self) -> None:
        sql = "@MY_PROC.COB_DATE AND @MY_PROC.COB_DATE"
        result = detect_parameters_from_sql("MY_PROC", sql)
        assert result == ["COB_DATE"]

    def test_different_process_not_detected(self) -> None:
        result = detect_parameters_from_sql("PROC_A", "WHERE X = @PROC_B.PARAM")
        assert result == []

    def test_no_params_returns_empty(self) -> None:
        result = detect_parameters_from_sql("MY_PROC", "SELECT * FROM STG_TABLE")
        assert result == []

    def test_case_insensitive_detection(self) -> None:
        result = detect_parameters_from_sql("my_proc", "WHERE X = @MY_PROC.COB_DATE")
        assert result == ["COB_DATE"]


# ── prompt_builder tests ──────────────────────────────────────────────────────

class TestPromptBuilder:
    def test_returns_list_of_messages(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        assert isinstance(messages, list)
        assert len(messages) >= 2

    def test_first_message_is_system(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        assert messages[0].role == "system"

    def test_rule_name_in_task_message(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        combined = " ".join(m.content for m in messages)
        assert "TEST_RULE" in combined

    def test_process_and_operation_in_task_message(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        combined = " ".join(m.content for m in messages)
        assert "MY_PROCESS" in combined
        assert "MY_OPERATION" in combined

    def test_parameter_in_task_message(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        combined = " ".join(m.content for m in messages)
        assert "COB_DATE" in combined

    def test_scope_sql_in_task_message(self, replace_rule: RuleInput) -> None:
        messages = build_messages(replace_rule)
        combined = " ".join(m.content for m in messages)
        assert "SCOPE" in combined
        assert "DWH_CUSTOMER" in combined

    def test_last_message_is_user(self, minimal_rule: RuleInput) -> None:
        messages = build_messages(minimal_rule)
        assert messages[-1].role == "user"


# ── rule_generator (save) tests ───────────────────────────────────────────────

class TestSaveRule:
    def test_saves_to_output_dir(self, tmp_path: Path) -> None:
        with patch("src.core.rule_generator.OUTPUT_DIR", tmp_path):
            path = save_rule("MY_RULE", "-- generated content")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == "-- generated content"

    def test_appends_sql_extension(self, tmp_path: Path) -> None:
        with patch("src.core.rule_generator.OUTPUT_DIR", tmp_path):
            path = save_rule("NO_EXT", "-- content")
        assert path.suffix == ".sql"

    def test_does_not_double_extension(self, tmp_path: Path) -> None:
        with patch("src.core.rule_generator.OUTPUT_DIR", tmp_path):
            path = save_rule("RULE.sql", "-- content")
        assert path.name == "RULE.sql"


# ── generate_rule (mocked LLM) tests ─────────────────────────────────────────

class TestGenerateRule:
    def test_calls_llm_and_returns_output(self, minimal_rule: RuleInput) -> None:
        mock_client = MagicMock()
        mock_client.generate.return_value = "-- GENERATED RULE\nSELECT 1;"

        with patch("src.core.rule_generator.get_llm_client", return_value=mock_client):
            result = generate_rule(minimal_rule)

        assert result == "-- GENERATED RULE\nSELECT 1;"
        mock_client.generate.assert_called_once()

    def test_strips_whitespace_from_output(self, minimal_rule: RuleInput) -> None:
        mock_client = MagicMock()
        mock_client.generate.return_value = "  \n-- RULE\n  "

        with patch("src.core.rule_generator.get_llm_client", return_value=mock_client):
            result = generate_rule(minimal_rule)

        assert result == "-- RULE"
