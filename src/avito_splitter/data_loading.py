from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Item, Microcategory
from .utils import ensure_list, load_json, load_jsonl


def load_microcategories(path: str | Path) -> list[Microcategory]:
    data = load_json(path)
    return [Microcategory.from_dict(row) for row in ensure_list(data)]


def load_item(path: str | Path) -> Item:
    return Item.from_dict(load_json(path))


def load_examples(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".jsonl":
        return load_jsonl(path)
    return ensure_list(load_json(path))
