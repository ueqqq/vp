"""Poll logic with no Discord in it, so it can be tested properly."""

from __future__ import annotations

import re

_MARKER = re.compile(r"^\s*(?:[-•*]|\d{1,2}[.)])\s+")  # "- x", "• x", "1. x", "2) x" (not "2024 x")


def new_poll(poll_id: str, question: str, options: list[str], author: int, now: float, closes: float) -> dict:
    return {"id": poll_id, "question": question, "options": options, "author": author, "created": now,
            "closes": closes, "status": "open", "votes": {}, "channel": None, "message": None}


def cast(poll: dict, user_id: int, index: int) -> str:
    """Record or change a vote. Returns 'ok', 'changed', 'same', 'closed' or 'invalid'."""
    if poll["status"] != "open":
        return "closed"
    if not 0 <= index < len(poll["options"]):
        return "invalid"
    previous = poll["votes"].get(str(user_id))
    poll["votes"][str(user_id)] = index
    if previous is None:
        return "ok"
    return "same" if previous == index else "changed"


def tally(poll: dict) -> list[int]:
    counts = [0] * len(poll["options"])
    for index in poll["votes"].values():
        if 0 <= index < len(counts):
            counts[index] += 1
    return counts


def winners(poll: dict) -> list[int]:
    """Indexes of the leading option(s); more than one means a tie; empty means no votes."""
    counts = tally(poll)
    top = max(counts, default=0)
    return [i for i, n in enumerate(counts) if n == top] if top else []


def is_expired(poll: dict, now: float) -> bool:
    return poll["status"] == "open" and poll["closes"] is not None and now >= poll["closes"]


def close(poll: dict, now: float) -> None:
    poll["status"] = "closed"
    poll["closed_at"] = now


def parse_options(raw: str, max_options: int = 4, max_len: int = 80) -> tuple[list[str], str | None]:
    """One option per line. Returns (options, error_message_or_None)."""
    options, seen = [], set()
    for line in raw.splitlines():
        text = _MARKER.sub("", line).strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        options.append(text)
    if len(options) < 2:
        return options, "Give at least 2 different options, one per line."
    if len(options) > max_options:
        return options, f"At most {max_options} options are supported."
    if any(len(o) > max_len for o in options):
        return options, f"Each option must be {max_len} characters or fewer."
    return options, None
