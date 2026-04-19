from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PROTOTYPES_DIR = Path(__file__).resolve().parents[2] / "prototypes"


@dataclass
class Prototype:
    """A single prototype rule loaded from disk."""

    filename: str
    content: str


def load_prototypes(directory: Path = PROTOTYPES_DIR) -> list[Prototype]:
    """
    Recursively load all .sql files from *directory*.

    Returns an empty list (with a warning) if no files are found — the
    generator will still function, just without few-shot examples.
    """
    if not directory.exists():
        logger.warning("Prototypes directory not found: %s", directory)
        return []

    sql_files = sorted(directory.rglob("*.sql"))

    if not sql_files:
        logger.warning(
            "No .sql prototype files found in %s. "
            "Rule generation will proceed without few-shot examples.",
            directory,
        )
        return []

    prototypes: list[Prototype] = []
    for path in sql_files:
        try:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                prototypes.append(Prototype(filename=path.name, content=content))
                logger.debug("Loaded prototype: %s", path.name)
        except OSError as exc:
            logger.warning("Could not read prototype file %s: %s", path, exc)

    logger.info("Loaded %d prototype(s) from %s", len(prototypes), directory)
    return prototypes
