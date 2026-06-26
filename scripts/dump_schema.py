#!/usr/bin/env python3
"""Dump the MissionSpec JSON schema to a file.

Usage:
    python scripts/dump_schema.py [output_path]

Defaults to schemas/mission.schema.json.
"""

import json
import sys
from pathlib import Path

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dcs_agentic.schemas import MissionSpec


def main(output_path: str | None = None) -> str:
    if output_path is None:
        output_path = str(Path(__file__).resolve().parent.parent / "src" / "dcs_agentic" / "schemas" / "mission.schema.json")

    schema = MissionSpec.model_json_schema()
    Path(output_path).write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Schema written to {output_path}")
    return output_path


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)