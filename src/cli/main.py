from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
import questionary
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from src.core.rule_generator import generate_rule, save_rule
from src.core.validator import check_missing_mandatory, detect_parameters_from_sql, validate_rule_input
from src.models.rule_config import KNOWN_ACTIONS, ContainerConfig, Parameter, RuleInput

load_dotenv()

console = Console()
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


# ── helpers ───────────────────────────────────────────────────────────────────


def _prompt_source_sql() -> str:
    """Prompt for a multiline SQL query, accepting blank line as terminator."""
    console.print("\n[bold cyan]Source SQL[/bold cyan]")
    console.print(
        "Paste or type your SOURCE SQL query.\n"
        "Enter a [bold]blank line[/bold] when done.\n"
    )
    lines: list[str] = []
    while True:
        line = questionary.text("  SQL> ").ask()
        if line is None:
            sys.exit(0)
        if line == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────────────


@click.command()
@click.option("--debug", is_flag=True, default=False, help="Enable debug logging.")
def cli(debug: bool) -> None:
    """AI-assisted Loader ETL Rule Generator."""

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    console.print(
        Panel.fit(
            "[bold blue]Loader Rule Generator[/bold blue]\n"
            "[dim]Powered by LLM -- provider-agnostic[/dim]",
            border_style="blue",
        )
    )

    # -- collect inputs -------------------------------------------------------
    console.print("[bold]Step 1 of 4 -- Rule Identity[/bold]\n")

    rule_name = questionary.text("Output filename (rule name):").ask()
    if rule_name is None:
        sys.exit(0)
    created_by = questionary.text("Created by (email / ID):").ask()
    if created_by is None:
        sys.exit(0)
    comments = questionary.text("Comments / description:").ask()
    if comments is None:
        sys.exit(0)

    console.print("\n[bold]Step 2 of 4 -- Loader Process & Operation[/bold]\n")

    process = questionary.text("PROCESS name:").ask()
    if process is None:
        sys.exit(0)
    operation = questionary.text("OPERATION name:").ask()
    if operation is None:
        sys.exit(0)

    console.print("\n[bold]Step 3 of 4 -- Containers[/bold]\n")
    console.print(
        "Define one or more containers (target tables) for this rule.\n"
        "Each container has its own action, source SQL, and target table.\n"
    )

    raw_containers: list[dict] = []
    container_index = 1

    while True:
        console.print(f"[bold cyan]Container {container_index}[/bold cyan]\n")

        container_name = questionary.text("  Container name (key path tag, e.g. ORDERS):").ask()
        if container_name is None:
            sys.exit(0)

        target_table = questionary.text("  Target table name:").ask()
        if target_table is None:
            sys.exit(0)

        action = questionary.select("  Action:", choices=KNOWN_ACTIONS).ask()
        if action is None:
            sys.exit(0)

        # SCOPE SQL is required for REPLACE
        container_scope_sql: str | None = None
        if action == "REPLACE":
            console.print(
                "\n  [bold cyan]SCOPE SQL[/bold cyan] [dim](required for REPLACE)[/dim]\n"
                "  This SQL runs against the [bold]target[/bold] table to scope which rows\n"
                "  will be replaced. Enter a [bold]blank line[/bold] when done.\n"
            )
            scope_lines: list[str] = []
            while True:
                line = questionary.text("    SCOPE SQL> ").ask()
                if line is None:
                    sys.exit(0)
                if line == "" and scope_lines:
                    break
                scope_lines.append(line)
            container_scope_sql = "\n".join(scope_lines)

        source_sql = _prompt_source_sql()

        raw_containers.append({
            "container_name": container_name.strip(),
            "target_table": target_table.strip(),
            "action": action,
            "scope_sql": container_scope_sql,
            "source_sql": source_sql,
            "column_mappings": [],
        })

        console.print(f"\n  [green]✔[/green] Container [{container_name.strip()}] added.\n")
        container_index += 1

        add_container = questionary.confirm("Add another container?", default=False).ask()
        if add_container is None:
            sys.exit(0)
        if not add_container:
            break

    # ── Step 4: parameters (auto-detect from all containers' SQL + manual) ───
    console.print("\n[bold]Step 4 of 4 -- Parameters[/bold]\n")
    combined_sql = "\n".join(c["source_sql"] for c in raw_containers)
    detected = detect_parameters_from_sql(process, combined_sql)
    raw_params: list[dict] = []

    if detected:
        console.print(
            f"[green]Auto-detected parameter(s) from SQL:[/green] "
            f"{', '.join(f'@{process}.{n}' for n in detected)}\n"
        )
        for name in detected:
            default = questionary.text(
                f"  Default value for @{process}.{name}:"
            ).ask()
            if default is None:
                sys.exit(0)
            raw_params.append({"name": name, "default_value": default.strip()})
    else:
        console.print("[dim]No parameters detected in the source SQL.[/dim]\n")

    add_more = questionary.confirm(
        "Add additional parameter(s) manually?", default=False
    ).ask()
    if add_more:
        while True:
            pname = questionary.text(
                f"  Parameter name for @{process}.? (blank to finish):"
            ).ask()
            if pname is None:
                sys.exit(0)
            if not pname.strip():
                break
            pdefault = questionary.text(
                f"  Default value for @{process}.{pname.strip()}:"
            ).ask()
            if pdefault is None:
                sys.exit(0)
            raw_params.append({"name": pname.strip(), "default_value": (pdefault or "").strip()})

    # ── build data dict & validate ───────────────────────────────────────────
    data: dict = {
        "rule_name": rule_name,
        "process": process,
        "operation": operation,
        "created_by": created_by,
        "comments": comments or "",
        "parameters": [Parameter(**p) for p in raw_params],
        "containers": [ContainerConfig(**c) for c in raw_containers],
    }

    missing = check_missing_mandatory(data)
    if missing:
        console.print(
            f"\n[red]✖ Missing mandatory fields:[/red] {', '.join(missing)}\n"
            "Please re-run and provide all required inputs."
        )
        sys.exit(1)

    rule_input, errors = validate_rule_input(data)
    if errors or rule_input is None:
        console.print("\n[red]✖ Validation errors:[/red]")
        for err in errors:
            console.print(f"  • {err}")
        sys.exit(1)

    # ── generate ─────────────────────────────────────────────────────────────
    console.print("\n[bold yellow]⟳  Generating rule...[/bold yellow]")

    try:
        generated = generate_rule(rule_input)
    except EnvironmentError as exc:
        console.print(f"\n[red]✖ Configuration error:[/red] {exc}")
        console.print(
            "Ensure your [bold].env[/bold] file is configured correctly "
            "(see [italic].env.example[/italic])."
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"\n[red]✖ LLM call failed:[/red] {exc}")
        sys.exit(1)

    # ── display ──────────────────────────────────────────────────────────────
    console.print()
    console.print(
        Panel(
            Syntax(generated, "sql", theme="monokai", line_numbers=True),
            title=f"[bold green]Generated Rule: {rule_name}[/bold green]",
            border_style="green",
        )
    )

    # ── save prompt ──────────────────────────────────────────────────────────
    save = questionary.confirm(
        "\nSave this rule to the output/ folder?", default=True
    ).ask()

    if save:
        output_path = save_rule(rule_name, generated)
        console.print(f"\n[green]✔[/green] Saved to [italic]{output_path}[/italic]")
    else:
        console.print("\n[dim]Rule not saved.[/dim]")


if __name__ == "__main__":
    cli()
