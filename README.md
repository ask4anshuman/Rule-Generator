# Rule Generator

An AI-assisted CLI tool that helps developers create **Loader ETL rules** by:
- Interactively collecting all mandatory rule inputs (process, operation, containers, source SQL, etc.)
- Calling a configurable LLM to generate a well-formed, production-ready rule
- Saving the output to the `output/` folder

---

## Project Structure

```
Rule-Generator/
+-- .env                        <- your credentials (git-ignored; copy from .env.example)
+-- .env.example                <- template for all environment variables
+-- requirements.txt
+-- pyproject.toml
+-- config/
|   \-- llm_config.yaml         <- provider selection, model, temperature defaults
+-- output/                     <- generated rules are saved here
+-- templates/
|   \-- system_prompt.txt       <- LLM system instructions (update as needed)
+-- src/
|   +-- cli/
|   |   \-- main.py             <- interactive CLI entry point
|   +-- core/
|   |   +-- rule_generator.py   <- orchestration: load -> prompt -> LLM -> save
|   |   +-- prompt_builder.py   <- assembles few-shot prompt from prototypes + inputs
|   |   \-- validator.py        <- mandatory field checks before LLM call
|   +-- llm/
|   |   +-- client.py           <- generic LLM client + factory
|   |   \-- __init__.py         <- re-exports LLMClient, Message, get_llm_client
|   \-- models/
|       \-- rule_config.py      <- Pydantic models: RuleInput, Parameter, ColumnMapping
\-- tests/
    \-- test_rule_generator.py  <- unit tests (25 tests)
```

---

## Prerequisites

- Python 3.10 or higher
- pip

---

## Setup

### 1. Create and activate a virtual environment

```bash
# Windows
py -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the values for your chosen provider:

| Variable | Required for | Description |
|---|---|---|
| `LLM_API_KEY` | all | API key for your chosen provider |
| `LLM_ENDPOINT` | azure | Azure resource endpoint URL |
| `LLM_PROVIDER` | optional | Override provider set in `llm_config.yaml` |

Model, temperature, and other non-secret settings are configured in `config/llm_config.yaml`.

---

## Running the Tool

```bash
py -m src.cli.main
```

Or, if installed via `pyproject.toml`:

```bash
rule-gen
```

**Optional flags:**

| Flag | Description |
|---|---|
| `--debug` | Enable verbose debug logging |

---

## Interactive Workflow

The CLI walks you through 4 steps:

| Step | What you provide |
|---|---|
| 1 | Rule name, created by (email / ID), comments / description |
| 2 | PROCESS name, OPERATION name |
| 3 | One or more containers: container name, target table, action, source SQL (+ scope SQL if REPLACE). Repeat until all containers are added. |
| 4 | COB / filter parameters (auto-detected from source SQL; option to add more manually) |

After generation, the rule is displayed with syntax highlighting and you are prompted to save it to `output/<rule_name>.sql`.

> **Column mappings** are derived automatically from the SELECT columns in each container's source SQL — no manual entry required.

---

## Supported Actions

| Action | Description |
|---|---|
| `APPEND` | Insert new rows; never update existing ones |
| `REPLACE` | Truncate-and-reload the target partition/table |
| `EXPIRE` | Logically close (expire) existing rows matching the key |
| `TRANSACTIONAL APPEND` | Append within a transaction; rolls back on failure |
| `TRANSACTIONAL REPLACE` | Replace within a transaction; rolls back on failure |


## LLM Configuration

Non-secret settings live in `config/llm_config.yaml`. Secrets live in `.env`.

**`config/llm_config.yaml`** -- sets provider and model defaults:

```yaml
LLM_PROVIDER: openai        # openai | azure | anthropic
LLM_MODEL: gpt-4o
LLM_TEMPERATURE: 0.2
LLM_MAX_TOKENS: 4096
LLM_AZURE_API_VERSION: "2024-02-01"   # Azure only
```

To switch provider, change `LLM_PROVIDER` in the YAML or set `LLM_PROVIDER=<value>` in `.env`.

---

## Running Tests

```bash
py -m pytest tests/ -v
```

All 25 unit tests cover: prototype loading, input validation, parameter detection, prompt assembly, rule saving, and the LLM call (mocked).

---

## Updating the System Prompt

When new Loader features or rule conventions are introduced, update `templates/system_prompt.txt`.  
This file is injected as the LLM system message on every run -- no code changes needed.
