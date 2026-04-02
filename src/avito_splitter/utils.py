from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def normalize_text(text: str) -> str:
    lowered = text.lower().replace("\u0451", "\u0435")
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    lowered = lowered.replace("_", " ")
    return re.sub(r"\s+", " ", lowered).strip()


def normalize_for_cli_ascii(text: str) -> str:
    safe = text.encode("unicode_escape").decode("ascii")
    return safe.replace('"', '\\"')


def ensure_list(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise TypeError(f"Unsupported top-level JSON type: {type(data)!r}")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def dump_json(data: Any, pretty: bool = True) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)


def extract_first_json(text: str) -> Any:
    text = text.strip()
    if not text:
        raise ValueError("Empty model response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    candidates: list[Any] = []
    for start in range(len(text)):
        opening = text[start]
        if opening not in "[{":
            continue
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    snippet = text[start : index + 1]
                    try:
                        candidates.append(json.loads(snippet))
                    except json.JSONDecodeError:
                        pass
                    break
    if not candidates:
        raise ValueError("No JSON object found in model response")
    return candidates[-1]
