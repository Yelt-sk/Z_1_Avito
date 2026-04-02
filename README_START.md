# README_START

## Что нужно для старта
- Python 3.11+
- Локальная папка `D:\LLM\Qwen 3`
- GGUF-модель и `llama-cli.exe`

## Установка

```bash
python -m pip install -e .[dev]
```

Если не нужен `pytest`:

```bash
python -m pip install -e .
```

## Первый запуск

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json --debug
```

## Если локальный HTTP API Qwen 3 поднят
По умолчанию клиент сначала пробует:

```text
http://127.0.0.1:8090/v1/chat/completions
```

Если endpoint недоступен, клиент автоматически переключается на `llama-cli.exe`.

## Режим без Qwen 3

```bash
python -m avito_splitter predict --item data/input_item.json --dict data/microcategories.json --disable-qwen --debug
```

Это полезно для smoke-теста пайплайна, но в целевом режиме `Qwen 3` должен участвовать в verification и generation.

## Проверка тестов

```bash
pytest
```

## Проверка качества на примерах

```bash
python -m avito_splitter evaluate --examples data/examples.jsonl --dict data/microcategories.json --disable-qwen
python -m avito_splitter calibrate --examples data/examples.jsonl --dict data/microcategories.json --disable-qwen
```
