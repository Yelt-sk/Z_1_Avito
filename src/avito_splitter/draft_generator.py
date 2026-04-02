from __future__ import annotations

from .models import Draft, Item, Microcategory
from .prompts import build_draft_prompt
from .qwen_client import QwenClient


class DraftGenerator:
    def __init__(self, qwen_client: QwenClient) -> None:
        self.qwen_client = qwen_client

    def generate(
        self,
        item: Item,
        microcategory: Microcategory,
        rationale: str,
        *,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> tuple[Draft, dict]:
        prompt = build_draft_prompt(item, microcategory, rationale)
        payload, meta = self.qwen_client.generate_json(prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
        if isinstance(payload, list):
            payload = next((row for row in payload if isinstance(row, dict)), {})
        if not isinstance(payload, dict):
            payload = {}
        text = str(payload.get("text", "")).strip()
        if not text:
            text = self._fallback_text(item.description, microcategory.mc_title)
        return Draft(mc_id=microcategory.mc_id, mc_title=microcategory.mc_title, text=text), meta

    @staticmethod
    def _fallback_text(description: str, mc_title: str) -> str:
        cleaned = description.strip().replace("\n", " ")
        if len(cleaned) > 240:
            cleaned = cleaned[:237].rstrip() + "..."
        return f"{mc_title}. {cleaned}"
