from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import extract_first_json, normalize_for_cli_ascii

DEFAULT_QWEN_ROOT = Path(r"D:\LLM\Qwen 3")


@dataclass(slots=True)
class QwenSettings:
    model_name: str = "qwen3-local"
    endpoint: str = "http://127.0.0.1:8090/v1/chat/completions"
    llama_cli_path: Path = DEFAULT_QWEN_ROOT / "runtime" / "llama-cli.exe"
    model_path: Path = DEFAULT_QWEN_ROOT / "model" / "Qwen3-4B-f16-Q4_K_M.gguf"
    context_size: int = 4096
    max_tokens: int = 96
    temperature: float = 0.15
    top_p: float = 0.82
    top_k: int = 20
    timeout_seconds: int = 45
    retries: int = 1


class QwenClient:
    def __init__(self, settings: QwenSettings | None = None) -> None:
        self.settings = settings or QwenSettings()

    def generate_json(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        errors: list[str] = []
        for attempt in range(1, self.settings.retries + 1):
            try:
                response_text = self._call_http(prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
                return extract_first_json(response_text), {"transport": "http", "attempt": attempt, "rawText": response_text}
            except Exception as exc:  # noqa: BLE001
                errors.append(f"http attempt {attempt}: {exc}")

            try:
                response_text = self._call_cli(prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
                return extract_first_json(response_text), {"transport": "cli", "attempt": attempt, "rawText": response_text}
            except Exception as exc:  # noqa: BLE001
                errors.append(f"cli attempt {attempt}: {exc}")

        raise RuntimeError("Qwen call failed: " + " | ".join(errors))

    def _call_http(self, prompt: str, *, max_tokens: int | None, timeout_seconds: int | None) -> str:
        user_prompt = prompt if prompt.startswith("/no_think") else f"/no_think\n{prompt}"
        body = {
            "model": self.settings.model_name,
            "stream": False,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "top_k": self.settings.top_k,
            "max_tokens": max_tokens if max_tokens is not None else self.settings.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precision-first JSON API. "
                        "Respond with strict JSON only. "
                        "If ambiguous, prefer false and be concise."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        }
        request = urllib.request.Request(
            self.settings.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds if timeout_seconds is not None else self.settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        message = payload["choices"][0]["message"]
        content = message.get("content") or message.get("reasoning_content") or ""
        return content

    def _call_cli(self, prompt: str, *, max_tokens: int | None, timeout_seconds: int | None) -> str:
        if not self.settings.llama_cli_path.exists():
            raise FileNotFoundError(f"llama-cli not found at {self.settings.llama_cli_path}")
        if not self.settings.model_path.exists():
            raise FileNotFoundError(f"GGUF model not found at {self.settings.model_path}")

        system_prompt = (
            "You are a precision-first JSON API. "
            "Respond with strict JSON only. "
            "If ambiguous, prefer false and be concise."
        )
        user_prompt = prompt if prompt.startswith("/no_think") else f"/no_think\n{prompt}"
        full_prompt = (
            "<|im_start|>system\n"
            f"{system_prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"{user_prompt}\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        safe_prompt = normalize_for_cli_ascii(full_prompt)
        command = [
            str(self.settings.llama_cli_path),
            "-m",
            str(self.settings.model_path),
            "-c",
            str(self.settings.context_size),
            "-n",
            str(max_tokens if max_tokens is not None else self.settings.max_tokens),
            "-ngl",
            "0",
            "--temp",
            str(self.settings.temperature),
            "--top-p",
            str(self.settings.top_p),
            "--top-k",
            str(self.settings.top_k),
            "--simple-io",
            "-no-cnv",
            "-e",
            "-p",
            safe_prompt,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds if timeout_seconds is not None else self.settings.timeout_seconds,
            check=False,
        )
        output = completed.stdout.strip()
        if completed.returncode != 0 and not output:
            raise RuntimeError(completed.stderr.strip() or f"llama-cli failed with code {completed.returncode}")
        return output
