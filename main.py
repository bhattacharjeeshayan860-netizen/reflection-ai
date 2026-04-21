#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import textwrap
from typing import Optional

from engine import run_reflection

# ── colour helpers ─────────────────────────────────────────────────────────────

USE_COLOR = True


def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def dim(t: str) -> str: return _c("2", t)
def bold(t: str) -> str: return _c("1", t)
def italic(t: str) -> str: return _c("3", t)
def cyan(t: str) -> str: return _c("36", t)
def yellow(t: str) -> str: return _c("33", t)
def white(t: str) -> str: return _c("97", t)

# ── layout ─────────────────────────────────────────────────────────────────────

WIDTH = 62
INDENT = "   "


def blank():
    print()


def ruler():
    return dim("─" * WIDTH)


def wrap(text: str, width: int = WIDTH - len(INDENT)) -> str:
    lines = text.split("\n")
    wrapped = []
    for line in lines:
        if line.strip() == "":
            wrapped.append("")
        else:
            wrapped.extend(textwrap.wrap(line, width=width) or [""])
    return "\n".join(INDENT + l for l in wrapped)


# ── custom IO for engine ───────────────────────────────────────────────────────

def styled_output(text: str) -> None:
    if text.strip() == "":
        print(text)
        return

    # basic formatting (keeps your original feel)
    if text.startswith("-----"):
        print(dim(text))
    elif text.startswith("="):
        print(bold(text))
    else:
        print(wrap(text))


def styled_input(prompt: str) -> str:
    try:
        return input(cyan(INDENT + "→ ") + prompt)
    except (EOFError, KeyboardInterrupt):
        print(dim("\nSession ended."))
        sys.exit(0)


# ── result rendering ───────────────────────────────────────────────────────────

def render_final_structured(result: dict) -> None:
    blank()
    print(bold(yellow("  ◆  STRUCTURED OUTPUT")))
    print(dim("  " + "─" * 20))
    blank()

    print(INDENT + f"axis1 → {result.get('axis1')}")
    print(INDENT + f"axis2 → {result.get('axis2')}")
    print(INDENT + f"axis3 → {result.get('axis3')}")
    print(INDENT + f"signals → {len(result.get('signals', []))} captured")

    blank()
    print(ruler())
    blank()


# ── main run ───────────────────────────────────────────────────────────────────

def main() -> None:
    global USE_COLOR

    parser = argparse.ArgumentParser(
        description="Daily Reflection Tree — deterministic reflection agent",
    )
    parser.add_argument("--plain", action="store_true")
    parser.add_argument("--no-insight", action="store_true")
    args = parser.parse_args()

    if args.plain:
        USE_COLOR = False

    try:
        result = run_reflection(
            input_fn=styled_input,
            output_fn=styled_output,
            show_final_insight=not args.no_insight,
        )

        # show structured result (new capability)
        render_final_structured(result)

    except KeyboardInterrupt:
        blank()
        print(dim("Session interrupted."))
        blank()


if __name__ == "__main__":
    main()