#!/usr/bin/env python3
"""
approval_loop.py — Shared approval infrastructure for COS scheduled tasks.

All scripts that need Wes approval call these functions.
Primary channel: file-based (tasks/pending-approvals.md).
M365 MCP email send is not available — file-based is the active method.

Usage:
    from approval_loop import send_approval_request, read_file_approvals

Smoke test:
    python3 scripts/approval_loop.py
"""

import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Project root = two levels up from this script
PROJECT_ROOT = Path(__file__).parent.parent
APPROVALS_FILE = PROJECT_ROOT / "tasks" / "pending-approvals.md"


def send_approval_request(items: List[Dict], task_name: str, context: str = "") -> None:
    """
    Write approval request to pending-approvals.md.

    Args:
        items: List of dicts with keys: id (int), description (str)
        task_name: Name of the calling script/task
        context: Optional context paragraph shown above items

    Example:
        send_approval_request(
            items=[
                {"id": 1, "description": "Load 247 contacts into Campaign 2 sequence"},
                {"id": 2, "description": "Skip 12 contacts already in a sequence"},
            ],
            task_name="weekly_list_build",
            context="Weekly list build found 259 new contacts. 12 excluded (already in sequence)."
        )
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"\n---\n",
        f"## {task_name} — {timestamp}\n",
    ]

    if context:
        lines.append(f"{context}\n\n")

    for item in items:
        lines.append(f"- [ ] **{item['id']}** — {item['description']}\n")

    lines.append("\n*Edit `[ ]` to `[Y]` or `[N]` and save. COS checks this file at session start.*\n")

    _append_to_approvals(lines)
    print(f"[approval_loop] Wrote {len(items)} approval request(s) to {APPROVALS_FILE}")


def read_file_approvals(task_name: str) -> Dict[int, bool]:
    """
    Parse pending-approvals.md for responses to a given task.

    Returns:
        Dict mapping item_id -> True (approved) / False (rejected)
        Only returns items with [Y] or [N] — omits still-pending [ ] items.

    Example:
        parse_approval_reply("1Y 2N 3Y") == {1: True, 2: False, 3: True}  # via string
        read_file_approvals("weekly_list_build") == {1: True, 2: False}   # via file
    """
    if not APPROVALS_FILE.exists():
        return {}

    content = APPROVALS_FILE.read_text()

    # Find the section for this task
    pattern = rf"## {re.escape(task_name)}.*?(?=\n---|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        return {}

    section = match.group(0)
    return _parse_approvals_from_section(section)


def parse_approval_reply(reply_string: str) -> Dict[int, bool]:
    """
    Parse approval reply string format: "1Y 2N 3Y"

    Returns dict of item_id -> approved (True/False).
    Ignores unrecognized tokens.

    >>> parse_approval_reply("1Y 2N 3Y")
    {1: True, 2: False, 3: True}
    >>> parse_approval_reply("1y 2n")
    {1: True, 2: False}
    """
    result = {}
    tokens = reply_string.upper().split()
    for token in tokens:
        match = re.match(r"^(\d+)([YN])$", token)
        if match:
            item_id = int(match.group(1))
            approved = match.group(2) == "Y"
            result[item_id] = approved
    return result


def _parse_approvals_from_section(section: str) -> Dict[int, bool]:
    """Parse [Y]/[N]/[ ] checkbox lines from a section of the approvals file."""
    result = {}
    for line in section.split("\n"):
        # Match: - [Y] **1** — description  or  - [N] **1** — ...
        match = re.match(r"-\s+\[([YN])\]\s+\*\*(\d+)\*\*", line)
        if match:
            status = match.group(1)
            item_id = int(match.group(2))
            result[item_id] = status == "Y"
    return result


def _append_to_approvals(lines: List[str]) -> None:
    """Append lines to the approvals file, creating it if needed."""
    APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not APPROVALS_FILE.exists():
        APPROVALS_FILE.write_text(
            "# Pending Approvals\n\n"
            "Edit `[ ]` to `[Y]` or `[N]` and save. COS checks at session start.\n\n"
        )

    with open(APPROVALS_FILE, "a") as f:
        f.writelines(lines)


# ── Smoke test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Running approval_loop smoke test...\n")

    # Test parse_approval_reply
    result = parse_approval_reply("1Y 2N 3Y")
    expected = {1: True, 2: False, 3: True}
    assert result == expected, f"parse_approval_reply failed: {result} != {expected}"
    print(f"✓ parse_approval_reply('1Y 2N 3Y') == {result}")

    result2 = parse_approval_reply("1y 2n")
    assert result2 == {1: True, 2: False}, f"Lowercase test failed: {result2}"
    print(f"✓ parse_approval_reply('1y 2n') == {result2}")

    result3 = parse_approval_reply("garbage 1Y bad 2N")
    assert result3 == {1: True, 2: False}, f"Garbage filter failed: {result3}"
    print(f"✓ parse_approval_reply handles garbage tokens: {result3}")

    # Test _parse_approvals_from_section directly (round-trip without file I/O)
    fake_section = (
        "## smoke_test — 2026-01-01 09:00\n"
        "- [Y] **1** — Test item A\n"
        "- [N] **2** — Test item B\n"
        "- [ ] **3** — Test item C (still pending)\n"
    )
    approvals = _parse_approvals_from_section(fake_section)
    assert approvals == {1: True, 2: False}, f"Section parse failed: {approvals}"
    assert 3 not in approvals, "Pending item should not be in results"
    print(f"✓ _parse_approvals_from_section: {approvals} (pending item correctly excluded)")

    print("\n✓ All smoke tests passed.")
