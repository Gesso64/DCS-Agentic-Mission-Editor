"""Phase 12: CLI subcommands and bundled examples."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from dcs_agentic.cli import inspect as cli_inspect
from dcs_agentic.cli import list_catalog as cli_list
from dcs_agentic.pipeline import MissionAssembler
from dcs_agentic.schemas import MissionSpec


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


# ─── Examples build ───────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["cap.json", "strike_with_sead.json", "carrier_ops.json",
                                  "capabilities_demo.json", "multirole_f16.json", "cas_sa6_gauntlet.json"])
def test_example_builds(tmp_path, name):
    """Every bundled example must build cleanly (no error issues)."""
    data = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    spec = MissionSpec.model_validate(data)
    asm = MissionAssembler(spec)
    out = tmp_path / name.replace(".json", ".miz")
    asm.save(str(out))
    assert out.exists() and out.stat().st_size > 0
    # Examples may include CARRIER_OPS_PARTIAL warnings (intentional).
    fatal = [i for i in asm.report.issues
             if i.severity.value == "error"]
    assert not fatal, f"Example '{name}' produced errors: {[i.code for i in fatal]}"


# ─── inspect subcommand ──────────────────────────────────────────────────


def test_inspect_summary_runs_on_json(capsys):
    args = type("A", (), {"input": str(EXAMPLES / "cap.json"), "json": False})()
    cli_inspect.run(args)
    out = capsys.readouterr().out
    assert "Batumi CAP" in out
    assert "Eagle 1" in out
    assert "Flights" in out


def test_inspect_json_dump(capsys):
    args = type("A", (), {"input": str(EXAMPLES / "cap.json"), "json": True})()
    cli_inspect.run(args)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["name"] == "Batumi CAP"


def test_inspect_missing_file_exits(capsys):
    args = type("A", (), {"input": "/no/such/path.json", "json": False})()
    with pytest.raises(SystemExit):
        cli_inspect.run(args)


# ─── list subcommand ─────────────────────────────────────────────────────


def test_list_aircraft_by_role(capsys):
    args = type("A", (), {"what": "aircraft", "role": "cap",
                          "aircraft": None, "theatre": None})()
    cli_list.run(args)
    out = capsys.readouterr().out
    assert "F/A-18C" in out or "F-15C" in out


def test_list_payloads_for_aircraft(capsys):
    args = type("A", (), {"what": "payloads", "role": None,
                          "aircraft": "F/A-18C", "theatre": None})()
    cli_list.run(args)
    out = capsys.readouterr().out
    assert "CAP A-A" in out


def test_list_theatres(capsys):
    args = type("A", (), {"what": "theatres", "role": None,
                          "aircraft": None, "theatre": None})()
    cli_list.run(args)
    out = capsys.readouterr().out
    assert "Caucasus" in out


def test_list_callsigns(capsys):
    args = type("A", (), {"what": "callsigns", "role": None,
                          "aircraft": None, "theatre": None})()
    cli_list.run(args)
    out = capsys.readouterr().out
    assert "AWACS" in out
    assert "Overlord" in out


# ─── --help end-to-end ───────────────────────────────────────────────────


def test_cli_help_lists_all_subcommands():
    result = subprocess.run(
        [sys.executable, "-m", "dcs_agentic", "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    for sub in ("build", "design", "edit", "campaign", "validate",
                "inspect", "list"):
        assert sub in result.stdout


def test_cli_version_flag():
    result = subprocess.run(
        [sys.executable, "-m", "dcs_agentic", "--version"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0
    assert "dcs-agentic" in result.stdout
