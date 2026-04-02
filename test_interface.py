from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from avito_splitter.data_loading import load_microcategories
from avito_splitter.models import Item, PredictionResult
from avito_splitter.pipeline import AvitoSplitterPipeline, PipelineConfig
from avito_splitter.qwen_client import DEFAULT_QWEN_ROOT


MICROCATEGORIES_PATH = r"D:\projects\Avito\data\microcategories.json"
QWEN_HEALTH_URL = "http://127.0.0.1:8090/health"
LLAMA_CLI_PATH = DEFAULT_QWEN_ROOT / "runtime" / "llama-cli.exe"
MODEL_PATH = DEFAULT_QWEN_ROOT / "model" / "Qwen3-4B-f16-Q4_K_M.gguf"


class TestInterfaceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Avito Splitter Test Interface")
        self.root.geometry("1200x820")

        microcategories = load_microcategories(MICROCATEGORIES_PATH)
        self.pipeline = AvitoSplitterPipeline(microcategories, config=PipelineConfig(enable_qwen=True))
        self.microcategory_lookup = {mc.mc_id: mc.mc_title for mc in microcategories}

        self.description_var = tk.StringVar(
            value="Делаем ремонт под ключ, а также отдельно выполняем сантехнические и электромонтажные работы."
        )
        self.source_mc_var = tk.StringVar(value="201")
        self.source_mc_title_var = tk.StringVar(value="Ремонт квартир и домов под ключ")
        self.llm_status_var = tk.StringVar(value="Проверка LLM...")
        self.run_status_var = tk.StringVar(value="Готово к запуску")
        self.is_running = False
        self.last_item: Item | None = None
        self.last_verification_result: PredictionResult | None = None

        self._build_layout()
        self.refresh_llm_status()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(container)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Статус LLM:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(top, textvariable=self.llm_status_var).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Button(top, text="Обновить статус", command=self.refresh_llm_status).grid(row=0, column=2, padx=(12, 0))
        ttk.Label(top, text="Статус анализа:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(top, textvariable=self.run_status_var).grid(row=1, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=(8, 0))

        source_row = ttk.Frame(container)
        source_row.pack(fill=tk.X, pady=(12, 8))

        ttk.Label(source_row, text="Исходный mcId").grid(row=0, column=0, sticky="w")
        ttk.Entry(source_row, textvariable=self.source_mc_var, width=12).grid(row=1, column=0, sticky="w", padx=(0, 12))

        ttk.Label(source_row, text="Исходная микрокатегория").grid(row=0, column=1, sticky="w")
        ttk.Entry(source_row, textvariable=self.source_mc_title_var, width=48).grid(row=1, column=1, sticky="we")
        source_row.columnconfigure(1, weight=1)

        ttk.Label(container, text="Объявление", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.input_text = ScrolledText(container, height=8, wrap=tk.WORD, font=("Consolas", 10))
        self.input_text.pack(fill=tk.X, pady=(4, 8))
        self.input_text.insert("1.0", self.description_var.get())

        buttons = ttk.Frame(container)
        buttons.pack(fill=tk.X, pady=(0, 10))
        self.verify_button = ttk.Button(buttons, text="Определить категории", command=self.run_verification)
        self.verify_button.pack(side=tk.LEFT)
        self.generate_button = ttk.Button(buttons, text="Сгенерировать draft", command=self.run_generation)
        self.generate_button.pack(side=tk.LEFT, padx=(8, 0))
        self.generate_button.state(["disabled"])
        self.clear_button = ttk.Button(buttons, text="Очистить вывод", command=self.clear_outputs)
        self.clear_button.pack(side=tk.LEFT, padx=(8, 0))

        outputs = ttk.Panedwindow(container, orient=tk.HORIZONTAL)
        outputs.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(outputs, padding=4)
        center = ttk.Frame(outputs, padding=4)
        right = ttk.Frame(outputs, padding=4)
        outputs.add(left, weight=3)
        outputs.add(center, weight=2)
        outputs.add(right, weight=3)

        ttk.Label(left, text="JSON / код ответа", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.json_output = ScrolledText(left, wrap=tk.WORD, font=("Consolas", 10))
        self.json_output.pack(fill=tk.BOTH, expand=True)

        ttk.Label(center, text="Микрокатегории", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.categories_output = ScrolledText(center, wrap=tk.WORD, font=("Consolas", 10))
        self.categories_output.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Debug / описание", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.debug_output = ScrolledText(right, wrap=tk.WORD, font=("Consolas", 10))
        self.debug_output.pack(fill=tk.BOTH, expand=True)

    def refresh_llm_status(self) -> None:
        http_ok = False
        http_message = "HTTP API недоступен"
        try:
            with urlopen(QWEN_HEALTH_URL, timeout=2) as response:
                payload = response.read().decode("utf-8", errors="replace").strip()
            http_ok = True
            http_message = payload if payload else "HTTP API отвечает"
        except URLError:
            http_message = "HTTP API недоступен"
        except Exception as exc:  # noqa: BLE001
            http_message = f"HTTP API ошибка: {exc}"

        cli_ok, cli_message = self._check_cli_status()

        if http_ok:
            summary = f"LLM работает: да | server: ok ({http_message}) | cli: {'ok' if cli_ok else 'not ready'}"
        elif cli_ok:
            summary = f"LLM работает: частично | server: down | cli fallback: ok ({cli_message})"
        else:
            summary = f"LLM работает: нет | server: down | cli fallback: not ready ({cli_message})"
        self.llm_status_var.set(summary)

    def _check_cli_status(self) -> tuple[bool, str]:
        if not LLAMA_CLI_PATH.exists():
            return False, f"не найден {LLAMA_CLI_PATH}"
        if not MODEL_PATH.exists():
            return False, f"не найдена модель {MODEL_PATH}"
        cli_size_mb = Path(LLAMA_CLI_PATH).stat().st_size // (1024 * 1024)
        model_size_mb = Path(MODEL_PATH).stat().st_size // (1024 * 1024)
        return True, f"llama-cli={cli_size_mb}MB, model={model_size_mb}MB"

    def clear_outputs(self) -> None:
        for widget in (self.json_output, self.categories_output, self.debug_output):
            widget.delete("1.0", tk.END)
        self.last_item = None
        self.last_verification_result = None
        self.generate_button.state(["disabled"])

    def run_verification(self) -> None:
        if self.is_running:
            return
        self.clear_outputs()
        description = self.input_text.get("1.0", tk.END).strip()
        if not description:
            self.debug_output.insert("1.0", "Введите текст объявления.")
            return

        try:
            item = Item(
                item_id=999999,
                mc_id=int(self.source_mc_var.get().strip()),
                mc_title=self.source_mc_title_var.get().strip(),
                description=description,
            )
        except ValueError:
            self.debug_output.insert("1.0", "mcId должен быть целым числом.")
            return

        self.last_item = item
        self.is_running = True
        self.verify_button.state(["disabled"])
        self.generate_button.state(["disabled"])
        self.run_status_var.set("Идёт verification...")
        self.debug_output.insert("1.0", "Запуск verification...\n")
        thread = threading.Thread(target=self._run_verification_worker, args=(item,), daemon=True)
        thread.start()

    def run_generation(self) -> None:
        if self.is_running or not self.last_item or not self.last_verification_result:
            return
        verified = self.last_verification_result.verified_microcategories
        if not verified:
            self.debug_output.delete("1.0", tk.END)
            self.debug_output.insert("1.0", "Нет подтвержденных микрокатегорий для генерации draft.")
            return

        self.is_running = True
        self.verify_button.state(["disabled"])
        self.generate_button.state(["disabled"])
        self.run_status_var.set("Идёт генерация draft...")
        self.debug_output.delete("1.0", tk.END)
        self.debug_output.insert("1.0", "Запуск draft generation...\n")
        mc_ids = [row["mcId"] for row in verified]
        thread = threading.Thread(target=self._run_generation_worker, args=(self.last_item, mc_ids), daemon=True)
        thread.start()

    def _run_verification_worker(self, item: Item) -> None:
        started_at = time.time()
        try:
            result = self.pipeline.verify_only(item, include_debug=True)
            payload = result.to_public_dict(include_debug=True)
            elapsed = time.time() - started_at
            self.root.after(0, lambda: self._handle_verification_success(result, payload, elapsed))
        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - started_at
            self.root.after(0, lambda: self._handle_error(exc, elapsed, "verification"))

    def _run_generation_worker(self, item: Item, mc_ids: list[int]) -> None:
        started_at = time.time()
        try:
            result = self.pipeline.generate_drafts_for_verified(
                item,
                mc_ids,
                verification_result=self.last_verification_result,
                include_debug=True,
            )
            payload = result.to_public_dict(include_debug=True)
            elapsed = time.time() - started_at
            self.root.after(0, lambda: self._handle_generation_success(result, payload, elapsed))
        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - started_at
            self.root.after(0, lambda: self._handle_error(exc, elapsed, "generation"))

    def _handle_verification_success(self, result: PredictionResult, public_payload: dict, elapsed: float) -> None:
        self.last_verification_result = result
        self.json_output.insert("1.0", json.dumps(public_payload, ensure_ascii=False, indent=2))

        lines = [f"shouldSplit: {public_payload['shouldSplit']}"]
        lines.append(f"Исходная категория: {self.last_item.mc_id} | {self.last_item.mc_title}")
        lines.append("")
        lines.append("Найдено в тексте:")
        for match in debug.get("matches", []):
            lines.append(f"- {match['mcId']} | {match['mcTitle']}")
        lines.append("")
        lines.append("Дополнительные draft-кандидаты:")
        verified_rows = public_payload.get("verifiedMicrocategories", [])
        if verified_rows:
            for row in verified_rows:
                lines.append(f"- {row['mcId']} | {row['mcTitle']} | standalone={row['isStandalone']}")
        else:
            lines.append("- подтвержденных микрокатегорий не найдено")
        self.categories_output.insert("1.0", "\n".join(lines))

        debug_lines = [f"Время ответа: {elapsed:.1f} сек"]
        debug = public_payload.get("debug", {})
        verification_meta = debug.get("qwenVerificationMeta", {})
        transport = verification_meta.get("transport", "unknown")
        debug_lines.append(f"LLM transport: {transport}")
        if debug.get("verificationTimedOut"):
            debug_lines.append("verification timed out")
        debug_lines.append("")
        debug_lines.append("Matched categories:")
        for match in debug.get("matches", []):
            debug_lines.append(
                f"- {match['mcId']} | {match['mcTitle']} | phrases={', '.join(match['matchedPhrases'])}"
            )
        debug_lines.append("")
        debug_lines.append(
            "Примечание: исходная микрокатегория объявления не добавляется в verifiedMicrocategories, "
            "потому что split нужен только для дополнительных черновиков."
        )
        debug_lines.append("")
        debug_lines.append("Verification:")
        for row in debug.get("verification", []):
            debug_lines.append(
                f"- mcId={row['mcId']} standalone={row['isStandalone']} confidence={row['confidence']} source={row['source']}"
            )
            debug_lines.append(f"  rationale: {row['rationale']}")
        self.debug_output.delete("1.0", tk.END)
        self.debug_output.insert("1.0", "\n".join(debug_lines))
        self.is_running = False
        self.verify_button.state(["!disabled"])
        if verified_rows and not debug.get("verificationTimedOut"):
            self.generate_button.state(["!disabled"])
            self.run_status_var.set(f"Verification готов. Категории найдены за {elapsed:.1f} сек")
        elif debug.get("verificationTimedOut"):
            self.run_status_var.set(f"Verification timed out after {elapsed:.1f} сек")
        else:
            self.run_status_var.set(f"Verification завершён за {elapsed:.1f} сек")

    def _handle_generation_success(self, result: PredictionResult, public_payload: dict, elapsed: float) -> None:
        self.last_verification_result = result
        self.json_output.delete("1.0", tk.END)
        self.json_output.insert("1.0", json.dumps(public_payload, ensure_ascii=False, indent=2))
        lines = [f"shouldSplit: {public_payload['shouldSplit']}"]
        for draft in public_payload.get("drafts", []):
            lines.append(f"- {draft['mcId']} | {draft['mcTitle']}")
        self.categories_output.delete("1.0", tk.END)
        self.categories_output.insert("1.0", "\n".join(lines))

        debug_lines = [f"Draft generation time: {elapsed:.1f} сек"]
        for meta in public_payload.get("debug", {}).get("draftGenerationMeta", []):
            debug_lines.append(f"- mcId={meta['mcId']} transport={meta['meta'].get('transport', 'unknown')}")
        self.debug_output.delete("1.0", tk.END)
        self.debug_output.insert("1.0", "\n".join(debug_lines))
        self.is_running = False
        self.verify_button.state(["!disabled"])
        self.generate_button.state(["!disabled"])
        self.run_status_var.set(f"Draft generation завершён за {elapsed:.1f} сек")

    def _handle_error(self, exc: Exception, elapsed: float, phase: str) -> None:
        self.debug_output.delete("1.0", tk.END)
        self.debug_output.insert("1.0", f"Ошибка во время {phase} после {elapsed:.1f} сек:\n{exc}")
        self.is_running = False
        self.verify_button.state(["!disabled"])
        if self.last_verification_result and self.last_verification_result.verified_microcategories:
            self.generate_button.state(["!disabled"])
        self.run_status_var.set(f"Ошибка {phase}")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    TestInterfaceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
