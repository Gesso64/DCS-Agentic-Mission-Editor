#!/usr/bin/env python3
"""Interactive setup for DCS Agentic Mission Editor.

Run from the project root:
    python install.py          # full interactive menu
    python install.py --mcp    # install MCP server + choose AI host
    python install.py --all    # install everything (mcp + agents + gui + dev)
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
IS_WINDOWS = platform.system() == "Windows"

# ── Helpers ──────────────────────────────────────────────────────────────────

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Windows terminals support ANSI in Win10+; enable it if needed.
if IS_WINDOWS:
    os.system("")  # enables ANSI escape processing


def banner(text: str) -> None:
    print(f"\n{CYAN}{BOLD}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{RESET}\n")


def step(n: int, total: int, text: str) -> None:
    print(f"{GREEN}[{n}/{total}]{RESET} {text}")


def warn(text: str) -> None:
    print(f"{YELLOW}  WARNING: {text}{RESET}")


def fail(text: str) -> None:
    print(f"\n{RED}ERROR: {text}{RESET}")
    if IS_WINDOWS:
        input("\nPress Enter to exit...")
    sys.exit(1)


def ok(text: str) -> None:
    print(f"{GREEN}  {text}{RESET}")


def run(cmd: list[str], label: str) -> None:
    """Run a subprocess; fail hard on error."""
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        fail(f"{label} failed (exit code {result.returncode}). See output above.")


# ── Detection ────────────────────────────────────────────────────────────────

def _importable(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


EXTRA_MODULES = {
    "mcp": "mcp",
    "agents": "anthropic",
    "gui": "PySide6",
    "dev": "pytest",
}


def detect_extras() -> dict[str, bool]:
    """Check which optional extras are already importable."""
    return {name: _importable(mod) for name, mod in EXTRA_MODULES.items()}


def detect_package() -> bool:
    return _importable("dcs_agentic")


def _host_config_path(host_flag: str) -> Path | None:
    """Return the config file path for a given host flag, or None."""
    paths = {
        "claude-desktop": (
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
            if IS_WINDOWS
            else Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        ),
        "claude-code": Path.home() / ".claude.json",
        "claude-code-project": PROJECT_DIR / ".mcp.json",
        "cursor": Path.home() / ".cursor" / "mcp.json",
        "cursor-project": PROJECT_DIR / ".cursor" / "mcp.json",
        "windsurf": Path.home() / ".codeium" / "windsurf" / "mcp_config.json",
        "zed": Path.home() / ".config" / "zed" / "settings.json",
    }
    return paths.get(host_flag)


def detect_mcp_registered(host_flag: str) -> bool:
    """Check whether dcs-agentic is already in the host's MCP config."""
    path = _host_config_path(host_flag)
    if path is None or not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    key = "context_servers" if host_flag == "zed" else "mcpServers"
    servers = data.get(key, {})
    return "dcs-agentic" in servers


def status_tag(done: bool, label_if_done: str = "installed") -> str:
    if done:
        return f"{GREEN}({label_if_done}){RESET}"
    return f"{DIM}(not yet){RESET}"


# ── Host picker (shared by interactive and quick paths) ──────────────────────

def prompt_host() -> str:
    """Ask the user to pick an AI host. Returns a HOST_FLAGS value."""
    # Default to the first already-registered host, or 0 if none
    registered = [detect_mcp_registered(f) for f in HOST_FLAGS]
    default_idx = next((i for i, r in enumerate(registered) if r), 0)

    host_display = []
    for i, label in enumerate(HOST_CHOICES):
        tag = f" {GREEN}(registered){RESET}" if registered[i] else ""
        host_display.append(f"{label}{tag}")

    idx = prompt_choice("Which AI host?", host_display, default=default_idx)
    return HOST_FLAGS[idx]


# ── Prompt helpers ───────────────────────────────────────────────────────────

def prompt_choice(prompt: str, options: list[str], default: int = 0) -> int:
    """Ask the user to pick from a numbered list. Returns the index."""
    print(f"{BOLD}{prompt}{RESET}")
    for i, opt in enumerate(options):
        marker = f"{CYAN}>{RESET}" if i == default else " "
        print(f"  {marker} {i + 1}) {opt}")
    print()
    while True:
        raw = input(f"  Choice [{default + 1}]: ").strip()
        if raw == "":
            return default
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except ValueError:
            pass
        print(f"  {DIM}Enter a number 1-{len(options)}{RESET}")


def prompt_yn(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"  {prompt} [{hint}]: ").strip().lower()
        if raw == "":
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False


# ── Checks ───────────────────────────────────────────────────────────────────

def check_python() -> None:
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        fail(f"Python 3.11+ is required. You have {major}.{minor}.")
    ok(f"Python {major}.{minor} ({PYTHON})")


# ── Main flow ────────────────────────────────────────────────────────────────

HOST_CHOICES = [
    "Claude Desktop",
    "Claude Code (global)",
    "Claude Code (this project only)",
    "Cursor (global)",
    "Cursor (this project only)",
    "Windsurf",
    "Zed",
]
HOST_FLAGS = [
    "claude-desktop",
    "claude-code",
    "claude-code-project",
    "cursor",
    "cursor-project",
    "windsurf",
    "zed",
]


def do_pip_install(extras: list[str]) -> None:
    spec = ",".join(extras) if extras else ""
    tag = f"[{spec}]" if spec else ""
    step(1, 2, f"Installing dcs-agentic{tag}...")
    cmd = [PYTHON, "-m", "pip", "install", "-e", f".{tag}", "--quiet"]
    run(cmd, "pip install")
    ok("Package installed.")


def do_mcp_register(host_flag: str) -> None:
    step(2, 2, f"Registering MCP server ({host_flag})...")
    run([PYTHON, "-m", "dcs_agentic", "setup", "--host", host_flag], "MCP setup")
    ok("MCP server registered.")


def interactive_setup() -> None:
    banner("DCS Agentic Mission Editor - Setup")
    check_python()

    # ── Detect current state ──
    pkg_ok = detect_package()
    extras_ok = detect_extras()
    print()
    if pkg_ok:
        ok("dcs-agentic package is already installed.")
    else:
        warn("dcs-agentic package is not installed yet.")

    # ── What to install ──
    print()
    print(f"{BOLD}What would you like to set up?{RESET}")
    print()

    want_mcp = prompt_yn(
        f"MCP server (connect to AI host)? {status_tag(extras_ok['mcp'])}",
        default=not extras_ok["mcp"],  # default No if already installed
    )
    want_agents = prompt_yn(
        f"Bundled agents (design/edit/campaign via API)? {status_tag(extras_ok['agents'])}",
        default=not extras_ok["agents"],
    )
    want_gui = prompt_yn(
        f"Chat GUI (PySide6 desktop app)? {status_tag(extras_ok['gui'])}",
        default=not extras_ok["gui"],
    )
    want_dev = prompt_yn(
        f"Developer tools (pytest)? {status_tag(extras_ok['dev'])}",
        default=not extras_ok["dev"],
    )

    # ── Which host for MCP ──
    host_flag = HOST_FLAGS[0]
    if want_mcp:
        print()
        host_flag = prompt_host()

    # ── Figure out what actually needs doing ──
    extras_to_install = []
    for name in ("mcp", "agents", "gui", "dev"):
        want = locals()[f"want_{'mcp' if name == 'mcp' else name}"]
        if want and not extras_ok[name]:
            extras_to_install.append(name)

    mcp_already = want_mcp and detect_mcp_registered(host_flag)
    nothing_to_do = not extras_to_install and (not want_mcp or mcp_already)

    # ── Summary ──
    extras_str = ", ".join(extras_to_install) if extras_to_install else "(none)"

    print()
    print(f"{BOLD}Setup plan:{RESET}")
    if extras_to_install:
        print(f"  pip install -e .[{extras_str}]")
    if want_mcp and not mcp_already:
        print(f"  Register MCP server with: {host_flag}")
    if want_mcp and mcp_already:
        print(f"  MCP server with {host_flag}: {GREEN}already registered{RESET}")
    if nothing_to_do:
        print(f"  {GREEN}Everything you selected is already set up.{RESET}")
        print()
        return

    # Show what's already done
    for name in ("mcp", "agents", "gui", "dev"):
        want = locals()[f"want_{'mcp' if name == 'mcp' else name}"]
        if want and extras_ok[name] and name not in extras_to_install:
            print(f"  {name}: {GREEN}already installed, skipping{RESET}")
    print()

    if not prompt_yn("Proceed?", default=True):
        print("Cancelled.")
        return

    # ── Execute ──
    banner("Installing")
    if extras_to_install:
        do_pip_install(extras_to_install)
    else:
        ok("No new packages to install.")

    if want_mcp and not mcp_already:
        do_mcp_register(host_flag)
    elif want_mcp and mcp_already:
        ok(f"MCP server already registered with {host_flag}.")

    # ── Done ──
    banner("Setup Complete!")
    if want_mcp:
        print(f"  Next steps:")
        print(f"    - Restart your AI host to pick up the new MCP server.")
        if host_flag == "claude-desktop":
            print(f"    - Fully quit and relaunch Claude Desktop (Ctrl+Q / Cmd+Q).")
        elif "claude-code" in host_flag:
            print(f"    - Run {CYAN}claude mcp list{RESET} to verify.")
        print()
    if want_gui:
        print(f"  Launch the GUI with:")
        print(f"    {CYAN}python start-mission-gui.py{RESET}")
        print()
    if want_dev:
        print(f"  Run tests with:")
        print(f"    {CYAN}pytest tests/{RESET}")
        print()


def quick_setup(extras: list[str], host_flag: str | None) -> None:
    """Path for --mcp / --all flags. Prompts for host if not specified."""
    banner("DCS Agentic Mission Editor - Setup")
    check_python()

    # If MCP is requested but no host was given, ask now
    if "mcp" in extras and host_flag is None:
        print()
        host_flag = prompt_host()
        print()

    extras_ok = detect_extras()
    to_install = [e for e in extras if not extras_ok.get(e, False)]
    mcp_already = host_flag is not None and detect_mcp_registered(host_flag)

    if not to_install and (host_flag is None or mcp_already):
        banner("Already set up!")
        for e in extras:
            print(f"  {e}: {GREEN}already installed{RESET}")
        if mcp_already:
            print(f"  MCP ({host_flag}): {GREEN}already registered{RESET}")
        print()
        return

    banner("Installing")
    if to_install:
        do_pip_install(to_install)
    else:
        ok("No new packages to install.")
    if host_flag and not mcp_already:
        do_mcp_register(host_flag)
    elif mcp_already:
        ok(f"MCP server already registered with {host_flag}.")

    banner("Setup Complete!")
    if host_flag:
        print(f"  Restart your AI host to pick up the MCP server.")
        if host_flag == "claude-desktop":
            print(f"  Fully quit and relaunch Claude Desktop.")
        elif "claude-code" in host_flag:
            print(f"  Run {CYAN}claude mcp list{RESET} to verify.")


# ── Entrypoint ───────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    if "--mcp" in args:
        quick_setup(["mcp"], None)
        return

    if "--all" in args:
        quick_setup(["mcp", "agents", "gui", "dev"], None)
        return

    try:
        interactive_setup()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    except EOFError:
        print("\nCancelled.")
        sys.exit(0)

    if IS_WINDOWS:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
